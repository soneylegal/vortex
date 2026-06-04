import os

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from src.app.core.config import settings


class VectorStoreService:
    """Manages the ChromaDB vector store with HuggingFace embeddings."""

    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.persist_directory = settings.chroma_persist_directory
        os.makedirs(self.persist_directory, exist_ok=True)
        self._collections: dict[str, Chroma] = {}

    def _get_collection(self, tenant_id: str | None = None) -> Chroma:
        collection_name = f"vortex_kb_{tenant_id}" if tenant_id else "vortex_kb"
        if collection_name not in self._collections:
            self._collections[collection_name] = Chroma(
                collection_name=collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
            )
        return self._collections[collection_name]

    def search(self, query: str, k: int = 4, tenant_id: str | None = None) -> list[Document]:
        """Search the vector store for relevant documents."""
        db = self._get_collection(tenant_id)
        return db.similarity_search(query, k=k)

    def add_documents(self, documents: list[Document], tenant_id: str | None = None):
        """Add documents to the vector store."""
        db = self._get_collection(tenant_id)
        db.add_documents(documents)

    def document_count(self, tenant_id: str | None = None) -> int:
        """Return the total number of documents in the collection."""
        db = self._get_collection(tenant_id)
        return db._collection.count()

    def clear(self, tenant_id: str | None = None):
        """Delete all documents from the collection and re-initialize."""
        db = self._get_collection(tenant_id)
        db.delete_collection()
        collection_name = f"vortex_kb_{tenant_id}" if tenant_id else "vortex_kb"
        if collection_name in self._collections:
            del self._collections[collection_name]


# ── Lazy singleton ──────────────────────────────────────────────────────
# Prevents HuggingFace model from loading at import time (breaks tests).
_instance: VectorStoreService | None = None


def get_vector_store() -> VectorStoreService:
    """Lazily initialize and return the singleton VectorStoreService."""
    global _instance
    if _instance is None:
        _instance = VectorStoreService()
    return _instance
