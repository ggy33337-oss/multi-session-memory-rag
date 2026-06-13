from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    conversation_path: Path = Path("data/conversation.json")
    faiss_index_path: Path = Path("data/faiss.index")
    vector_map_path: Path = Path("data/vector_map.json")

    recent_turns: int = 5
    retrieve_top_k: int = 3

    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-v4"
    embedding_dimension: int = 1024

    llm_provider: str = "openai"
    llm_model: str = "qwen-plus"

    openai_api_key: str | None = None
    openai_base_url: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
