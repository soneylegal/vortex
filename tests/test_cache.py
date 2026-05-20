import shutil
import tempfile
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.app.core.dependencies import get_agent_workflow
from src.app.main import app


@pytest.fixture
def temp_chroma_dir():
    """Create a temporary directory for ChromaDB cache tests."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def semantic_cache(temp_chroma_dir):
    """Fixture for SemanticCacheService configured to use a temp directory."""
    with (
        patch("src.app.services.cache.settings") as cache_settings,
        patch("src.app.services.vector_store.settings") as vs_settings,
    ):
        cache_settings.chroma_persist_directory = temp_chroma_dir
        cache_settings.semantic_cache_threshold = 0.1
        cache_settings.llm_provider = "gemini"
        vs_settings.chroma_persist_directory = temp_chroma_dir

        # Reset singletons to force reload with mocked settings
        import src.app.services.cache as cache_module
        import src.app.services.vector_store as vs_module

        cache_module._cache_instance = None
        vs_module._instance = None

        from src.app.services.cache import SemanticCacheService

        service = SemanticCacheService()

        yield service

        # Cleanup singletons
        cache_module._cache_instance = None
        vs_module._instance = None


@pytest.fixture
def client_with_cache(temp_chroma_dir):
    """Fixture for FastAPI TestClient configured to use a temp cache directory."""
    with (
        patch("src.app.services.cache.settings") as cache_settings,
        patch("src.app.services.vector_store.settings") as vs_settings,
        patch("src.app.api.v1.chat.settings") as api_settings,
    ):
        cache_settings.chroma_persist_directory = temp_chroma_dir
        cache_settings.semantic_cache_threshold = 0.15
        cache_settings.enable_semantic_cache = True
        cache_settings.llm_provider = "gemini"

        vs_settings.chroma_persist_directory = temp_chroma_dir

        api_settings.enable_semantic_cache = True

        import src.app.services.cache as cache_module
        import src.app.services.vector_store as vs_module

        cache_module._cache_instance = None
        vs_module._instance = None

        yield TestClient(app)

        cache_module._cache_instance = None
        vs_module._instance = None


class TestSemanticCacheService:
    def test_cache_hit_and_miss(self, semantic_cache):
        """Test exact lookup, semantic lookup (hit), and miss for unrelated queries."""
        # 1. Initially empty cache lookup should miss
        assert semantic_cache.lookup("How to fix Cortex Error 503?") is None

        # 2. Store response
        semantic_cache.update(
            query="How to fix Cortex Error 503?",
            answer="Restart the Sentinel service and clear the cache.",
            sources=[{"content": "Cortex Error 503 details", "metadata": {}}],
            steps=["received_query", "router", "retrieve"],
            route="retrieve",
        )

        # 3. Exact match lookup should hit
        exact_res = semantic_cache.lookup("How to fix Cortex Error 503?")
        assert exact_res is not None
        assert exact_res["answer"] == (
            "Restart the Sentinel service and clear the cache."
        )
        assert exact_res["route"] == "retrieve"
        assert len(exact_res["sources"]) == 1

        # 4. Semantically close query lookup should hit (slight phrasing difference)
        semantic_res = semantic_cache.lookup("Can you help me solve Cortex Error 503?")
        assert semantic_res is not None
        assert semantic_res["answer"] == (
            "Restart the Sentinel service and clear the cache."
        )

        # 5. Unrelated query should miss
        unrelated_res = semantic_cache.lookup("What is Ollama base URL?")
        assert unrelated_res is None

    def test_cache_provider_isolation(self, semantic_cache):
        """Test that caches are partitioned by the LLM provider."""
        # Store for gemini
        semantic_cache.update(
            query="test query",
            answer="gemini answer",
            sources=[],
            steps=[],
            route="direct",
            provider="gemini",
        )

        # Lookup with anthropic should miss
        assert semantic_cache.lookup("test query", provider="anthropic") is None

        # Lookup with gemini should hit
        res = semantic_cache.lookup("test query", provider="gemini")
        assert res is not None
        assert res["answer"] == "gemini answer"

    def test_clear_cache(self, semantic_cache):
        """Test that clear() purges the cache collection."""
        semantic_cache.update(
            query="test query",
            answer="test answer",
            sources=[],
            steps=[],
            route="direct",
        )
        assert semantic_cache.lookup("test query") is not None

        semantic_cache.clear()
        assert semantic_cache.lookup("test query") is None


class TestSemanticCacheIntegration:
    def test_api_caching_flow(self, client_with_cache):
        """Test that the API endpoint successfully looks up and updates the cache."""
        mock_workflow = AsyncMock()
        mock_workflow.ainvoke.return_value = {
            "question": "How to start Sentinel?",
            "generation": "Run sentinel start command.",
            "documents": [],
            "steps": ["received_query", "router", "direct_response"],
            "route": "direct",
            "retry_count": 0,
        }

        app.dependency_overrides[get_agent_workflow] = lambda: mock_workflow

        # First request: Cache Miss -> Call workflow -> Cache Response
        response1 = client_with_cache.post(
            "/api/v1/chat", json={"query": "How to start Sentinel?"}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["answer"] == "Run sentinel start command."
        assert "semantic_cache_hit" not in data1["steps"]
        assert mock_workflow.ainvoke.call_count == 1

        # Second request: Semantically similar query -> Cache Hit -> Return directly
        mock_workflow.reset_mock()
        response2 = client_with_cache.post(
            "/api/v1/chat", json={"query": "Can you tell me how to start Sentinel?"}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["answer"] == "Run sentinel start command."
        assert "semantic_cache_hit" in data2["steps"]
        assert mock_workflow.ainvoke.call_count == 0  # Workflow was NOT invoked

        app.dependency_overrides.clear()
