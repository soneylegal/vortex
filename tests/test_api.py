from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.app.core.dependencies import get_agent_workflow
from src.app.main import app

client = TestClient(app)


def test_health_check():
    """Health endpoint returns 200 OK with system status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "chromadb" in data
    assert "model" in data


def test_chat_rag_path():
    """Test /api/v1/chat endpoint with the RAG retrieval path."""
    from langchain_core.documents import Document

    mock_workflow = AsyncMock()
    mock_workflow.ainvoke.return_value = {
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

    app.dependency_overrides[get_agent_workflow] = lambda: mock_workflow
    response = client.post(
        "/api/v1/chat", json={"query": "How to fix Cortex Error 503?"}
    )

    assert response.status_code == 200
    data = response.json()
    expected = "Restart the Lambda functions and check concurrency limits."
    assert data["answer"] == expected
    assert len(data["sources"]) == 1
    assert data["route"] == "retrieve"
    assert "router" in data["steps"]
    assert "generate_answer" in data["steps"]

    app.dependency_overrides.clear()


def test_chat_direct_path():
    """Test /api/v1/chat endpoint with the direct response path (no RAG)."""
    mock_workflow = AsyncMock()
    mock_workflow.ainvoke.return_value = {
        "question": "What is 2+2?",
        "generation": "4.",
        "documents": [],
        "steps": ["received_query", "router", "direct_response"],
        "route": "direct",
        "retry_count": 0,
    }

    app.dependency_overrides[get_agent_workflow] = lambda: mock_workflow

    response = client.post("/api/v1/chat", json={"query": "What is 2+2?"})

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "4."
    assert data["sources"] == []
    assert data["route"] == "direct"
    assert "direct_response" in data["steps"]

    app.dependency_overrides.clear()


def test_chat_fallback_path():
    """Test /api/v1/chat endpoint when all retries are exhausted."""
    mock_workflow = AsyncMock()
    mock_workflow.ainvoke.return_value = {
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

    app.dependency_overrides[get_agent_workflow] = lambda: mock_workflow

    response = client.post("/api/v1/chat", json={"query": "something not in the KB"})

    assert response.status_code == 200
    data = response.json()
    assert "fallback" in data["steps"]
    assert data["route"] == "retrieve"

    app.dependency_overrides.clear()
