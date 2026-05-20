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

### Unit & Integration Tests
Vortex is equipped with 26 automated tests verifying routing logic, BYOK headers, semantic cache, vector store, and chaos fallbacks:

```bash
pytest tests/ -v
```

### Style & Types Check
Ensure style and type alignment using Ruff and Mypy before pushing code:

```bash
# Code style linter
ruff check .

# Code formatting checks
ruff format --check .

# Type checker
mypy src/ --ignore-missing-imports
```

---

## 📚 Building the Documentation Portal

To edit and preview this documentation portal locally:

```bash
# Run local live-reload server
mkdocs serve
```

Access the preview at [http://127.0.0.1:8000](http://127.0.0.1:8000).

To compile the documentation into static HTML files (suitable for GitHub Pages):

```bash
mkdocs build
```
