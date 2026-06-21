from app.core.config import get_settings
from app.services.embedding_service import build_openai_client


def generate_answer(system_prompt: str, user_prompt: str) -> str:
    settings = get_settings()
    if settings.llm_provider.lower() != "openai":
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")

    client = build_openai_client()
    response = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )
    content = response.choices[0].message.content
    return content.strip() if content else ""
