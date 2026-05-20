import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
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
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    x_provider: str | None = Header(default=None),
):
    """
    Submit a question to the Vortex agentic workflow.

    The Router Node classifies the query and dispatches it to either:
    - The RAG pipeline (retrieve → grade → generate) for technical questions.
    - A direct LLM response for general queries.
    """
    provider = x_provider.lower() if x_provider else None
    if provider and provider not in ["gemini", "anthropic", "ollama"]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported LLM provider: {x_provider}. "
                "Supported providers: gemini, anthropic, ollama"
            ),
        )

    api_key = None
    if authorization:
        if authorization.startswith("Bearer "):
            api_key = authorization[7:]
        else:
            api_key = authorization
    elif x_api_key:
        api_key = x_api_key

    try:
        initial_state = {
            "question": payload.query,
            "generation": "",
            "documents": [],
            "steps": ["received_query"],
            "route": "",
            "retry_count": 0,
            "api_key": api_key,
            "provider": provider,
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
