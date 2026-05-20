import json
import logging
import os

from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.app.core.config import settings
from src.app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class SemanticCacheService:
    """
    Zero-cost Semantic Cache Service using a local ChromaDB collection.
    Matches queries against answers based on semantic similarity.
    """

    def __init__(self):
        # Share the HuggingFace embeddings object to avoid loading the model again.
        self.embeddings = get_vector_store().embeddings
        self.persist_directory = settings.chroma_persist_directory
        self.collection_name = "vortex_semantic_cache"

        # Initialize the Chroma collection configured for cosine distance
        os.makedirs(self.persist_directory, exist_ok=True)
        self.vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory,
            collection_metadata={"hnsw:space": "cosine"},
        )
        self.distance_threshold = settings.semantic_cache_threshold

    def lookup(self, query: str, provider: str | None = None) -> dict | None:
        """
        Lookup a query in the cache. Matches semantically similar queries
        with cosine distance below the configured threshold.
        """
        try:
            active_provider = provider or settings.llm_provider
            filter_dict = {"provider": active_provider}

            results = self.vector_store.similarity_search_with_score(
                query, k=1, filter=filter_dict
            )
            if not results:
                logger.info(f"Semantic cache MISS (no matches) for query: '{query}'")
                return None

            doc, distance = results[0]
            logger.info(
                f"Semantic cache match found. Distance: {distance:.4f} "
                f"(threshold: {self.distance_threshold})"
            )

            if distance <= self.distance_threshold:
                logger.info(
                    f"Semantic cache HIT for query: '{query}' "
                    f"(matched: '{doc.page_content}', dist: {distance:.4f})"
                )
                metadata = doc.metadata

                try:
                    sources = json.loads(metadata.get("sources", "[]"))
                except Exception:
                    sources = []

                try:
                    steps = json.loads(metadata.get("steps", "[]"))
                except Exception:
                    steps = []

                return {
                    "answer": metadata.get("answer", ""),
                    "sources": sources,
                    "steps": steps,
                    "route": metadata.get("route") or None,
                }

            logger.info(
                f"Semantic cache MISS (distance {distance:.4f} > "
                f"threshold {self.distance_threshold}) for: '{query}'"
            )
        except Exception as e:
            logger.error(f"Failed to lookup in semantic cache: {e}", exc_info=True)

        return None

    def update(
        self,
        query: str,
        answer: str,
        sources: list,
        steps: list,
        route: str | None,
        provider: str | None = None,
    ):
        """Store a successful query-response pair in the semantic cache."""
        try:
            active_provider = provider or settings.llm_provider
            doc = Document(
                page_content=query,
                metadata={
                    "answer": answer,
                    "sources": json.dumps(sources),
                    "steps": json.dumps(steps),
                    "route": route or "",
                    "provider": active_provider,
                },
            )
            self.vector_store.add_documents([doc])
            logger.info(
                f"Stored query in semantic cache: '{query}' "
                f"[provider: {active_provider}]"
            )
        except Exception as e:
            logger.error(f"Failed to update semantic cache: {e}", exc_info=True)

    def clear(self):
        """Clear all cached entries."""
        try:
            self.vector_store.delete_collection()
            self.vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory,
                collection_metadata={"hnsw:space": "cosine"},
            )
            logger.info("Semantic cache cleared successfully.")
        except Exception as e:
            logger.error(f"Failed to clear semantic cache: {e}", exc_info=True)


# ── Lazy singleton ──────────────────────────────────────────────────────
_cache_instance: SemanticCacheService | None = None


def get_semantic_cache() -> SemanticCacheService:
    """Lazily initialize and return the singleton SemanticCacheService."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SemanticCacheService()
    return _cache_instance
