from functools import lru_cache

from langgraph.graph.state import CompiledStateGraph

from src.app.graph.workflow import get_workflow


@lru_cache
def get_workflow_instance() -> CompiledStateGraph:
    """
    Singleton factory for the LangGraph workflow.
    Cached to prevent recompilation on every request.
    """
    return get_workflow()


def get_agent_workflow() -> CompiledStateGraph:
    """
    FastAPI dependency that returns the compiled workflow.
    Can be overridden in tests.
    """
    return get_workflow_instance()
