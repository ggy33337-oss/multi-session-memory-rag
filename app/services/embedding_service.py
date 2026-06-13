from openai import OpenAI

from app.core.config import Settings


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.provider = settings.embedding_provider.lower()
        self.dimension = settings.embedding_dimension
        self.client = self._build_client()

    def embed(self, text: str) -> list[float]:
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Embedding text cannot be empty.")

        if self.provider == "openai":
            return self._openai_embed(cleaned_text)
        raise ValueError(f"Unsupported embedding provider: {self.settings.embedding_provider}")

    def _build_client(self) -> OpenAI | None:
        if self.provider != "openai":
            return None
        kwargs = {}
        if self.settings.openai_api_key:
            kwargs["api_key"] = self.settings.openai_api_key
        if self.settings.openai_base_url:
            kwargs["base_url"] = self.settings.openai_base_url
        return OpenAI(**kwargs)

    def _openai_embed(self, text: str) -> list[float]:
        if self.client is None:
            raise RuntimeError("OpenAI client is not initialized.")
        response = self.client.embeddings.create(
            model=self.settings.embedding_model,
            input=text,
            dimensions=self.settings.embedding_dimension,
            encoding_format="float",
        )
        vector = response.data[0].embedding
        self.dimension = len(vector)
        return vector
