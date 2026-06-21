import psycopg

from app.core.database import to_pgvector
from app.schemas.history import Turn
from app.schemas.session import Session


def list_sessions(connection: psycopg.Connection) -> list[Session]:
    rows = connection.execute(
        """
        SELECT
            sessions.id,
            sessions.title,
            sessions.created_at,
            sessions.updated_at,
            COUNT(turns.id) AS turn_count,
            latest.user_message AS last_message
        FROM conversation_sessions sessions
        LEFT JOIN conversation_turns turns ON turns.session_id = sessions.id
        LEFT JOIN LATERAL (
            SELECT user_message
            FROM conversation_turns
            WHERE session_id = sessions.id
            ORDER BY turn_index DESC
            LIMIT 1
        ) latest ON true
        GROUP BY sessions.id, sessions.title, sessions.created_at, sessions.updated_at, latest.user_message
        ORDER BY sessions.updated_at DESC, sessions.id DESC
        """
    ).fetchall()
    return [to_session(row) for row in rows]


def create_session(connection: psycopg.Connection, title: str) -> Session:
    row = connection.execute(
        """
        INSERT INTO conversation_sessions (title)
        VALUES (%s)
        RETURNING id, title, created_at, updated_at, 0 AS turn_count, NULL AS last_message
        """,
        (title,),
    ).fetchone()
    if row is None:
        raise RuntimeError("Failed to create conversation session.")
    return to_session(row)


def get_session(connection: psycopg.Connection, session_id: int) -> Session | None:
    row = connection.execute(
        """
        SELECT
            sessions.id,
            sessions.title,
            sessions.created_at,
            sessions.updated_at,
            COUNT(turns.id) AS turn_count,
            latest.user_message AS last_message
        FROM conversation_sessions sessions
        LEFT JOIN conversation_turns turns ON turns.session_id = sessions.id
        LEFT JOIN LATERAL (
            SELECT user_message
            FROM conversation_turns
            WHERE session_id = sessions.id
            ORDER BY turn_index DESC
            LIMIT 1
        ) latest ON true
        WHERE sessions.id = %s
        GROUP BY sessions.id, sessions.title, sessions.created_at, sessions.updated_at, latest.user_message
        """,
        (session_id,),
    ).fetchone()
    return to_session(row) if row else None


def update_session_after_turn(connection: psycopg.Connection, session_id: int, title: str | None) -> None:
    if title:
        connection.execute(
            """
            UPDATE conversation_sessions
            SET title = CASE WHEN title = '新会话' THEN %s ELSE title END,
                updated_at = now()
            WHERE id = %s
            """,
            (title, session_id),
        )
        return

    connection.execute(
        """
        UPDATE conversation_sessions
        SET updated_at = now()
        WHERE id = %s
        """,
        (session_id,),
    )


def delete_session(connection: psycopg.Connection, session_id: int) -> Session | None:
    row = connection.execute(
        """
        DELETE FROM conversation_sessions
        WHERE id = %s
        RETURNING id, title, created_at, updated_at, 0 AS turn_count, NULL AS last_message
        """,
        (session_id,),
    ).fetchone()
    return to_session(row) if row else None


def list_turns(connection: psycopg.Connection, session_id: int) -> list[Turn]:
    rows = connection.execute(
        """
        SELECT id, turn_index, user_message, assistant_message, created_at
        FROM conversation_turns
        WHERE session_id = %s
        ORDER BY turn_index
        """,
        (session_id,),
    ).fetchall()
    return [to_turn(row) for row in rows]


def get_recent_turns(connection: psycopg.Connection, session_id: int, limit: int) -> list[Turn]:
    if limit <= 0:
        return []

    rows = connection.execute(
        """
        SELECT id, turn_index, user_message, assistant_message, created_at
        FROM conversation_turns
        WHERE session_id = %s
        ORDER BY turn_index DESC
        LIMIT %s
        """,
        (session_id, limit),
    ).fetchall()
    return [to_turn(row) for row in reversed(rows)]


def search_similar_turns(
    connection: psycopg.Connection,
    session_id: int,
    query_vector: list[float],
    top_k: int,
) -> list[Turn]:
    if top_k <= 0:
        return []

    rows = connection.execute(
        """
        SELECT id, turn_index, user_message, assistant_message, created_at
        FROM conversation_turns
        WHERE session_id = %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (session_id, to_pgvector(query_vector), top_k),
    ).fetchall()
    return [to_turn(row) for row in rows]


def append_turn(
    connection: psycopg.Connection,
    session_id: int,
    user: str,
    assistant: str,
    embedding: list[float],
) -> Turn:
    row = connection.execute(
        """
        INSERT INTO conversation_turns (
            session_id, turn_index, user_message, assistant_message, embedding
        )
        VALUES (
            %s,
            COALESCE(
                (
                    SELECT max(turn_index) + 1
                    FROM conversation_turns
                    WHERE session_id = %s
                ),
                1
            ),
            %s,
            %s,
            %s::vector
        )
        RETURNING id, turn_index, user_message, assistant_message, created_at
        """,
        (session_id, session_id, user, assistant, to_pgvector(embedding)),
    ).fetchone()
    if row is None:
        raise RuntimeError("Failed to insert conversation turn.")
    return to_turn(row)


def clear_turns(connection: psycopg.Connection, session_id: int) -> None:
    connection.execute(
        "DELETE FROM conversation_turns WHERE session_id = %s",
        (session_id,),
    )
    connection.execute(
        """
        UPDATE conversation_sessions
        SET updated_at = now()
        WHERE id = %s
        """,
        (session_id,),
    )


def to_turn(row) -> Turn:
    return Turn(
        turn_id=row[0],
        turn_index=row[1],
        user=row[2],
        assistant=row[3],
        created_at=row[4].isoformat(timespec="seconds"),
    )


def to_session(row) -> Session:
    return Session(
        session_id=row[0],
        title=row[1],
        created_at=row[2].isoformat(timespec="seconds"),
        updated_at=row[3].isoformat(timespec="seconds"),
        turn_count=row[4],
        last_message=row[5],
    )
