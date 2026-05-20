# Vortex AI Orchestrator

Welcome to the official documentation portal for **Vortex**, a production-grade, state-of-the-art **Corrective RAG (CRAG) Agentic Orchestrator** designed for automated IT support and troubleshooting.

Vortex is engineered to resolve complex customer queries for the *Cortex* serverless pipeline and *Sentinel* infrastructure monitoring systems using local semantic search, dynamic LLM routers, self-grading pipelines, query rewriting loops, and advanced caching.

---

## 🚀 Key Architectural Highlights

*   **Bring Your Own Key (BYOK)**: Empowers clients with request-level dynamic API credentials and seamless fallback options.
*   **Multi-Provider Flexibility**: Native compatibility with top-tier foundation models (Google Gemini, Anthropic Claude, and local Ollama nodes).
*   **Zero-Cost Local Stack**: Complete development environment running locally with ChromaDB and HuggingFace Sentence-Transformers.
*   **Semantic Caching Layer**: Ultra-fast cosine-similarity cache partitioned by LLM provider to bypass expensive LLM token calls.
*   **Chaos Engineering Resilience**: Built-in exception shielding on graph nodes and state transitions to survive backend service outages.
*   **Modern Observability**: Full instrumentation via OpenInference and OpenTelemetry (compatible with Arize Phoenix).

---

## 🛠️ Technology Stack

Vortex is built with modern, industry-standard technologies:

*   **Orchestration**: [LangGraph](https://github.com/langchain-ai/langgraph) / [LangChain](https://github.com/langchain-ai/langchain)
*   **API Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12+)
*   **Vector Database**: [ChromaDB](https://www.trychroma.com/) (Local persistent storage)
*   **Embeddings Model**: Local `sentence-transformers/all-MiniLM-L6-v2` via HuggingFace
*   **Build System**: [Hatchling](https://hatch.pypa.io/) & [pip]
*   **CI/CD & Release**: Python Semantic Release on GitHub Actions

---

## 📖 Navigating the Documentation

Use the tabs above or the side menu to explore:

*   **[Architecture](architecture.md)**: Deep dive into the LangGraph state machine, nodes, and transition routing.
*   **[Bring Your Own Key](features/byok.md)**: How request-level header extraction and LLM factories are implemented.
*   **[Semantic Caching](features/caching.md)**: In-depth view of the zero-cost ChromaDB similarity caching mechanism.
*   **[Resilience & Chaos](features/resilience.md)**: Exception handling, state-level error propagation, and recovery.
*   **[Developer Guide](developer-guide.md)**: Local installation, configuration, testing, and CI/CD setup.
