from typing import TypedDict

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
    """

    question: str
    generation: str
    documents: list[Document]
    steps: list[str]
    route: str
    retry_count: int
