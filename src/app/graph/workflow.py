"""
Workflow — Compiles the Corrective RAG state machine.

Graph topology:

    START → router
    router ──[needs_docs]──→ retrieve → grade_documents
    router ──[general]─────→ direct_response → END

    grade_documents ──[valid]───→ generate → END
    grade_documents ──[invalid]─→ rewrite_query

    rewrite_query ──[retries < max]──→ retrieve
    rewrite_query ──[retries >= max]─→ fallback → END
"""

from langgraph.graph import END, StateGraph

from src.app.core.config import settings
from src.app.graph.nodes import (
    direct_response_node,
    fallback_node,
    generate_node,
    grade_documents_node,
    retrieve_node,
    rewrite_query_node,
)
from src.app.graph.router import router_node
from src.app.graph.state import AgentState

# ── Conditional edge functions ──────────────────────────────────────────


def route_query(state: AgentState) -> str:
    """Route based on the Router Node's classification."""
    if state.get("error") or state.get("route") == "fallback":
        return "fallback"
    return state["route"]  # "retrieve" or "direct"


def decide_to_generate(state: AgentState) -> str:
    """
    After grading, decide whether to generate an answer or rewrite the query.
    Returns 'generate' if there are relevant documents, 'rewrite_query' otherwise.
    """
    if state.get("error"):
        return "fallback"
    if state["documents"]:
        return "generate"
    return "rewrite_query"


def check_retry_limit(state: AgentState) -> str:
    """
    After rewriting, decide whether to retry retrieval or fall back.
    Compares retry_count against the configured max_rewrite_retries.
    """
    if state.get("error"):
        return "fallback"
    if state.get("retry_count", 0) >= settings.max_rewrite_retries:
        return "fallback"
    return "retrieve"


# ── Graph builder ───────────────────────────────────────────────────────


def get_workflow():
    """
    Builds and compiles the Corrective RAG StateGraph workflow.
    """
    workflow = StateGraph(AgentState)

    # ── Define nodes ────────────────────────────────────────────────────
    workflow.add_node("router", router_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade_documents", grade_documents_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("direct_response", direct_response_node)
    workflow.add_node("rewrite_query", rewrite_query_node)
    workflow.add_node("fallback", fallback_node)

    # ── Entry point ─────────────────────────────────────────────────────
    workflow.set_entry_point("router")

    # ── Router → retrieve or direct_response ────────────────────────────
    workflow.add_conditional_edges(
        "router",
        route_query,
        {
            "retrieve": "retrieve",
            "direct": "direct_response",
            "fallback": "fallback",
        },
    )

    # ── RAG pipeline ────────────────────────────────────────────────────
    workflow.add_edge("retrieve", "grade_documents")

    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {
            "generate": "generate",
            "rewrite_query": "rewrite_query",
            "fallback": "fallback",
        },
    )

    # ── Rewrite loop with retry protection ──────────────────────────────
    workflow.add_conditional_edges(
        "rewrite_query",
        check_retry_limit,
        {
            "retrieve": "retrieve",
            "fallback": "fallback",
        },
    )

    # ── Terminal edges ──────────────────────────────────────────────────
    workflow.add_edge("generate", END)
    workflow.add_edge("direct_response", END)
    workflow.add_edge("fallback", END)

    return workflow.compile()
