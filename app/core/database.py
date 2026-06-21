import psycopg

from app.core.config import Settings, get_settings


def init_database(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    dimension = settings.embedding_dimension

    schema_sql = f"""
    CREATE EXTENSION IF NOT EXISTS vector;

    CREATE TABLE IF NOT EXISTS conversation_sessions (
        id BIGSERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS conversation_turns (
        id BIGSERIAL PRIMARY KEY,
        session_id BIGINT,
        turn_index INTEGER,
        user_message TEXT NOT NULL,
        assistant_message TEXT NOT NULL,
        embedding vector({dimension}) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    INSERT INTO conversation_sessions (title)
    SELECT '默认会话'
    WHERE NOT EXISTS (SELECT 1 FROM conversation_sessions);

    ALTER TABLE conversation_turns
        ADD COLUMN IF NOT EXISTS session_id BIGINT;

    ALTER TABLE conversation_turns
        ADD COLUMN IF NOT EXISTS turn_index INTEGER;

    UPDATE conversation_turns
    SET session_id = (SELECT id FROM conversation_sessions ORDER BY id LIMIT 1)
    WHERE session_id IS NULL;

    WITH indexed_turns AS (
        SELECT
            id,
            row_number() OVER (PARTITION BY session_id ORDER BY id) AS index_in_session
        FROM conversation_turns
        WHERE turn_index IS NULL
    )
    UPDATE conversation_turns turns
    SET turn_index = indexed_turns.index_in_session
    FROM indexed_turns
    WHERE turns.id = indexed_turns.id;

    ALTER TABLE conversation_turns
        ALTER COLUMN session_id SET NOT NULL;

    ALTER TABLE conversation_turns
        ALTER COLUMN turn_index SET NOT NULL;

    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'conversation_turns_session_id_fkey'
        ) THEN
            ALTER TABLE conversation_turns
                ADD CONSTRAINT conversation_turns_session_id_fkey
                FOREIGN KEY (session_id)
                REFERENCES conversation_sessions(id)
                ON DELETE CASCADE;
        END IF;
    END $$;

    CREATE TABLE IF NOT EXISTS documents (
        id BIGSERIAL PRIMARY KEY,
        filename TEXT NOT NULL,
        content_type TEXT NOT NULL,
        file_path TEXT NOT NULL,
        chunk_count INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS document_chunks (
        id BIGSERIAL PRIMARY KEY,
        document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        filename TEXT NOT NULL,
        content TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        embedding vector({dimension}) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE INDEX IF NOT EXISTS conversation_turns_embedding_idx
        ON conversation_turns
        USING hnsw (embedding vector_cosine_ops);

    CREATE INDEX IF NOT EXISTS conversation_turns_session_id_idx
        ON conversation_turns (session_id, id DESC);

    CREATE UNIQUE INDEX IF NOT EXISTS conversation_turns_session_turn_index_idx
        ON conversation_turns (session_id, turn_index);

    CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops);
    """

    with psycopg.connect(settings.database_url, autocommit=True) as connection:
        connection.execute(schema_sql)


def to_pgvector(vector: list[float]) -> str:
    return "[" + ",".join(str(value) for value in vector) + "]"
