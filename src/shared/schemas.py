from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming chat request."""

    query: str = Field(..., description="The user's technical question.")


class SourceDocument(BaseModel):
    """A retrieved document returned as part of the response."""

    content: str
    metadata: dict


class ChatResponse(BaseModel):
    """Chat response including the answer, sources, execution steps, and route taken."""

    answer: str
    sources: list[SourceDocument] = []
    steps: list[str] = []
    route: str | None = Field(
        default=None,
        description="Router decision: 'retrieve' (RAG) or 'direct' (general LLM).",
    )
