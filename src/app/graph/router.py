"""
Router Node — LLM-based query classifier.

Classifies incoming queries into:
  - "retrieve": The query requires technical documentation (Cortex/Sentinel manuals).
  - "direct":   The query is a general question that can be answered without RAG.
"""

import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.app.core.llm import get_llm
from src.app.graph.state import AgentState

logger = logging.getLogger(__name__)


class RouteDecision(BaseModel):
    """Structured output for the router classification."""

    route: str = Field(
        description=(
            "Route the query to 'retrieve' if it requires technical documentation "
            "about IT infrastructure, Cortex, or Sentinel systems. "
            "Route to 'direct' if it is a general or conversational question."
        )
    )


def router_node(state: AgentState) -> dict[str, Any]:
    """
    Classify the user query as needing document retrieval or a direct LLM response.

    Uses a structured LLM call to produce a deterministic routing decision,
    stored in state["route"] for downstream conditional edges and API observability.
    """
    question = state["question"]
    steps = list(state.get("steps", []))
    steps.append("router")

    try:
        llm = get_llm(api_key=state.get("api_key"), provider=state.get("provider"))
        structured_llm = llm.with_structured_output(RouteDecision)

        system = (
            "You are a query classifier for an IT infrastructure support system.\n"
            "The knowledge base contains technical manuals for two systems:\n"
            "  - Cortex: A serverless data pipeline (Lambda, API Gateway, DynamoDB).\n"
            "  - Sentinel: An infrastructure monitoring and alerting platform.\n\n"
            "Classify the user's question:\n"
            "  - Reply 'retrieve' if the question is about "
            "errors, troubleshooting, configuration, "
            "architecture, or any technical topic related "
            "to these systems.\n"
            "  - Reply 'direct' if the question is general, "
            "conversational, or unrelated to IT infrastructure "
            "(e.g., 'What is 2+2?', 'Tell me a joke')."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                ("human", "{question}"),
            ]
        )

        chain = prompt | structured_llm
        result = chain.invoke({"question": question})

        return {
            "question": question,
            "route": result.route,  # type: ignore[union-attr]
            "steps": steps,
        }
    except Exception as e:
        logger.error(f"Router node failed: {e}", exc_info=True)
        return {
            "question": question,
            "route": "fallback",
            "error": str(e),
            "steps": steps,
        }
