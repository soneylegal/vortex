"""
Correlation ID Middleware — Assigns a unique request ID to each HTTP request.

The ID is propagated via a ContextVar so that all log messages emitted
during a request automatically include the same correlation identifier,
enabling end-to-end request tracing across structured log output.
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.app.core.logging import request_id_ctx


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Injects a unique ``X-Request-ID`` into every request/response cycle.

    - If the client sends an ``X-Request-ID`` header, it is reused.
    - Otherwise, a new UUID4 is generated.
    - The ID is stored in a ContextVar for structured logging.
    - The ID is returned in the response ``X-Request-ID`` header.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        incoming_id = request.headers.get("x-request-id")
        correlation_id = incoming_id or uuid.uuid4().hex[:16]

        # Set the context variable for structured logging
        token = request_id_ctx.set(correlation_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = correlation_id
            return response
        finally:
            request_id_ctx.reset(token)
