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

        # Initialize the Chroma DB
        os.makedirs(self.persist_directory, exist_ok=True)
        self.vector_store = Chroma(
            collection_name="vortex_kb",
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory,
        )

    def search(self, query: str, k: int = 4) -> list[Document]:
        """Search the vector store for relevant documents."""
        return self.vector_store.similarity_search(query, k=k)

    def add_documents(self, documents: list[Document]):
        """Add documents to the vector store."""
        self.vector_store.add_documents(documents)

    def document_count(self) -> int:
        """Return the total number of documents in the collection."""
        return self.vector_store._collection.count()

    def clear(self):
        """Delete all documents from the collection and re-initialize."""
        self.vector_store.delete_collection()
        self.vector_store = Chroma(
            collection_name="vortex_kb",
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory,
        )


# ── Lazy singleton ──────────────────────────────────────────────────────
# Prevents HuggingFace model from loading at import time (breaks tests).
_instance: VectorStoreService | None = None


def get_vector_store() -> VectorStoreService:
    """Lazily initialize and return the singleton VectorStoreService."""
    global _instance
    if _instance is None:
        _instance = VectorStoreService()
    return _instance
