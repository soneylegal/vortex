import functools

from langchain_core.language_models.chat_models import BaseChatModel

from .config import settings


@functools.lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    """
    Returns the appropriate LLM instance based on configuration.
    Supports Gemini (free), Ollama (local), and Anthropic (paid).

    The instance is cached so that all graph nodes share a single LLM client
    per process, avoiding redundant re-initialization on every node call.
    """
    if settings.llm_provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY must be set to use Gemini. "
                "Get a free key at https://aistudio.google.com/"
            )
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.0,
        )

    elif settings.llm_provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError as exc:
            raise ImportError(
                "Ollama support requires the 'ollama' extra. "
                "Install with: pip install vortex[ollama]"
            ) from exc
        return ChatOllama(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            temperature=0.0,
        )

    elif settings.llm_provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set to use Anthropic.")
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise ImportError(
                "Anthropic support requires the 'anthropic' extra. "
                "Install with: pip install vortex[anthropic]"
            ) from exc
        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            temperature=0.0,
        )

    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
