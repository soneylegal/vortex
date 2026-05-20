from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.app.core.dependencies import get_agent_workflow
from src.app.main import app

client = TestClient(app)


def test_chat_byok_headers():
    """
    Test that Authorization and X-Provider headers are correctly
    extracted and passed to the workflow state.
    """
    mock_workflow = AsyncMock()
    mock_workflow.ainvoke.return_value = {
        "question": "test question",
        "generation": "mock response",
        "documents": [],
        "steps": ["received_query"],
        "route": "direct",
        "retry_count": 0,
    }

    app.dependency_overrides[get_agent_workflow] = lambda: mock_workflow

    # 1. Test Bearer token in Authorization header and X-Provider header
    headers = {
        "Authorization": "Bearer my-custom-gemini-key",
        "X-Provider": "gemini",
    }
    response = client.post(
        "/api/v1/chat",
        json={"query": "test question"},
        headers=headers,
    )

    assert response.status_code == 200
    assert mock_workflow.ainvoke.call_count == 1
    call_state = mock_workflow.ainvoke.call_args[0][0]
    assert call_state["api_key"] == "my-custom-gemini-key"
    assert call_state["provider"] == "gemini"

    # 2. Test X-API-Key header and different casing for X-Provider
    mock_workflow.reset_mock()
    headers = {
        "X-API-Key": "my-custom-anthropic-key",
        "X-Provider": "Anthropic",
    }
    response = client.post(
        "/api/v1/chat",
        json={"query": "test question"},
        headers=headers,
    )

    assert response.status_code == 200
    assert mock_workflow.ainvoke.call_count == 1
    call_state = mock_workflow.ainvoke.call_args[0][0]
    assert call_state["api_key"] == "my-custom-anthropic-key"
    assert call_state["provider"] == "anthropic"

    # 3. Test when no headers are provided (should pass None)
    mock_workflow.reset_mock()
    response = client.post(
        "/api/v1/chat",
        json={"query": "test question"},
    )

    assert response.status_code == 200
    assert mock_workflow.ainvoke.call_count == 1
    call_state = mock_workflow.ainvoke.call_args[0][0]
    assert call_state["api_key"] is None
    assert call_state["provider"] is None

    app.dependency_overrides.clear()


def test_chat_invalid_provider():
    """Test that an unsupported provider returns a 400 Bad Request error."""
    mock_workflow = AsyncMock()
    app.dependency_overrides[get_agent_workflow] = lambda: mock_workflow

    headers = {
        "X-Provider": "unsupported-llm-brand",
    }
    response = client.post(
        "/api/v1/chat",
        json={"query": "test question"},
        headers=headers,
    )

    assert response.status_code == 400
    assert "Unsupported LLM provider" in response.json()["detail"]
    assert mock_workflow.ainvoke.call_count == 0

    app.dependency_overrides.clear()
