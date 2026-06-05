# Developer Guide

This guide provides step-by-step instructions on setting up, configuring, running, and testing the Vortex AI Orchestrator local environment.

---

## 💻 Local Setup

### 1. Requirements
*   Python 3.12 or 3.13 (Python 3.14 recommended / tested)
*   Virtualenv

### 2. Installation
Clone the repository and install the project in editable mode with development dependencies:

```bash
# Clone the repository
git clone https://github.com/soneylegal/vortex.git
cd vortex

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install package and dev requirements
pip install -e ".[dev]"
```

---

## ⚙️ Configuration (`.env`)

Create a `.env` file in the project root:

```env
# Selected LLM Provider (options: gemini, anthropic, ollama)
LLM_PROVIDER=gemini

# Default API keys (server fallbacks)
GEMINI_API_KEY=AIzaSy...
ANTHROPIC_API_KEY=sk-ant-...

# Storage configuration
CHROMA_PERSIST_DIRECTORY=data/chroma_db

# Caching parameters
ENABLE_SEMANTIC_CACHE=true
SEMANTIC_CACHE_THRESHOLD=0.1

# Graph parameters
MAX_REWRITE_RETRIES=2
```

---

## 📥 Ingesting Knowledge Base Documents

Vortex comes with a persistent vector store. You can programmatically seed the store with documents from Markdown files or technical manuals:

```python
from langchain_core.documents import Document
from src.app.services.vector_store import get_vector_store

vs = get_vector_store()

# Seed document list
docs = [
    Document(
        page_content="Cortex Error 503 is resolved by checking Lambda concurrency limits and restarting.",
        metadata={"source": "cortex_manual.md"}
    ),
    Document(
        page_content="Sentinel monitoring is restarted via: systemctl restart sentinel",
        metadata={"source": "sentinel_guide.md"}
    )
]

vs.add_documents(docs)
print(f"Total documents loaded: {vs.document_count()}")
```

---

## 🏃 Running the Application

Start the FastAPI application server locally:

```bash
uvicorn src.app.main:app --reload --host 0.0.0.0 --port 8000
```

Once running, the interactive Swagger documentation is available at:
*   [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧪 Running Tests

### Local Quality Tools
Vortex is equipped with automated tests verifying routing logic, BYOK headers, semantic cache, vector store, and chaos fallbacks:

```bash
pytest tests/ -v
```

Ensure style and type alignment using Ruff and Mypy before pushing code:

```bash
# Code style linter
ruff check .

# Code formatting checks
ruff format --check .

# Type checker
mypy src/ --ignore-missing-imports
```

### 🐳 Docker Quality Tools
Run the quality suite inside standard development containers:

```bash
# Lint inside container
make docker-lint

# Format and check inside container
make docker-format

# Typecheck inside container
make docker-typecheck

# Run tests inside container
make docker-test

# Run full CI inside container
make docker-ci
```

---

## 👥 Multi-Tenancy & Streaming APIs

Vortex supports dynamic namespace isolation and real-time streaming:

### 1. Document Ingestion API (`POST /api/v1/documents`)
Upload PDF or Markdown files isolated under a specific `tenant_id`:

```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -F "file=@manual.pdf" \
  -F "tenant_id=tenant-alpha"
```

This chunks the document and indexes it into the isolated `vortex_kb_tenant-alpha` collection namespace in ChromaDB.

### 2. Conversation Chat Streaming API (`POST /api/v1/chat/stream`)
Stream responses token-by-token using Server-Sent Events (SSE), maintaining separate session context with `session_id` and isolating data via `tenant_id`:

```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I configure Sentinel?",
    "tenant_id": "tenant-alpha",
    "session_id": "session-123"
  }'
```

---

## 📚 Building the Documentation Portal

To edit and preview this documentation portal locally:

```bash
# Via Makefile (recommended)
make docs          # Local live-reload server (requires venv)
make docker-docs   # Serve docs inside Docker container
```

Access the preview at [http://localhost:8001](http://localhost:8001).

To compile the documentation into static HTML files (suitable for GitHub Pages):

```bash
mkdocs build
```
