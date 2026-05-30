"""
Graph Nodes — Processing steps for the Corrective RAG workflow.

Each node receives the current AgentState, performs its operation,
and returns a partial state update dict that LangGraph merges back.
"""

import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.app.core.llm import get_llm
from src.app.graph.state import AgentState
from src.app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)


# ── Structured output schema for document grading ───────────────────────
class Grade(BaseModel):
    """Binary score for relevance check."""

    binary_score: str = Field(description="Relevance score 'yes' or 'no'")


# ── Nodes ────────────────────────────────────────────────────────────────


def retrieve_node(state: AgentState) -> dict[str, Any]:
    """Retrieve documents from ChromaDB based on the current question."""
    question = state["question"]
    steps = list(state.get("steps", []))
    steps.append("retrieve_documents")

    try:
        vs = get_vector_store()
        docs = vs.search(question)
        return {"documents": docs, "question": question, "steps": steps}
    except Exception as e:
        logger.error("Retrieve node failed: %s", e, exc_info=True)
        return {
            "documents": [],
            "question": question,
            "error": str(e),
            "steps": steps,
        }


def grade_documents_node(state: AgentState) -> dict[str, Any]:
    """
    Evaluate whether retrieved documents are relevant to the question.

    Uses a structured LLM call to produce a binary 'yes'/'no' grade
    for each document. Only documents graded 'yes' are kept.
    """
    question = state["question"]
    documents = state["documents"]
    steps = list(state.get("steps", []))
    steps.append("grade_documents")

    if state.get("error"):
        return {"documents": [], "question": question, "steps": steps}

    try:
        llm = get_llm(api_key=state.get("api_key"), provider=state.get("provider"))
        structured_llm_grader = llm.with_structured_output(Grade)

        system = (
            "You are a grader assessing relevance of a retrieved "
            "document to a user question.\n"
            "If the document contains keyword(s) or semantic "
            "meaning related to the question, "
            "grade it as relevant.\n"
            "Give a binary score 'yes' or 'no' to indicate "
            "whether the document is relevant."
        )
        grade_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                (
                    "human",
                    "Retrieved document:\n\n{document}\n\nUser question: {question}",
                ),
            ]
        )

        retrieval_grader = grade_prompt | structured_llm_grader

        filtered_docs = []
        for d in documents:
            score = retrieval_grader.invoke(
                {"question": question, "document": d.page_content}
            )
            if score.binary_score == "yes":  # type: ignore[union-attr]
                filtered_docs.append(d)

        return {"documents": filtered_docs, "question": question, "steps": steps}
    except Exception as e:
        logger.error("Grade documents node failed: %s", e, exc_info=True)
        return {
            "documents": [],
            "question": question,
            "error": str(e),
            "steps": steps,
        }


def generate_node(state: AgentState) -> dict[str, Any]:
    """Generate the final answer using RAG context from graded documents."""
    question = state["question"]
    documents = state["documents"]
    steps = list(state.get("steps", []))
    steps.append("generate_answer")

    try:
        llm = get_llm(api_key=state.get("api_key"), provider=state.get("provider"))
        prompt = ChatPromptTemplate.from_template(
            "You are an expert IT infrastructure support "
            "assistant for the Cortex and Sentinel platforms. "
            "Use the following retrieved context to answer "
            "the question. If you don't know the answer, "
            "say so. Be concise and actionable.\n\n"
            "Question: {question}\n"
            "Context: {context}\n"
            "Answer:"
        )

        docs_content = "\n\n".join(doc.page_content for doc in documents)
        rag_chain = prompt | llm

        generation = rag_chain.invoke({"context": docs_content, "question": question})
        return {
            "documents": documents,
            "question": question,
            "generation": generation.content,
            "steps": steps,
        }
    except Exception as e:
        logger.error("Generate node failed: %s", e, exc_info=True)
        return {
            "documents": documents,
            "question": question,
            "generation": (
                "I'm sorry, but I encountered an internal system error while "
                "generating the answer. Please try again later or consult "
                "the system administrators."
            ),
            "steps": steps + ["error_fallback"],
        }


def direct_response_node(state: AgentState) -> dict[str, Any]:
    """
    Handle general queries that don't require RAG retrieval.

    The Router classified this query as 'direct', so we answer
    using the LLM without any document context.
    """
    question = state["question"]
    steps = list(state.get("steps", []))
    steps.append("direct_response")

    try:
        llm = get_llm(api_key=state.get("api_key"), provider=state.get("provider"))
        prompt = ChatPromptTemplate.from_template(
            "You are a helpful IT support assistant. Answer the following question "
            "directly and concisely.\n\n"
            "Question: {question}\n"
            "Answer:"
        )

        chain = prompt | llm
        generation = chain.invoke({"question": question})

        return {
            "question": question,
            "generation": generation.content,
            "documents": [],
            "steps": steps,
        }
    except Exception as e:
        logger.error("Direct response node failed: %s", e, exc_info=True)
        return {
            "question": question,
            "generation": (
                "I'm sorry, but I encountered an internal system error while "
                "answering your question. Please try again later or consult "
                "the system administrators."
            ),
            "documents": [],
            "steps": steps + ["error_fallback"],
        }


def rewrite_query_node(state: AgentState) -> dict[str, Any]:
    """
    Rewrite the query to produce a better vector search.

    Increments retry_count so the workflow can enforce a maximum
    number of rewrite attempts before falling back gracefully.
    """
    question = state["question"]
    retry_count = state.get("retry_count", 0)
    steps = list(state.get("steps", []))
    steps.append("rewrite_query")

    if state.get("error"):
        return {
            "documents": state["documents"],
            "question": question,
            "retry_count": retry_count,
            "steps": steps,
        }

    try:
        llm = get_llm(api_key=state.get("api_key"), provider=state.get("provider"))
        system = (
            "You are a question re-writer that converts an input question to a better "
            "version optimized for vector store retrieval. Reason about the underlying "
            "semantic intent and rephrase for maximum recall."
        )
        re_write_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                (
                    "human",
                    "Here is the initial question:\n\n"
                    "{question}\n\n"
                    "Formulate an improved question.",
                ),
            ]
        )

        question_rewriter = re_write_prompt | llm
        better_question = question_rewriter.invoke({"question": question})

        return {
            "documents": state["documents"],
            "question": better_question.content,
            "retry_count": retry_count + 1,
            "steps": steps,
        }
    except Exception as e:
        logger.error("Rewrite query node failed: %s", e, exc_info=True)
        return {
            "documents": state["documents"],
            "question": question,
            "error": str(e),
            "steps": steps,
        }


def fallback_node(state: AgentState) -> dict[str, Any]:
    """
    Graceful fallback when the rewrite loop is exhausted or error occurs.

    After max_rewrite_retries or error, the agent stops and returns
    a friendly explanation.
    """
    question = state["question"]
    steps = list(state.get("steps", []))
    steps.append("fallback")

    if state.get("error"):
        generation = (
            "I'm sorry, but I encountered an internal system error while "
            "processing your request. Please try again later or consult "
            "the system administrators."
        )
    else:
        generation = (
            "I wasn't able to find relevant documentation in the Cortex/Sentinel "
            "knowledge base to answer your question. Please try rephrasing, or "
            "consult the system administrators for further assistance."
        )

    return {
        "question": question,
        "generation": generation,
        "documents": [],
        "steps": steps,
    }
