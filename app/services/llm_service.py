from openai import OpenAI

from app.core.config import Settings


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.provider = settings.llm_provider.lower()
        self.client = self._build_client()

    def _build_client(self) -> OpenAI | None:
        if self.provider != "openai":
            return None
        kwargs = {}
        if self.settings.openai_api_key:
            kwargs["api_key"] = self.settings.openai_api_key
        if self.settings.openai_base_url:
            kwargs["base_url"] = self.settings.openai_base_url
        return OpenAI(**kwargs)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider == "openai":
            return self._openai_generate(system_prompt, user_prompt)
        raise ValueError(f"Unsupported LLM provider: {self.settings.llm_provider}")

    def _openai_generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.client is None:
            raise RuntimeError("OpenAI client is not initialized.")
        response = self.client.chat.completions.create(
            model=self.settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""
