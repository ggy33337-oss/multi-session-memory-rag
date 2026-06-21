import psycopg

from app.core.config import get_settings
from app.core.errors import bad_request, service_unavailable
from app.repositories import conversation_repository
from app.schemas.chat import ChatResponse
from app.schemas.history import Turn
from app.schemas.session import Session
from app.services import document_service, prompt_builder
from app.services.embedding_service import embed_text
from app.services.llm_service import generate_answer


def list_sessions() -> list[Session]:
    settings = get_settings()
    with psycopg.connect(settings.database_url) as connection:
        return conversation_repository.list_sessions(connection)


def create_session(title: str | None = None) -> Session:
    settings = get_settings()
    clean_title = normalize_session_title(title)
    with psycopg.connect(settings.database_url) as connection:
        return conversation_repository.create_session(connection, clean_title)


def delete_session(session_id: int) -> None:
    settings = get_settings()
    with psycopg.connect(settings.database_url) as connection:
        session = conversation_repository.delete_session(connection, session_id)

    if session is None:
        raise bad_request(f"Session {session_id} does not exist.")


def chat(session_id: int, user_query: str) -> ChatResponse:
    settings = get_settings()
    user_query = user_query.strip()
    if not user_query:
        raise bad_request("message cannot be empty.")

    query_vector = embed_query(user_query)

    with psycopg.connect(settings.database_url) as connection:
        ensure_session_exists(connection, session_id)
        recent_turns = conversation_repository.get_recent_turns(
            connection,
            session_id,
            settings.recent_turns,
        )
        retrieved_turns = conversation_repository.search_similar_turns(
            connection,
            session_id,
            query_vector,
            settings.retrieve_top_k,
        )

    retrieved_turns = remove_recent_duplicates(recent_turns, retrieved_turns)
    retrieved_chunks = document_service.search_by_vector(query_vector)

    system_prompt = prompt_builder.build_system_prompt()
    user_prompt = prompt_builder.build_user_prompt(
        recent_turns=recent_turns,
        retrieved_turns=retrieved_turns,
        retrieved_document_chunks=retrieved_chunks,
        user_query=user_query,
    )
    answer = call_llm(system_prompt, user_prompt)
    turn_vector = embed_turn(user_query, answer)

    with psycopg.connect(settings.database_url) as connection:
        turn = conversation_repository.append_turn(
            connection,
            session_id=session_id,
            user=user_query,
            assistant=answer,
            embedding=turn_vector,
        )
        conversation_repository.update_session_after_turn(
            connection,
            session_id=session_id,
            title=build_session_title(user_query),
        )

    return ChatResponse(
        answer=answer,
        session_id=session_id,
        turn_id=turn.turn_id,
        turn_index=turn.turn_index,
        retrieved_turn_ids=[turn.turn_id for turn in retrieved_turns],
        retrieved_turn_indexes=[turn.turn_index for turn in retrieved_turns],
        retrieved_document_chunk_ids=[chunk.chunk_id for chunk in retrieved_chunks],
    )


def list_history(session_id: int) -> list[Turn]:
    settings = get_settings()
    with psycopg.connect(settings.database_url) as connection:
        ensure_session_exists(connection, session_id)
        return conversation_repository.list_turns(connection, session_id)


def list_recent_history(session_id: int, limit: int) -> list[Turn]:
    settings = get_settings()
    with psycopg.connect(settings.database_url) as connection:
        ensure_session_exists(connection, session_id)
        return conversation_repository.get_recent_turns(connection, session_id, limit)


def clear_history(session_id: int) -> None:
    settings = get_settings()
    with psycopg.connect(settings.database_url) as connection:
        ensure_session_exists(connection, session_id)
        conversation_repository.clear_turns(connection, session_id)


def embed_query(user_query: str) -> list[float]:
    try:
        return embed_text(user_query)
    except Exception as exc:
        raise service_unavailable(f"Failed to embed query: {exc}") from exc


def call_llm(system_prompt: str, user_prompt: str) -> str:
    try:
        answer = generate_answer(system_prompt, user_prompt)
    except Exception as exc:
        raise service_unavailable(f"Failed to generate answer: {exc}") from exc

    if not answer:
        raise service_unavailable("LLM returned an empty answer.")
    return answer


def embed_turn(user: str, assistant: str) -> list[float]:
    try:
        text = prompt_builder.build_turn_embedding_text(user=user, assistant=assistant)
        return embed_text(text)
    except Exception as exc:
        raise service_unavailable(f"Failed to embed turn: {exc}") from exc


def remove_recent_duplicates(recent_turns: list[Turn], retrieved_turns: list[Turn]) -> list[Turn]:
    recent_turn_ids = {turn.turn_id for turn in recent_turns}
    return [turn for turn in retrieved_turns if turn.turn_id not in recent_turn_ids]


def ensure_session_exists(connection: psycopg.Connection, session_id: int) -> Session:
    session = conversation_repository.get_session(connection, session_id)
    if session is None:
        raise bad_request(f"Session {session_id} does not exist.")
    return session


def normalize_session_title(title: str | None) -> str:
    clean_title = (title or "").strip()
    return clean_title[:80] if clean_title else "新会话"


def build_session_title(user_query: str) -> str:
    compact_query = " ".join(user_query.split())
    return compact_query[:30] or "新会话"
