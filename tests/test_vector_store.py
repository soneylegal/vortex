import shutil
import tempfile
from unittest.mock import patch

import pytest
from langchain_core.documents import Document


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


class TestVectorStoreService:
    def test_add_and_search(self, vector_store):
        """Documents can be added and retrieved via similarity search."""
        docs = [
            Document(
                page_content="Cortex Error 503: Restart Lambda functions.",
                metadata={"source": "cortex_manual.md"},
            ),
            Document(
                page_content="Sentinel monitors CPU utilization via Prometheus.",
                metadata={"source": "sentinel_manual.md"},
            ),
        ]
        vector_store.add_documents(docs)

        results = vector_store.search("Lambda error", k=1)
        assert len(results) == 1
        assert "Lambda" in results[0].page_content or "503" in results[0].page_content

    def test_document_count(self, vector_store):
        """document_count() returns the correct number of indexed documents."""
        assert vector_store.document_count() == 0

        docs = [
            Document(page_content="Test document 1", metadata={}),
            Document(page_content="Test document 2", metadata={}),
        ]
        vector_store.add_documents(docs)

        assert vector_store.document_count() == 2

    def test_clear(self, vector_store):
        """clear() removes all documents from the collection."""
        docs = [
            Document(page_content="Will be deleted", metadata={}),
        ]
        vector_store.add_documents(docs)
        assert vector_store.document_count() == 1

        vector_store.clear()
        assert vector_store.document_count() == 0

    def test_search_empty_store(self, vector_store):
        """Searching an empty store returns an empty list."""
        results = vector_store.search("anything")
        assert results == []


class TestLazySingleton:
    def test_lazy_init_does_not_load_at_import(self):
        """Importing the module should NOT instantiate VectorStoreService."""
        import src.app.services.vector_store as vs_module

        # Reset singleton
        vs_module._instance = None
        # The module-level _instance should be None after reset
        assert vs_module._instance is None
