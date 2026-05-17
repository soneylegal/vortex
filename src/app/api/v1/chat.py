import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from langgraph.graph.state import CompiledStateGraph

from src.app.core.dependencies import get_agent_workflow
from src.app.core.rate_limit import limiter
from src.shared.schemas import ChatRequest, ChatResponse, SourceDocument

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
async def chat_endpoint(
    request: Request,
    payload: ChatRequest,
    workflow: CompiledStateGraph = Depends(get_agent_workflow),
):
    """
    Submit a question to the Vortex agentic workflow.

    The Router Node classifies the query and dispatches it to either:
    - The RAG pipeline (retrieve → grade → generate) for technical questions.
    - A direct LLM response for general queries.
    """
    try:
        initial_state = {
            "question": payload.query,
            "generation": "",
            "documents": [],
            "steps": ["received_query"],
            "route": "",
            "retry_count": 0,
        }

        result = await workflow.ainvoke(initial_state)

        sources = [
            SourceDocument(content=doc.page_content, metadata=doc.metadata)
            for doc in result.get("documents", [])
        ]

        return ChatResponse(
            answer=result.get("generation", "I could not generate an answer."),
            sources=sources,
            steps=result.get("steps", []),
            route=result.get("route", ""),
        )
    except Exception as e:
        logger.error("Workflow execution failed", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
