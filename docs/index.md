# Vortex AI Orchestrator

Welcome to the official documentation portal for **Vortex**, a production-grade, state-of-the-art **Corrective RAG (CRAG) Agentic Orchestrator** designed for automated IT support and troubleshooting.

Vortex is engineered to resolve complex customer queries for the *Cortex* serverless pipeline and *Sentinel* infrastructure monitoring systems using local semantic search, dynamic LLM routers, self-grading pipelines, query rewriting loops, and advanced caching.

---

## 🚀 Key Architectural Highlights

*   **Self-Corrective RAG (CRAG)**: LangGraph state machine dynamically grades retrieved documentation relevance, filters out noise, and initiates rewrite loops for failed queries.
*   **Real-time SSE Streaming**: High-performance Server-Sent Events (SSE) streaming API (`POST /api/v1/chat/stream`) yielding token-by-token generation chunks and final structured references.
*   **Multi-Tenant Isolation**: Physical namespace partitioning for ChromaDB collections (`vortex_kb_{tenant_id}`) and dynamic cache lookup isolating tenant context.
*   **In-Memory Ingestion API**: Endpoint (`POST /api/v1/documents`) supporting hot-loading of `.md` and `.pdf` files directly into tenant vector stores.
*   **Bring Your Own Key (BYOK)**: Supports dynamic, request-level API credentials and provider routing via HTTP headers (`Authorization`, `X-API-Key`, `X-Provider`).
*   **Zero-Cost Local Semantic Cache**: Persistent ChromaDB-backed similarity cache using a shared local Sentence-Transformers embeddings model. It features provider-level and tenant-level partition isolation to avoid context leaks.
*   **Chaos Engineering Resilience**: Complete exception shielding across all graph nodes (ChromaDB down, LLM timeouts, grading exceptions) with fast-bypass routing to fallbacks, guaranteeing zero HTTP 500 crashes.
*   **Model-Agnostic Engine**: Native support for Google Gemini, Anthropic Claude, and local Ollama models with seamless environment-level fallback.
*   **Observability**: Integrated OpenTelemetry/OpenInference telemetry compatible with Arize Phoenix for step-by-step agent execution tracing.

---

## 🛠️ Technology Stack

| Layer | Technology | Description |
| :--- | :--- | :--- |
| **Runtime** | Python 3.12 / 3.13 / 3.14 | High-performance async runtime |
| **Web Framework** | FastAPI (AsyncIO) | ASGI web server for fast API delivery |
| **Agent Engine** | LangGraph & LangChain | Stateful multi-actor graph orchestration |
| **Vector Store** | ChromaDB (Embedded) | Persistent vector index for local documents |
| **Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | CPU-friendly embeddings for zero cost |
| **Observability** | OpenTelemetry + Arize Phoenix | Distributed tracing and LLM evaluation |
| **Build & Tooling** | Hatchling, Ruff, Mypy, pytest | Standardized modern Python developer experience |

---

## 📖 Navigating the Documentation

Use the tabs above or the side menu to explore:

*   **[Architecture](architecture.md)**: Deep dive into the LangGraph state machine, nodes, and transition routing.
*   **[Bring Your Own Key](features/byok.md)**: How request-level header extraction and LLM factories are implemented.
*   **[Semantic Caching](features/caching.md)**: In-depth view of the zero-cost ChromaDB similarity caching mechanism.
*   **[Resilience & Chaos](features/resilience.md)**: Exception handling, state-level error propagation, and recovery.
*   **[Developer Guide](developer-guide.md)**: Local installation, configuration, testing, and CI/CD setup.
