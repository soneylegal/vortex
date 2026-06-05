import hashlib
from unittest.mock import patch

import numpy as np
import pytest
from langchain_core.embeddings import Embeddings


class MockEmbeddings(Embeddings):
    def __init__(self, size: int = 384):
        self.size = size

    def embed_query(self, text: str) -> list[float]:
        vector = np.zeros(self.size)
        text_lower = text.lower()
        if "cortex" in text_lower:
            vector[0] += 1.0
        if "503" in text_lower:
            vector[1] += 1.0
        if "lambda" in text_lower:
            vector[2] += 1.0
        if "error" in text_lower:
            vector[3] += 1.0
        if "test query" in text_lower:
            vector[4] += 1.0
        if "content" in text_lower:
            vector[5] += 1.0
        if "sentinel" in text_lower:
            vector[6] += 1.0

        h = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
        idx = 7 + (h % (self.size - 7))
        vector[idx] += 0.1

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]


@pytest.fixture(autouse=True, scope="session")
def mock_huggingface_embeddings():
    """Mock HuggingFaceEmbeddings to use MockEmbeddings in all tests."""
    with patch("src.app.services.vector_store.HuggingFaceEmbeddings") as mock_hf:
        mock_hf.return_value = MockEmbeddings(size=384)
        yield
