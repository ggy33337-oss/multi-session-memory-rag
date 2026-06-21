from pathlib import Path

import psycopg

from app.core.database import to_pgvector
from app.schemas.document import Document, DocumentChunk, DocumentSearchResult


def list_documents(connection: psycopg.Connection) -> list[Document]:
    rows = connection.execute(
        """
        SELECT id, filename, content_type, file_path, chunk_count, created_at
        FROM documents
        ORDER BY id DESC
        """
    ).fetchall()
    return [to_document(row) for row in rows]


def append_document_with_chunks(
    connection: psycopg.Connection,
    filename: str,
    content_type: str,
    file_path: Path,
    contents: list[str],
    vectors: list[list[float]],
) -> tuple[Document, list[DocumentChunk]]:
    if len(contents) != len(vectors):
        raise ValueError("Chunk contents and vectors must have the same length.")

    document_row = connection.execute(
        """
        INSERT INTO documents (filename, content_type, file_path, chunk_count)
        VALUES (%s, %s, %s, %s)
        RETURNING id, filename, content_type, file_path, chunk_count, created_at
        """,
        (filename, content_type, str(file_path), len(contents)),
    ).fetchone()
    if document_row is None:
        raise RuntimeError("Failed to insert document.")

    document = to_document(document_row)
    chunks = []
    for chunk_index, (content, vector) in enumerate(zip(contents, vectors, strict=True)):
        chunk_row = connection.execute(
            """
            INSERT INTO document_chunks (
                document_id, filename, content, chunk_index, embedding
            )
            VALUES (%s, %s, %s, %s, %s::vector)
            RETURNING id, document_id, filename, content, chunk_index, created_at
            """,
            (
                document.document_id,
                filename,
                content,
                chunk_index,
                to_pgvector(vector),
            ),
        ).fetchone()
        if chunk_row is None:
            raise RuntimeError("Failed to insert document chunk.")
        chunks.append(to_chunk(chunk_row))

    return document, chunks


def search_chunks(
    connection: psycopg.Connection,
    query_vector: list[float],
    top_k: int,
    similarity_threshold: float,
) -> list[DocumentSearchResult]:
    if top_k <= 0:
        return []

    rows = connection.execute(
        """
        SELECT id, document_id, filename, chunk_index, content
        FROM (
            SELECT
                id,
                document_id,
                filename,
                chunk_index,
                content,
                1 - (embedding <=> %s::vector) AS similarity
            FROM document_chunks
        ) scored_chunks
        WHERE similarity >= %s
        ORDER BY similarity DESC
        LIMIT %s
        """,
        (to_pgvector(query_vector), similarity_threshold, top_k),
    ).fetchall()

    return [
        DocumentSearchResult(
            chunk_id=row[0],
            document_id=row[1],
            filename=row[2],
            chunk_index=row[3],
            content=row[4],
        )
        for row in rows
    ]


def delete_document(connection: psycopg.Connection, document_id: int) -> Document | None:
    row = connection.execute(
        """
        DELETE FROM documents
        WHERE id = %s
        RETURNING id, filename, content_type, file_path, chunk_count, created_at
        """,
        (document_id,),
    ).fetchone()
    return to_document(row) if row else None


def clear_documents(connection: psycopg.Connection) -> None:
    connection.execute("DELETE FROM documents")


def to_document(row) -> Document:
    return Document(
        document_id=row[0],
        filename=row[1],
        content_type=row[2],
        file_path=row[3],
        chunk_count=row[4],
        created_at=row[5].isoformat(timespec="seconds"),
    )


def to_chunk(row) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=row[0],
        document_id=row[1],
        filename=row[2],
        content=row[3],
        chunk_index=row[4],
        created_at=row[5].isoformat(timespec="seconds"),
    )
