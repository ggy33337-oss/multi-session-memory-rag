from openai import OpenAI

from app.core.config import get_settings


def embed_text(text: str) -> list[float]:
    settings = get_settings()
    cleaned_text = text.strip()
    if not cleaned_text:
        raise ValueError("Embedding text cannot be empty.")

    if settings.embedding_provider.lower() != "openai":
        raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")

    client = build_openai_client()
    response = client.embeddings.create(
        model=settings.embedding_model,
        input=cleaned_text,
        dimensions=settings.embedding_dimension,
        encoding_format="float",
    )
    return response.data[0].embedding


def build_openai_client() -> OpenAI:
    settings = get_settings()
    kwargs = {}
    if settings.openai_api_key:
        kwargs["api_key"] = settings.openai_api_key
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return OpenAI(**kwargs)
