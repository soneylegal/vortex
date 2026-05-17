import logging

from fastapi import FastAPI, HTTPException

from src.app.core.config import settings
from src.app.graph.workflow import get_workflow
from src.shared.schemas import ChatRequest, ChatResponse, SourceDocument

logger = logging.getLogger(__name__)

# ── OpenTelemetry / Arize Phoenix (optional, self-hosted) ───────────────
if settings.phoenix_collector_endpoint:
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        endpoint = f"{settings.phoenix_collector_endpoint}/v1/traces"
        tracer_provider = TracerProvider()
        tracer_provider.add_span_processor(
            SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )
        trace.set_tracer_provider(tracer_provider)
        LangChainInstrumentor().instrument()
        logger.info("Phoenix tracing enabled → %s", endpoint)
    except Exception:
        logger.warning(
            "Failed to initialize Phoenix tracing. "
            "The app will run without observability.",
            exc_info=True,
        )

# ── FastAPI Application ─────────────────────────────────────────────────
app = FastAPI(
    title="Vortex — Agentic RAG Orchestrator",
    version="0.1.0",
    description=(
        "A production-ready Agentic RAG Orchestrator featuring a self-corrective "
        "LangGraph workflow with model-agnostic LLM support."
    ),
)

# Initialize graph workflow
workflow = get_workflow()


@app.get("/health")
async def health_check():
    """Liveness probe."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Submit a question to the Vortex agentic workflow.

    The Router Node classifies the query and dispatches it to either:
    - The RAG pipeline (retrieve → grade → generate) for technical questions.
    - A direct LLM response for general queries.
    """
    try:
        initial_state = {
            "question": request.query,
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
