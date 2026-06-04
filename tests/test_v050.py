import io
import json
import shutil
import tempfile
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from src.app.core.dependencies import get_agent_workflow
from src.app.main import app


@pytest.fixture
def temp_chroma_dir():
    """Create a temporary directory for ChromaDB tests."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def vector_store(temp_chroma_dir):
    """Create a VectorStoreService with a temporary persist directory."""
    with patch("src.app.services.vector_store.settings") as mock_settings:
        mock_settings.chroma_persist_directory = temp_chroma_dir

        # Reset the singleton so we get a fresh instance
        import src.app.services.vector_store as vs_module
        vs_module._instance = None

        from src.app.services.vector_store import VectorStoreService
        service = VectorStoreService()
        service.persist_directory = temp_chroma_dir

        yield service

        # Clean up singleton
        vs_module._instance = None


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


class TestVectorStoreTenantIsolation:
    def test_tenant_isolation_and_counting(self, vector_store):
        """Verify dynamic collections keep tenants isolated."""
        doc_a = Document(page_content="Tenant A doc content", metadata={"source": "a.md"})
        doc_b = Document(page_content="Tenant B doc content", metadata={"source": "b.md"})

        vector_store.add_documents([doc_a], tenant_id="tenant-a")
        vector_store.add_documents([doc_b], tenant_id="tenant-b")

        # Isolation verification
        res_a = vector_store.search("content", tenant_id="tenant-a")
        assert len(res_a) == 1
        assert "Tenant A" in res_a[0].page_content

        res_b = vector_store.search("content", tenant_id="tenant-b")
        assert len(res_b) == 1
        assert "Tenant B" in res_b[0].page_content

        # Counting isolation
        assert vector_store.document_count(tenant_id="tenant-a") == 1
        assert vector_store.document_count(tenant_id="tenant-b") == 1

        # Clearing isolation
        vector_store.clear(tenant_id="tenant-a")
        assert vector_store.document_count(tenant_id="tenant-a") == 0
        assert vector_store.document_count(tenant_id="tenant-b") == 1


class TestSemanticCacheTenantIsolation:
    def test_cache_tenant_isolation(self, semantic_cache):
        """Verify cache hits are isolated by tenant."""
        semantic_cache.update(
            query="test query",
            answer="Tenant A Answer",
            sources=[],
            steps=["step1"],
            route="direct",
            provider="gemini",
            tenant_id="tenant-a",
        )

        # Hits on tenant-a
        hit_a = semantic_cache.lookup("test query", provider="gemini", tenant_id="tenant-a")
        assert hit_a is not None
        assert hit_a["answer"] == "Tenant A Answer"

        # Misses on tenant-b
        hit_b = semantic_cache.lookup("test query", provider="gemini", tenant_id="tenant-b")
        assert hit_b is None

        # Misses on default
        hit_def = semantic_cache.lookup("test query", provider="gemini")
        assert hit_def is None


class TestStreamingAndHistoryEndpoints:
    def test_chat_stream_endpoint(self):
        """Verify POST /api/v1/chat/stream yields SSE chunks and final metadata."""
        mock_workflow = AsyncMock()

        # Simulate graph events stream
        async def mock_astream_events(initial_state, config, version):
            # yield model stream token
            yield {
                "event": "on_chat_model_stream",
                "name": "gemini",
                "tags": ["generate_answer"],
                "data": {
                    "chunk": AsyncMock(content="Hello")
                }
            }
            yield {
                "event": "on_chat_model_stream",
                "name": "gemini",
                "tags": ["generate_answer"],
                "data": {
                    "chunk": AsyncMock(content=" world")
                }
            }
            # yield workflow end
            yield {
                "event": "on_chain_end",
                "name": "LangGraph",
                "data": {
                    "output": {
                        "documents": [
                            Document(page_content="manual info", metadata={"source": "kb.md"})
                        ],
                        "steps": ["router", "generate_answer"],
                        "route": "retrieve",
                    }
                }
            }

        mock_workflow.astream_events = mock_astream_events

        app.dependency_overrides[get_agent_workflow] = lambda: mock_workflow
        client = TestClient(app)

        response = client.post(
            "/api/v1/chat/stream",
            json={"query": "test query", "tenant_id": "tenant-a", "session_id": "session-1"},
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Parse SSE stream output
        lines = [line.decode("utf-8") if isinstance(line, bytes) else line for line in response.iter_lines() if line]
        tokens = []
        metadata = None

        for line in lines:
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                if payload.get("event") == "token":
                    tokens.append(payload["text"])
                elif payload.get("event") == "metadata":
                    metadata = payload

        assert "".join(tokens) == "Hello world"
        assert metadata is not None
        assert metadata["route"] == "retrieve"
        assert metadata["steps"] == ["router", "generate_answer"]
        assert len(metadata["sources"]) == 1
        assert metadata["sources"][0]["content"] == "manual info"

        app.dependency_overrides.clear()

    def test_document_ingestion_endpoint(self, vector_store):
        """Verify POST /api/v1/documents API chunks and ingests Markdown files."""
        client = TestClient(app)

        # Mock get_vector_store to return our test fixture vector_store
        with patch("src.app.api.v1.documents.get_vector_store", return_value=vector_store):
            # Test Markdown ingestion
            md_content = b"# Title\n\nSome knowledge description.\n\n## Section\n\nMore details."
            md_file = io.BytesIO(md_content)

            response = client.post(
                "/api/v1/documents",
                files={"file": ("manual.md", md_file, "text/markdown")},
                data={"tenant_id": "tenant-xyz"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["filename"] == "manual.md"
            assert data["chunks_count"] > 0
            assert data["tenant_id"] == "tenant-xyz"
            assert data["status"] == "success"

            # Check vector store
            assert vector_store.document_count(tenant_id="tenant-xyz") > 0
            docs = vector_store.search("details", tenant_id="tenant-xyz")
            assert len(docs) > 0
            assert "details" in docs[0].page_content
            assert docs[0].metadata["tenant_id"] == "tenant-xyz"

    def test_document_ingestion_unsupported_type(self):
        """Verify endpoints reject unsupported file extensions."""
        client = TestClient(app)
        response = client.post(
            "/api/v1/documents",
            files={"file": ("manual.txt", io.BytesIO(b"content"), "text/plain")},
        )
        assert response.status_code == 400
        assert "Only .md and .pdf files are supported" in response.json()["detail"]
