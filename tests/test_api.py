from unittest.mock import patch

from fastapi.testclient import TestClient

from src.app.main import app

client = TestClient(app)


def test_health_check():
    """Health endpoint returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("src.app.main.workflow")
def test_chat_rag_path(mock_workflow):
    """Test /chat endpoint with the RAG retrieval path."""
    from langchain_core.documents import Document

    async def mock_ainvoke(*args, **kwargs):
        return {
            "question": "How to fix Cortex Error 503?",
            "generation": "Restart the Lambda functions and check concurrency limits.",
            "documents": [
                Document(
                    page_content="If you see Error 503, restart Lambda.",
                    metadata={"source": "cortex_manual.md"},
                )
            ],
            "steps": [
                "received_query",
                "router",
                "retrieve_documents",
                "grade_documents",
                "generate_answer",
            ],
            "route": "retrieve",
            "retry_count": 0,
        }

    mock_workflow.ainvoke = mock_ainvoke

    response = client.post("/chat", json={"query": "How to fix Cortex Error 503?"})

    assert response.status_code == 200
    data = response.json()
    expected = "Restart the Lambda functions and check concurrency limits."
    assert data["answer"] == expected
    assert len(data["sources"]) == 1
    assert data["route"] == "retrieve"
    assert "router" in data["steps"]
    assert "generate_answer" in data["steps"]


@patch("src.app.main.workflow")
def test_chat_direct_path(mock_workflow):
    """Test /chat endpoint with the direct response path (no RAG)."""

    async def mock_ainvoke(*args, **kwargs):
        return {
            "question": "What is 2+2?",
            "generation": "4.",
            "documents": [],
            "steps": ["received_query", "router", "direct_response"],
            "route": "direct",
            "retry_count": 0,
        }

    mock_workflow.ainvoke = mock_ainvoke

    response = client.post("/chat", json={"query": "What is 2+2?"})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "4."
    assert data["sources"] == []
    assert data["route"] == "direct"
    assert "direct_response" in data["steps"]


@patch("src.app.main.workflow")
def test_chat_fallback_path(mock_workflow):
    """Test /chat endpoint when all retries are exhausted."""

    async def mock_ainvoke(*args, **kwargs):
        return {
            "question": "something not in the KB",
            "generation": "I wasn't able to find relevant documentation.",
            "documents": [],
            "steps": [
                "received_query",
                "router",
                "retrieve_documents",
                "grade_documents",
                "rewrite_query",
                "retrieve_documents",
                "grade_documents",
                "rewrite_query",
                "fallback",
            ],
            "route": "retrieve",
            "retry_count": 2,
        }

    mock_workflow.ainvoke = mock_ainvoke

    response = client.post("/chat", json={"query": "something not in the KB"})

    assert response.status_code == 200
    data = response.json()
    assert "fallback" in data["steps"]
    assert data["route"] == "retrieve"
