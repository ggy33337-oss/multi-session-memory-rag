from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_host: str = "127.0.0.1"
    app_port: int = 8001

    database_url: str = "postgresql://memory_user:memory_password@127.0.0.1:5432/memory_rag"

    document_dir: Path = Path("data/documents/uploads")

    recent_turns: int = 5
    retrieve_top_k: int = 3
    document_retrieve_top_k: int = 3
    document_chunk_size: int = 700
    document_chunk_overlap: int = 100
    document_similarity_threshold: float = 0.35

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

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            init_settings,
            dotenv_settings,
            env_settings,
            file_secret_settings,
        )


def get_settings() -> Settings:
    return Settings()
