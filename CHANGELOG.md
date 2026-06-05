# CHANGELOG



## v0.5.0 (2026-06-05)

### Chore

* chore: add python-multipart to dependencies ([`d563b5e`](https://github.com/soneylegal/vortex/commit/d563b5eeb84c5376788aa4ab2e59ab5993ab5bbf))

* chore: add langchain-text-splitters explicitly to dependencies ([`8aedfd0`](https://github.com/soneylegal/vortex/commit/8aedfd0d352e23ad3d2bf5b7dd2806b35394df86))

* chore: add docker targets to Makefile for unified verification inside container ([`bfde717`](https://github.com/soneylegal/vortex/commit/bfde717b85a47496a5d2f534920eb1fcf49ead2b))

* chore: implement multi-stage Docker build targeting development stage ([`3a9c8e0`](https://github.com/soneylegal/vortex/commit/3a9c8e0acd241e16d490219b0c42572ab60ba41b))

* chore: add pypdf dependency for PDF document support ([`5bc1d13`](https://github.com/soneylegal/vortex/commit/5bc1d1329112a314d0de5ea269374c14d873b1a6))

### Documentation

* docs: update developer guide and readme, fix style formatting, mypy types and mock embeddings ([`bc70d7d`](https://github.com/soneylegal/vortex/commit/bc70d7d591b3f3adc1d0bd9ac975d80791aec000))

### Feature

* feat: register documents router in main.py ([`a61ddf1`](https://github.com/soneylegal/vortex/commit/a61ddf1da7dbd01ef5ecb7102a0ffba0b601c312))

* feat: add api/v1/documents endpoint supporting markdown and PDF upload and ingestion ([`ac8c7d1`](https://github.com/soneylegal/vortex/commit/ac8c7d131394ceb31f469fdefa9d79fe357a4633))

* feat: add post chat/stream sse endpoint and support session checkpointers and cache bypassing ([`4cfe694`](https://github.com/soneylegal/vortex/commit/4cfe694e18cca197e28f0052ed27ace54b1c973c))

* feat: add tenant_id and session_id to ChatRequest schema and add DocumentUploadResponse ([`44a0c37`](https://github.com/soneylegal/vortex/commit/44a0c3765695f9fddf7f97d872e2995ad2b4de51))

* feat: refactor all graph nodes to be async with history support and tag tracking ([`e5b26e6`](https://github.com/soneylegal/vortex/commit/e5b26e61afbd2bb8061cc653560b2609fc2319b4))

* feat: isolate semantic cache lookup and updates by tenant_id ([`a0eec09`](https://github.com/soneylegal/vortex/commit/a0eec09d20ee9a1071449cc09431c7c3824ea9be))

* feat: partition VectorStoreService by tenant using dynamic collections ([`0916ade`](https://github.com/soneylegal/vortex/commit/0916adea2c1c58f14d58b055e2d7ebe7233c61ed))

* feat: compile StateGraph with MemorySaver and update AgentState with history and tenant_id ([`84c268f`](https://github.com/soneylegal/vortex/commit/84c268fa4a3d02882566abbe6e1e60aa22053c38))

### Test

* test: use real Document in chaos generation test for serialization ([`138e71c`](https://github.com/soneylegal/vortex/commit/138e71cca0f9e5b58e113a8ce7661cd87195c580))

* test: align chaos tests with async workflow changes ([`4a50ed6`](https://github.com/soneylegal/vortex/commit/4a50ed6a62b97a081e2a35e8b0679beb2ae052f8))

* test: refactor fallback test to be async ([`2b33ca7`](https://github.com/soneylegal/vortex/commit/2b33ca7a14d833be4d99486299a6fdedfdc20a27))

* test: add test suite v0.5.0 and fix semantic cache lookup filters ([`b6d4cfd`](https://github.com/soneylegal/vortex/commit/b6d4cfde3eed802a8a7584a885b8dec3cfcf384d))

### Unknown

* Merge pull request #1 from soneylegal/feat/v0.5.0-streaming-tenancy

Feat/v0.5.0 streaming tenancy ([`fa7fc22`](https://github.com/soneylegal/vortex/commit/fa7fc223427507f04c5eefe694e57f68e3b02ddd))


## v0.4.0 (2026-05-30)

### Chore

* chore(release): v0.4.0 [skip ci] ([`5906ab4`](https://github.com/soneylegal/vortex/commit/5906ab42756b66e96e930b208ba25dfbdf15e060))

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
