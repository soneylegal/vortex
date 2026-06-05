from langchain_core.documents import Document

from src.app.graph.workflow import check_retry_limit, decide_to_generate, route_query

# ── Router decision tests ───────────────────────────────────────────────


class TestRouteQuery:
    def test_routes_to_retrieve(self):
        """Router classified as 'retrieve' → should route to retrieval pipeline."""
        state = {
            "question": "How to fix Cortex Error 503?",
            "generation": "",
            "documents": [],
            "steps": ["router"],
            "route": "retrieve",
            "retry_count": 0,
        }
        assert route_query(state) == "retrieve"

    def test_routes_to_direct(self):
        """Router classified as 'direct' → should route to direct LLM response."""
        state = {
            "question": "What is 2+2?",
            "generation": "",
            "documents": [],
            "steps": ["router"],
            "route": "direct",
            "retry_count": 0,
        }
        assert route_query(state) == "direct"


# ── Grade → Generate decision tests ────────────────────────────────────


class TestDecideToGenerate:
    def test_generates_with_relevant_docs(self):
        """With graded documents present → should route to generate."""
        state = {
            "question": "How to fix error?",
            "generation": "",
            "documents": [Document(page_content="Fix by restarting the service.")],
            "steps": ["grade_documents"],
            "route": "retrieve",
            "retry_count": 0,
        }
        assert decide_to_generate(state) == "generate"

    def test_rewrites_without_docs(self):
        """With no documents after grading → should route to rewrite."""
        state = {
            "question": "How to fix error?",
            "generation": "",
            "documents": [],
            "steps": ["grade_documents"],
            "route": "retrieve",
            "retry_count": 0,
        }
        assert decide_to_generate(state) == "rewrite_query"


# ── Retry limit tests ──────────────────────────────────────────────────


class TestCheckRetryLimit:
    def test_retries_when_under_limit(self):
        """retry_count < max → should retry retrieval."""
        state = {
            "question": "rewritten question",
            "generation": "",
            "documents": [],
            "steps": ["rewrite_query"],
            "route": "retrieve",
            "retry_count": 0,
        }
        assert check_retry_limit(state) == "retrieve"

    def test_falls_back_when_limit_reached(self):
        """retry_count >= max (default 2) → should fall back gracefully."""
        state = {
            "question": "rewritten question",
            "generation": "",
            "documents": [],
            "steps": ["rewrite_query"],
            "route": "retrieve",
            "retry_count": 2,
        }
        assert check_retry_limit(state) == "fallback"

    def test_falls_back_when_over_limit(self):
        """retry_count > max → should also fall back."""
        state = {
            "question": "rewritten question",
            "generation": "",
            "documents": [],
            "steps": ["rewrite_query"],
            "route": "retrieve",
            "retry_count": 5,
        }
        assert check_retry_limit(state) == "fallback"


# ── Fallback node tests ────────────────────────────────────────────────


class TestFallbackNode:
    async def test_fallback_produces_message(self):
        """Fallback node should return a helpful 'not found' message."""
        from src.app.graph.nodes import fallback_node

        state = {
            "question": "something obscure",
            "generation": "",
            "documents": [],
            "steps": ["rewrite_query"],
            "route": "retrieve",
            "retry_count": 2,
        }
        result = await fallback_node(state)
        assert "knowledge base" in result["generation"].lower()
        assert result["documents"] == []
        assert "fallback" in result["steps"]
