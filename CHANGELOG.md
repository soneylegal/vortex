# CHANGELOG



## v0.4.0 (2026-05-30)

### Documentation

* docs: add mkdocs material site, architectural pages, and upgrade README badges ([`a008356`](https://github.com/soneylegal/vortex/commit/a0083561a6ef5ebaef2a982c118f51d832d7c0a2))

### Feature

* feat: implement structured JSON logging, telemetry metrics and extended health check

- Add python-json-logger for structured JSON log output
- Add CorrelationIdMiddleware to propagate X-Request-ID across all logs
- Expose GET /metrics endpoint with cache hit/miss rate and avg latency
- Expand GET /health to report ChromaDB connectivity and model readiness
- Migrate f-string logger calls to %-style across graph nodes, router and cache
- Add thread-safe CacheTimer/CacheMetrics service for semantic cache observability
- Expand CI matrix to test Python 3.12, 3.13 and 3.14 ([`4074b07`](https://github.com/soneylegal/vortex/commit/4074b0787b72a7344ab0b899b8af969169334687))

* feat: implement error handling wrappers in graph nodes and add chaos resilience tests ([`c50fc94`](https://github.com/soneylegal/vortex/commit/c50fc94b4b314c84e676fa39d35dd9ca0eb3c04d))


## v0.3.0 (2026-05-20)

### Chore

* chore(release): v0.3.0 [skip ci] ([`7408553`](https://github.com/soneylegal/vortex/commit/7408553a9b2b955352dc621f05d2e87cb89bc2b9))

### Feature

* feat: implement local zero-cost semantic caching using ChromaDB ([`a694d07`](https://github.com/soneylegal/vortex/commit/a694d072a42210c0149a0976aaeb361a348f61cb))


## v0.2.0 (2026-05-20)

### Chore

* chore(release): v0.2.0 [skip ci] ([`af886a9`](https://github.com/soneylegal/vortex/commit/af886a9d96e1c51360174d06dc1b4845bb49fc2d))

### Feature

* feat: add BYOK support and dynamic LLM provider selection via headers ([`bfc627c`](https://github.com/soneylegal/vortex/commit/bfc627cefa1e4f729d474c4eeb5b433af248e7d0))


## v0.1.0 (2026-05-17)

### Chore

* chore(release): v0.1.0 [skip ci] ([`9ff61e6`](https://github.com/soneylegal/vortex/commit/9ff61e68ab6d3de42393b2d82891eea7194e3d08))

* chore: implement semantic release and add apache license ([`de29d2d`](https://github.com/soneylegal/vortex/commit/de29d2db3bcc6c8b4f136c792aeceaf5ff7f42fd))

### Feature

* feat: finalize API endpoints, dependencies and rate limiting ([`37166c4`](https://github.com/soneylegal/vortex/commit/37166c4f30dec754100e7efb93b94fd80beccd13))

* feat: implement Vortex Agentic RAG Orchestrator

- LangGraph workflow with Router → Retrieve → Grade → Generate pipeline
- LLM-based query classifier (Router Node) for intelligent routing
- Self-corrective RAG with rewrite loop and configurable max retries
- Graceful fallback when retrieval is exhausted
- Model-agnostic LLM factory (Gemini free tier, Ollama, Anthropic)
- ChromaDB vector store with lazy singleton initialization
- Realistic Cortex/Sentinel knowledge base documentation
- OpenTelemetry/Arize Phoenix observability integration
- FastAPI server with async workflow execution
- Full test suite (17 tests): agent logic, API, vector store
- CI/CD via GitHub Actions (ruff + mypy + pytest)
- Docker Compose stack (API + Phoenix tracing UI)
- Modern Python tooling: pyproject.toml, ruff, hatchling ([`a8af4b7`](https://github.com/soneylegal/vortex/commit/a8af4b7367858e0fc22421458beb190e81944507))

### Fix

* fix(ci): resolve pipeline errors (PEP 668, mypy, semantic-release build) ([`2cfbe5d`](https://github.com/soneylegal/vortex/commit/2cfbe5d1d990c136ce71d6c321b8523f1a6426ac))
