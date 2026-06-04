"""
Graph Nodes — Processing steps for the Corrective RAG workflow.

Each node receives the current AgentState, performs its operation,
and returns a partial state update dict that LangGraph merges back.
"""

import asyncio
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


async def retrieve_node(state: AgentState) -> dict[str, Any]:
    """Retrieve documents from ChromaDB based on the current question."""
    question = state["question"]
    tenant_id = state.get("tenant_id")
    steps = list(state.get("steps", []))
    steps.append("retrieve_documents")

    try:
        vs = get_vector_store()
        docs = await asyncio.to_thread(vs.search, question, tenant_id=tenant_id)
        return {"documents": docs, "question": question, "steps": steps}
    except Exception as e:
        logger.error("Retrieve node failed: %s", e, exc_info=True)
        return {
            "documents": [],
            "question": question,
            "error": str(e),
            "steps": steps,
        }


async def grade_documents_node(state: AgentState) -> dict[str, Any]:
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

        async def _grade_single_doc(doc):
            try:
                score = await retrieval_grader.ainvoke(
                    {"question": question, "document": doc.page_content}
                )
                if score.binary_score == "yes":  # type: ignore[union-attr]
                    return doc
            except Exception as grade_err:
                logger.warning("Failed to grade document: %s", grade_err)
            return None

        # Concurrently grade all retrieved documents
        graded_results = await asyncio.gather(
            *(_grade_single_doc(d) for d in documents)
        )
        filtered_docs = [d for d in graded_results if d is not None]

        return {"documents": filtered_docs, "question": question, "steps": steps}
    except Exception as e:
        logger.error("Grade documents node failed: %s", e, exc_info=True)
        return {
            "documents": [],
            "question": question,
            "error": str(e),
            "steps": steps,
        }


async def generate_node(state: AgentState) -> dict[str, Any]:
    """Generate the final answer using RAG context from graded documents."""
    question = state["question"]
    documents = state["documents"]
    steps = list(state.get("steps", []))
    steps.append("generate_answer")

    try:
        llm = get_llm(api_key=state.get("api_key"), provider=state.get("provider"))
        
        # Build history string
        history = state.get("history") or []
        history_str = ""
        for turn in history:
            history_str += f"User: {turn.get('question', '')}\nAssistant: {turn.get('generation', '')}\n\n"

        prompt = ChatPromptTemplate.from_template(
            "You are an expert IT infrastructure support "
            "assistant for the Cortex and Sentinel platforms. "
            "Use the following conversation history and retrieved context to answer "
            "the question. If you don't know the answer, "
            "say so. Be concise and actionable.\n\n"
            "Conversation History:\n{history}\n"
            "Question: {question}\n"
            "Context: {context}\n"
            "Answer:"
        )

        docs_content = "\n\n".join(doc.page_content for doc in documents)
        rag_chain = prompt | llm

        generation = await rag_chain.ainvoke(
            {"context": docs_content, "question": question, "history": history_str},
            config={"tags": ["generate_answer"]}
        )

        # Update history
        new_history = list(history)
        new_history.append({"question": question, "generation": str(generation.content)})

        return {
            "documents": documents,
            "question": question,
            "generation": str(generation.content),
            "steps": steps,
            "history": new_history,
        }
    except Exception as e:
        logger.error("Generate node failed: %s", e, exc_info=True)
        fallback_gen = (
            "I'm sorry, but I encountered an internal system error while "
            "generating the answer. Please try again later or consult "
            "the system administrators."
        )
        history = state.get("history") or []
        new_history = list(history)
        new_history.append({"question": question, "generation": fallback_gen})
        return {
            "documents": documents,
            "question": question,
            "generation": fallback_gen,
            "steps": steps + ["error_fallback"],
            "history": new_history,
        }


async def direct_response_node(state: AgentState) -> dict[str, Any]:
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
        
        # Build history string
        history = state.get("history") or []
        history_str = ""
        for turn in history:
            history_str += f"User: {turn.get('question', '')}\nAssistant: {turn.get('generation', '')}\n\n"

        prompt = ChatPromptTemplate.from_template(
            "You are a helpful IT support assistant. Answer the following question "
            "directly and concisely, taking into account the conversation history if relevant.\n\n"
            "Conversation History:\n{history}\n"
            "Question: {question}\n"
            "Answer:"
        )

        chain = prompt | llm
        generation = await chain.ainvoke(
            {"question": question, "history": history_str},
            config={"tags": ["generate_answer"]}
        )

        # Update history
        new_history = list(history)
        new_history.append({"question": question, "generation": str(generation.content)})

        return {
            "question": question,
            "generation": str(generation.content),
            "documents": [],
            "steps": steps,
            "history": new_history,
        }
    except Exception as e:
        logger.error("Direct response node failed: %s", e, exc_info=True)
        fallback_gen = (
            "I'm sorry, but I encountered an internal system error while "
            "answering your question. Please try again later or consult "
            "the system administrators."
        )
        history = state.get("history") or []
        new_history = list(history)
        new_history.append({"question": question, "generation": fallback_gen})
        return {
            "question": question,
            "generation": fallback_gen,
            "documents": [],
            "steps": steps + ["error_fallback"],
            "history": new_history,
        }


async def rewrite_query_node(state: AgentState) -> dict[str, Any]:
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
        better_question = await question_rewriter.ainvoke({"question": question})

        return {
            "documents": state["documents"],
            "question": str(better_question.content),
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


async def fallback_node(state: AgentState) -> dict[str, Any]:
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

    # Append to history
    history = state.get("history") or []
    new_history = list(history)
    new_history.append({"question": question, "generation": generation})

    return {
        "question": question,
        "generation": generation,
        "documents": [],
        "steps": steps,
        "history": new_history,
    }
