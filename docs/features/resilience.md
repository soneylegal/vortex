# Chaos Engineering & Resilience

In production environments, external APIs and local databases can fail. Vortex implements defensive programming principles, exception shielding, and dynamic routing to guarantee that the orchestrator degrades gracefully without crashing the FastAPI server or returning HTTP 500 errors.

---

## 🛡️ Exception Shielding at Node Level

Every node in the Corrective RAG LangGraph workflow is wrapped in exception shielding blocks. 

```python
try:
    # Node logic (LLM invocation, database queries)
except Exception as e:
    logger.error(f"Node failed: {e}", exc_info=True)
    return {
        "error": str(e),
        # ... fallback state keys
    }
```

### Fault-Tolerant Behaviors:

*   **Router Failure**: If the router LLM times out or is unreachable, the system catches the error, sets `route` to `"fallback"`, and populates `error` in the state.
*   **Vector Database Offline**: If ChromaDB is unreachable, the `retrieve` node catches the exception, registers `error` in the state, and clears the document list.
*   **Grading Failure**: If the LLM grading step fails, the document list is cleared and the error is propagated.
*   **Generation Failures**: If the generator LLM fails, the system returns a polite, pre-formatted error message directly to the user rather than throwing an exception.

---

## 🚦 State-Driven Fallback Routing

When an exception occurs in a RAG pipeline node (e.g., retrieval or grading), we want to abort the workflow immediately rather than attempting useless retries. 

We accomplish this by checking the `error` state in the graph's conditional routing edges:

```python
def decide_to_generate(state: AgentState) -> str:
    if state.get("error"):
        return "fallback"  # Route immediately to fallback node
    if state["documents"]:
        return "generate"
    return "rewrite_query"
```

This bypass is applied to all decision points:
1.  **`route_query`**: Routes the router to `"fallback"` if `error` is present.
2.  **`decide_to_generate`**: Bypasses rewrite loops and routes grading output to `"fallback"` on error.
3.  **`check_retry_limit`**: Directs rewrites to `"fallback"` on error.

---

## 👾 Chaos Verification Suite (`tests/test_chaos.py`)

Vortex is guarded by a suite of integration tests designed to simulate severe backend infrastructure failures:

*   **`test_chaos_router_llm_failure`**: Verifies that when the LLM is dead at the router stage, the system returns an internal error message with a `"fallback"` route.
*   **`test_chaos_chromadb_offline`**: Asserts that if ChromaDB crashes, the system skips document grading/generation and returns a friendly database error message.
*   **`test_chaos_generate_llm_failure`**: Verifies that when the generator LLM times out, the system exits gracefully returning a polite error response.
