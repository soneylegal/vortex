from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.documents import Document

from src.app.graph.workflow import get_workflow


@pytest.fixture(autouse=True)
def disable_cache():
    """Globally disable semantic cache for validation tests."""
    from src.app.core.config import settings

    original_val = settings.enable_semantic_cache
    settings.enable_semantic_cache = False
    yield
    settings.enable_semantic_cache = original_val


@pytest.mark.asyncio
async def test_validation_successful_rag_path():
    """
    Test a fully successful RAG path:
    1. Router decides 'retrieve'
    2. Document is retrieved
    3. Grader determines document is relevant ('yes')
    4. Generator produces response
    """
    # 1. Mock router to route to 'retrieve'
    mock_router_decision = MagicMock()
    mock_router_decision.route = "retrieve"

    mock_router_llm = MagicMock()
    mock_structured_router = AsyncMock()
    mock_structured_router.return_value = mock_router_decision
    mock_structured_router.ainvoke.return_value = mock_router_decision
    mock_router_llm.with_structured_output.return_value = mock_structured_router

    # 2. Mock Vector Store to return a relevant document
    mock_vs = MagicMock()
    mock_doc = Document(
        page_content="Cortex Error 503 is resolved by checking concurrency limits.",
        metadata={"source": "cortex_manual.md"},
    )
    mock_vs.search.return_value = [mock_doc]

    # 3. Mock Grader LLM to grade document as 'yes' (relevant)
    mock_grade = MagicMock()
    mock_grade.binary_score = "yes"

    mock_grader_llm = MagicMock()
    mock_structured_grader = AsyncMock()
    mock_structured_grader.return_value = mock_grade
    mock_structured_grader.ainvoke.return_value = mock_grade
    mock_grader_llm.with_structured_output.return_value = mock_structured_grader

    # 4. Mock Generator LLM to return generation answer
    mock_gen_response = MagicMock()
    mock_gen_response.content = "To fix Cortex Error 503, increase concurrency limits."
    mock_gen_llm = AsyncMock()
    mock_gen_llm.return_value = mock_gen_response
    mock_gen_llm.ainvoke.return_value = mock_gen_response

    with (
        patch("src.app.graph.router.get_llm", return_value=mock_router_llm),
        patch("src.app.graph.nodes.get_vector_store", return_value=mock_vs),
        patch("src.app.graph.nodes.get_llm") as mock_get_llm,
    ):
        mock_get_llm.side_effect = [mock_grader_llm, mock_gen_llm]

        workflow = get_workflow()
        initial_state = {
            "question": "How to fix Cortex Error 503?",
            "generation": "",
            "documents": [],
            "steps": ["received_query"],
            "route": "",
            "retry_count": 0,
        }

        config = {"configurable": {"thread_id": "test_thread_rag"}}
        result = await workflow.ainvoke(initial_state, config=config)

        # Assert full path: router -> retrieve -> grade -> generate
        assert "router" in result["steps"]
        assert "retrieve_documents" in result["steps"]
        assert "grade_documents" in result["steps"]
        assert "generate_answer" in result["steps"]
        assert "rewrite_query" not in result["steps"]
        assert "fallback" not in result["steps"]
        assert result["route"] == "retrieve"
        assert "increase concurrency limits" in result["generation"]
        assert len(result["documents"]) == 1


@pytest.mark.asyncio
async def test_validation_correction_rewrite_loop():
    """
    Test the corrective rewrite loop:
    1. Router decides 'retrieve'
    2. Vector Store returns a document
    3. Grader determines document is irrelevant ('no')
    4. Rewrite node rewrites query
    5. Second retrieval returns document
    6. Second grading decides 'yes'
    7. Generator produces response
    """
    # 1. Mock router to route to 'retrieve'
    mock_router_decision = MagicMock()
    mock_router_decision.route = "retrieve"

    mock_router_llm = MagicMock()
    mock_structured_router = AsyncMock()
    mock_structured_router.return_value = mock_router_decision
    mock_structured_router.ainvoke.return_value = mock_router_decision
    mock_router_llm.with_structured_output.return_value = mock_structured_router

    # 2. Mock Vector Store to return document
    mock_vs = MagicMock()
    mock_doc_irrelevant = Document(
        page_content="Unrelated info.", metadata={"source": "manual.md"}
    )
    mock_doc_relevant = Document(
        page_content="Sentinel restart details.",
        metadata={"source": "sentinel_manual.md"},
    )
    mock_vs.search.side_effect = [[mock_doc_irrelevant], [mock_doc_relevant]]

    # 3. Mock Grader LLM (returns 'no' first, then 'yes')
    mock_grade_no = MagicMock()
    mock_grade_no.binary_score = "no"
    mock_grade_yes = MagicMock()
    mock_grade_yes.binary_score = "yes"

    mock_grader_llm1 = MagicMock()
    mock_structured_grader1 = AsyncMock()
    mock_structured_grader1.return_value = mock_grade_no
    mock_structured_grader1.ainvoke.return_value = mock_grade_no
    mock_grader_llm1.with_structured_output.return_value = mock_structured_grader1

    mock_grader_llm2 = MagicMock()
    mock_structured_grader2 = AsyncMock()
    mock_structured_grader2.return_value = mock_grade_yes
    mock_structured_grader2.ainvoke.return_value = mock_grade_yes
    mock_grader_llm2.with_structured_output.return_value = mock_structured_grader2

    # 4. Mock Rewrite LLM
    mock_rewritten_query = MagicMock()
    mock_rewritten_query.content = "rewritten query"
    mock_rewrite_llm = AsyncMock()
    mock_rewrite_llm.return_value = mock_rewritten_query
    mock_rewrite_llm.ainvoke.return_value = mock_rewritten_query

    # 5. Mock Generator LLM
    mock_gen_response = MagicMock()
    mock_gen_response.content = "Restart Sentinel."
    mock_gen_llm = AsyncMock()
    mock_gen_llm.return_value = mock_gen_response
    mock_gen_llm.ainvoke.return_value = mock_gen_response

    with (
        patch("src.app.graph.router.get_llm", return_value=mock_router_llm),
        patch("src.app.graph.nodes.get_vector_store", return_value=mock_vs),
        patch("src.app.graph.nodes.get_llm") as mock_get_llm,
    ):
        mock_get_llm.side_effect = [
            mock_grader_llm1,
            mock_rewrite_llm,
            mock_grader_llm2,
            mock_gen_llm,
        ]

        workflow = get_workflow()
        initial_state = {
            "question": "How to restart sentinel?",
            "generation": "",
            "documents": [],
            "steps": ["received_query"],
            "route": "",
            "retry_count": 0,
        }

        config = {"configurable": {"thread_id": "test_thread_rewrite"}}
        result = await workflow.ainvoke(initial_state, config=config)

        # Assert full path:
        # router -> retrieve -> grade -> rewrite -> retrieve -> grade -> generate
        assert "router" in result["steps"]
        assert "retrieve_documents" in result["steps"]
        assert "grade_documents" in result["steps"]
        assert "rewrite_query" in result["steps"]
        assert "generate_answer" in result["steps"]
        assert result["retry_count"] == 1
        assert "Restart Sentinel" in result["generation"]
