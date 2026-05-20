# Bring Your Own Key (BYOK) & AI Flexibility

Vortex features a highly flexible, multi-provider model factory that enables dynamic, request-level authentication. Rather than relying solely on server-side environment variables, client applications can supply their own API keys and choose their preferred AI model provider on the fly.

---

## 🔑 Header-Based Injection

When a client makes a request to the `/api/v1/chat` endpoint, Vortex inspects the HTTP headers to extract:
*   **API Key**: Extracted from the standard `Authorization: Bearer <key>` header or the custom `X-API-Key` header.
*   **LLM Provider**: Extracted from the `X-Provider` header. Supported providers are:
    *   `gemini` (Google Gemini)
    *   `anthropic` (Anthropic Claude)
    *   `ollama` (Local Ollama models)

### Example Request Headers

```http
POST /api/v1/chat HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Authorization: Bearer your-custom-gemini-api-key
X-Provider: gemini

{
  "query": "How to restart Sentinel monitoring service?"
}
```

---

## 🏭 Dynamic LLM Factory (`get_llm`)

Inside `src/app/core/llm.py`, the `get_llm` function acts as a centralized factory. It is cached using `functools.lru_cache` to avoid repeated instantiation overhead while supporting dynamic parameters:

```python
@lru_cache(maxsize=32)
def get_llm(
    api_key: str | None = None,
    provider: str | None = None,
) -> BaseChatModel:
    ...
```

### Routing and Fallback Mechanics

1.  **Provider Selection**: The function matches the requested provider. If no provider is specified via the `X-Provider` header, it defaults to the server-side configuration (`settings.llm_provider`).
2.  **API Key Resolution**:
    *   If a client-supplied key is present, it is injected directly into the LLM initializer.
    *   If no key is supplied, the factory falls back to the server's environment keys (e.g. `settings.gemini_api_key`), ensuring backward compatibility and easy developer onboarding.
3.  **Model Configuration**:
    *   **Gemini**: Instantiates `ChatGoogleGenerativeAI` with `gemini-1.5-pro` (or custom models).
    *   **Anthropic**: Instantiates `ChatAnthropic` with `claude-3-5-sonnet-latest`.
    *   **Ollama**: Instantiates `ChatOllama` mapping to local endpoints (e.g. `llama3`).

---

## 🔒 Security and Isolation

*   **No Persistence**: Client-provided API keys are transient and stored in the short-lived LangGraph `AgentState` for the duration of the request. They are never written to disk or recorded in the semantic cache.
*   **Validation**: Supported providers are strictly validated against a white list. Unsupported providers trigger an immediate `400 Bad Request` HTTP exception.
