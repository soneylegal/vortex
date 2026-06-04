from typing import NotRequired, TypedDict

from langchain_core.documents import Document


class AgentState(TypedDict):
    """
    State representation for the Agentic RAG Workflow.

    Fields:
        question:    The user's original (or rewritten) query.
        generation:  The final generated answer.
        documents:   Retrieved and/or filtered documents from ChromaDB.
        steps:       Ordered list of node names executed (for observability).
        route:       Router decision — "retrieve" or "direct" (for API response).
        retry_count: Number of query-rewrite retries performed (loop protection).
        api_key:     Optional dynamic API key for the LLM provider.
        provider:    Optional dynamic LLM provider (gemini, anthropic, ollama).
    """

    question: str
    generation: str
    documents: list[Document]
    steps: list[str]
    route: str
    retry_count: int
    api_key: NotRequired[str | None]
    provider: NotRequired[str | None]
    error: NotRequired[str | None]
    tenant_id: NotRequired[str | None]
    history: NotRequired[list[dict[str, str]] | None]

