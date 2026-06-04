import logging

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.app.api.v1 import chat, documents
from src.app.core.config import settings
from src.app.core.exceptions import (
    BaseAPIException,
    api_exception_handler,
    global_exception_handler,
    http_exception_handler,
)
from src.app.core.logging import setup_logging
from src.app.core.middleware import CorrelationIdMiddleware
from src.app.core.rate_limit import limiter

# ── Structured Logging ──────────────────────────────────────────────────
setup_logging()
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
    version="0.3.0",
    description=(
        "A production-ready Agentic RAG Orchestrator featuring a self-corrective "
        "LangGraph workflow with model-agnostic LLM support."
    ),
)

# ── Middleware ───────────────────────────────────────────────────────────
app.add_middleware(CorrelationIdMiddleware)

# Setup Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Setup Exception Handlers (RFC 7807)
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(BaseAPIException, api_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]


# ── Health Check (expanded) ─────────────────────────────────────────────
@app.get("/health")
async def health_check():
    """
    Liveness and readiness probe.

    Reports connectivity status for ChromaDB and the embeddings model
    in addition to the basic application status.
    """
    chromadb_status = "disconnected"
    model_status = "not_loaded"

    try:
        from src.app.services.vector_store import _instance as vs_instance

        if vs_instance is not None:
            vs_instance.vector_store._collection.count()
            chromadb_status = "connected"
    except Exception:
        logger.warning("Health check: ChromaDB connectivity failed", exc_info=True)

    try:
        from src.app.services.vector_store import _instance as vs_instance

        if vs_instance is not None and vs_instance.embeddings is not None:
            model_status = "loaded"
    except Exception:
        logger.warning("Health check: Model readiness check failed", exc_info=True)

    return {
        "status": "ok",
        "chromadb": chromadb_status,
        "model": model_status,
    }


# ── Metrics Endpoint ────────────────────────────────────────────────────
@app.get("/metrics")
async def metrics_endpoint():
    """
    Expose semantic cache performance metrics.

    Returns hit/miss counts, hit rate percentage, and average lookup latency.
    """
    from src.app.services.metrics import cache_metrics

    return cache_metrics.snapshot()


# Register Routers
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
