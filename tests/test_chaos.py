from unittest.mock import MagicMock, patch

import pytest

from src.app.core.config import settings
from src.app.graph.workflow import get_workflow


@pytest.fixture(autouse=True)
def disable_cache():
    """Globally disable semantic cache for chaos tests to ensure node execution."""
    original_val = settings.enable_semantic_cache
    settings.enable_semantic_cache = False
    yield
    settings.enable_semantic_cache = original_val


@pytest.mark.asyncio
async def test_chaos_router_llm_failure():
    """
    Test that if the LLM fails during routing, the workflow
    recovers and redirects to the fallback node.
    """
    # Mock get_llm to raise an exception when invoked
    mock_llm = MagicMock()
    mock_llm.with_structured_output.side_effect = RuntimeError("LLM Timeout")

    with patch("src.app.graph.router.get_llm", return_value=mock_llm):
        workflow = get_workflow()
        initial_state = {
            "question": "How to restart sentinel?",
            "generation": "",
            "documents": [],
            "steps": ["received_query"],
            "route": "",
            "retry_count": 0,
        }

        result = await workflow.ainvoke(initial_state)

        # The workflow must not crash, must return fallback response
        assert "steps" in result
        assert "router" in result["steps"]
        assert "fallback" in result["steps"]
        assert result["route"] == "fallback"
        assert "internal system error" in result["generation"]


@pytest.mark.asyncio
async def test_chaos_chromadb_offline():
    """
    Test that if ChromaDB is offline (throws exception during search),
    the workflow redirects to the fallback node gracefully.
    """
    # 1. Mock router to route to retrieve
    mock_router_decision = MagicMock()
    mock_router_decision.route = "retrieve"

    mock_router_llm = MagicMock()
    mock_router_llm.with_structured_output.return_value = mock_router_llm
    mock_router_llm.invoke.return_value = mock_router_decision
    mock_router_llm.return_value = mock_router_decision

    # 2. Mock Vector Store search to raise ConnectionError
    mock_vs = MagicMock()
    mock_vs.search.side_effect = ConnectionError("ChromaDB server down")

    with (
        patch("src.app.graph.router.get_llm", return_value=mock_router_llm),
        patch("src.app.graph.nodes.get_vector_store", return_value=mock_vs),
    ):
        workflow = get_workflow()
        initial_state = {
            "question": "How to fix Sentinel?",
            "generation": "",
            "documents": [],
            "steps": ["received_query"],
            "route": "",
            "retry_count": 0,
        }

        result = await workflow.ainvoke(initial_state)

        # The workflow should route: router -> retrieve -> grade -> fallback
        assert "steps" in result
        assert "router" in result["steps"]
        assert "retrieve_documents" in result["steps"]
        assert "grade_documents" in result["steps"]
        assert "fallback" in result["steps"]
        assert "internal system error" in result["generation"]


@pytest.mark.asyncio
async def test_chaos_generate_llm_failure():
    """
    Test that if the LLM fails during answer generation,
    the workflow returns a friendly error message instead of crashing.
    """
    # 1. Mock router to route to retrieve
    mock_router_decision = MagicMock()
    mock_router_decision.route = "retrieve"

    mock_router_llm = MagicMock()
    mock_router_llm.with_structured_output.return_value = mock_router_llm
    mock_router_llm.invoke.return_value = mock_router_decision
    mock_router_llm.return_value = mock_router_decision

    # 2. Mock Vector Store to return a document (so we bypass rewrite loop)
    mock_vs = MagicMock()
    mock_doc = MagicMock()
    mock_doc.page_content = "Sentinel configuration guide."
    mock_doc.metadata = {}
    mock_vs.search.return_value = [mock_doc]

    # 3. Mock Grader LLM to grade document as 'yes' (relevant)
    mock_grade = MagicMock()
    mock_grade.binary_score = "yes"

    mock_grader_llm = MagicMock()
    mock_grader_llm.with_structured_output.return_value = mock_grader_llm
    mock_grader_llm.invoke.return_value = mock_grade
    mock_grader_llm.return_value = mock_grade

    # 4. Mock Generator LLM to raise exception
    mock_gen_llm = MagicMock()
    mock_gen_llm.invoke.side_effect = RuntimeError("Generation Timeout")
    mock_gen_llm.side_effect = RuntimeError("Generation Timeout")

    # We use a custom get_llm patch that returns different LLM mocks based on the node
    def get_llm_side_effect(api_key=None, provider=None):
        # We can inspect call context, but simpler: return mock_gen_llm if it is called
        # for generation, or grader/router mock otherwise.
        # Actually, to make it robust, we can mock it per-node.
        pass

    with (
        patch("src.app.graph.router.get_llm", return_value=mock_router_llm),
        patch("src.app.graph.nodes.get_vector_store", return_value=mock_vs),
        patch("src.app.graph.nodes.get_llm") as mock_get_llm,
    ):
        # Side effect logic:
        # First call in grade_documents node: returns grader LLM
        # Second call in generate node: returns generator LLM (which throws error)
        mock_get_llm.side_effect = [mock_grader_llm, mock_gen_llm]

        workflow = get_workflow()
        initial_state = {
            "question": "How to configure Sentinel?",
            "generation": "",
            "documents": [],
            "steps": ["received_query"],
            "route": "",
            "retry_count": 0,
        }

        result = await workflow.ainvoke(initial_state)

        # The workflow should execute: router -> retrieve -> grade -> generate (fails)
        assert "steps" in result
        assert "router" in result["steps"]
        assert "retrieve_documents" in result["steps"]
        assert "grade_documents" in result["steps"]
        assert "generate_answer" in result["steps"]
        assert "error_fallback" in result["steps"]
        assert "internal system error" in result["generation"]
