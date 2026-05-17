from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM Settings
    llm_provider: Literal["anthropic", "gemini", "ollama"] = "gemini"

    # API Keys
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None

    # Ollama Settings
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # Model Names
    anthropic_model: str = "claude-3-5-sonnet-20240620"
    gemini_model: str = "gemini-2.5-flash"

    # Vector Store
    chroma_persist_directory: str = "data/chroma_db"

    # Agent Behavior
    max_rewrite_retries: int = 2

    # OpenTelemetry / Arize Phoenix (optional, self-hosted)
    phoenix_collector_endpoint: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
