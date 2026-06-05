import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from src.app.core.config import settings
from src.app.core.dependencies import get_agent_workflow
from src.app.core.rate_limit import limiter
from src.app.services.cache import get_semantic_cache
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

    # Check semantic cache if enabled and this is a single-turn request (no session_id)
    if settings.enable_semantic_cache and not payload.session_id:
        cached = get_semantic_cache().lookup(
            payload.query, provider=provider, tenant_id=payload.tenant_id
        )
        if cached:
            sources = [
                SourceDocument(content=src["content"], metadata=src["metadata"])
                for src in cached.get("sources", [])
            ]
            steps = list(cached.get("steps", []))
            if "semantic_cache_hit" not in steps:
                steps = ["semantic_cache_hit"] + steps

            return ChatResponse(
                answer=cached["answer"],
                sources=sources,
                steps=steps,
                route=cached["route"],
            )

    try:
        # Generate session ID if not provided for checkpoint isolation
        session_id = payload.session_id or f"transient-{uuid.uuid4()}"
        config: RunnableConfig = {"configurable": {"thread_id": session_id}}

        initial_state: dict[str, Any] = {
            "question": payload.query,
            "api_key": api_key,
            "provider": provider,
            "tenant_id": payload.tenant_id,
        }

        result = await workflow.ainvoke(initial_state, config=config)

        sources = [
            SourceDocument(content=doc.page_content, metadata=doc.metadata)
            for doc in result.get("documents", [])
        ]

        # Update cache if enabled and this is a single-turn request
        if settings.enable_semantic_cache and not payload.session_id:
            serialized_sources = [
                {"content": src.content, "metadata": src.metadata} for src in sources
            ]
            get_semantic_cache().update(
                query=payload.query,
                answer=result.get("generation", "I could not generate an answer."),
                sources=serialized_sources,
                steps=result.get("steps", []),
                route=result.get("route"),
                provider=provider,
                tenant_id=payload.tenant_id,
            )

        return ChatResponse(
            answer=result.get("generation", "I could not generate an answer."),
            sources=sources,
            steps=result.get("steps", []),
            route=result.get("route", ""),
        )
    except Exception as e:
        logger.error("Workflow execution failed", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/chat/stream")
@limiter.limit("10/minute")
async def chat_stream_endpoint(
    request: Request,
    payload: ChatRequest,
    workflow: CompiledStateGraph = Depends(get_agent_workflow),
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    x_provider: str | None = Header(default=None),
):
    """
    Submit a question to the Vortex workflow and stream the response
    token-by-token via SSE.
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

    # Generate session ID if not provided for checkpoint isolation
    session_id = payload.session_id or f"transient-{uuid.uuid4()}"
    config: RunnableConfig = {"configurable": {"thread_id": session_id}}

    initial_state: dict[str, Any] = {
        "question": payload.query,
        "api_key": api_key,
        "provider": provider,
        "tenant_id": payload.tenant_id,
    }

    async def event_generator():
        try:
            final_state = {}
            async for event in workflow.astream_events(
                initial_state, config=config, version="v2"
            ):
                kind = event["event"]

                # 1. Yield stream tokens from the generation step
                if kind == "on_chat_model_stream" and "generate_answer" in event.get(
                    "tags", []
                ):
                    chunk = event["data"].get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        token_data = {"event": "token", "text": chunk.content}
                        yield f"data: {json.dumps(token_data)}\n\n"

                # 2. Capture final state
                elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                    final_state = event["data"].get("output", {})

            # 3. Yield metadata payload at completion
            sources = [
                {"content": doc.page_content, "metadata": doc.metadata}
                for doc in final_state.get("documents", [])
            ]
            metadata_payload = {
                "event": "metadata",
                "sources": sources,
                "steps": final_state.get("steps", []),
                "route": final_state.get("route", ""),
            }
            yield f"data: {json.dumps(metadata_payload)}\n\n"

        except Exception as err:
            logger.error("Error during streaming generation", exc_info=True)
            yield f"data: {json.dumps({'event': 'error', 'text': str(err)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
