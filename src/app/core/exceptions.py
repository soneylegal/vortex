from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class BaseAPIException(Exception):
    """Base exception for API errors."""

    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str,
        type_uri: str = "about:blank",
        **kwargs: Any,
    ):
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.type_uri = type_uri
        self.extras = kwargs


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handles all uncaught exceptions returning RFC 7807 problem details."""
    return JSONResponse(
        status_code=500,
        content={
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An unexpected error occurred processing your request.",
            "instance": str(request.url),
        },
    )


async def api_exception_handler(
    request: Request, exc: BaseAPIException
) -> JSONResponse:
    """Handles custom API exceptions."""
    content = {
        "type": exc.type_uri,
        "title": exc.title,
        "status": exc.status_code,
        "detail": exc.detail,
        "instance": str(request.url),
    }
    if exc.extras:
        content.update(exc.extras)
    return JSONResponse(status_code=exc.status_code, content=content)


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Overrides default FastAPI HTTP exceptions to use RFC 7807."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "about:blank",
            "title": "HTTP Error",
            "status": exc.status_code,
            "detail": str(exc.detail),
            "instance": str(request.url),
        },
    )
