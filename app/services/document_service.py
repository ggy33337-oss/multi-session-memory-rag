from pathlib import Path
from shutil import copyfileobj
from uuid import uuid4

import psycopg
from fastapi import HTTPException, UploadFile
from pypdf import PdfReader

from app.core.config import get_settings
from app.core.errors import bad_request, service_unavailable
from app.repositories import document_repository
from app.schemas.document import Document, DocumentSearchResult, DocumentUploadResponse
from app.services.embedding_service import embed_text


ALLOWED_SUFFIXES = {".txt", ".md", ".pdf"}


def upload_document(file: UploadFile) -> DocumentUploadResponse:
    settings = get_settings()
    settings.document_dir.mkdir(parents=True, exist_ok=True)

    filename = Path(file.filename or "").name
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise bad_request("Only .txt, .md, and .pdf files are supported.")

    saved_path = save_upload_file(file, suffix)
    document: Document | None = None

    try:
        text = extract_text(saved_path, suffix)
        chunks = split_text(
            text,
            chunk_size=settings.document_chunk_size,
            chunk_overlap=settings.document_chunk_overlap,
        )
    #如果上传的文档没有提取到任何有效文本，就删除本地保存的文件，并返回“文档文本不能为空”的错误，避免空文件继续入库。
        if not chunks:
            saved_path.unlink(missing_ok=True)
            raise bad_request("Document text cannot be empty.")

        vectors = embed_chunks(filename, chunks)
        with psycopg.connect(settings.database_url) as connection:
            document, saved_chunks = document_repository.append_document_with_chunks(
                connection,
                filename=filename,
                content_type=file.content_type or "application/octet-stream",
                file_path=saved_path,
                contents=chunks,
                vectors=vectors,
            )

        return DocumentUploadResponse(document=document, chunk_count=len(saved_chunks))
    except HTTPException:
        rollback_upload(saved_path, document)
        raise
    except Exception:
        rollback_upload(saved_path, document)
        raise service_unavailable("Failed to process document upload.") from None


def list_documents() -> list[Document]:
    settings = get_settings()
    with psycopg.connect(settings.database_url) as connection:
        return document_repository.list_documents(connection)


def search(user_query: str) -> list[DocumentSearchResult]:
    if not user_query.strip():
        return []

    try:
        query_vector = embed_text(user_query)
    except Exception as exc:
        raise service_unavailable(f"Failed to embed document query: {exc}") from exc

    return search_by_vector(query_vector)


def search_by_vector(query_vector: list[float]) -> list[DocumentSearchResult]:
    settings = get_settings()
    try:
        with psycopg.connect(settings.database_url) as connection:
            return document_repository.search_chunks(
                connection,
                query_vector=query_vector,
                top_k=settings.document_retrieve_top_k,
                similarity_threshold=settings.document_similarity_threshold,
            )
    except Exception as exc:
        raise service_unavailable(f"Failed to retrieve document chunks: {exc}") from exc


def delete_document(document_id: int) -> None:
    settings = get_settings()
    with psycopg.connect(settings.database_url) as connection:
        document = document_repository.delete_document(connection, document_id)

    if document is None:
        raise bad_request(f"Document {document_id} does not exist.")

    Path(document.file_path).unlink(missing_ok=True)




def save_upload_file(file: UploadFile, suffix: str) -> Path:
    settings = get_settings()
    saved_path = settings.document_dir / f"{uuid4().hex}{suffix}"
    with saved_path.open("wb") as target:
        copyfileobj(file.file, target)
    return saved_path


def extract_text(path: Path, suffix: str) -> str:
    if suffix in {".txt", ".md"}:
        return read_text_file(path)
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)
    raise ValueError(f"Unsupported document type: {suffix}")


def read_text_file(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    cleaned_text = "\n".join(line.strip() for line in text.splitlines())
    cleaned_text = "\n".join(line for line in cleaned_text.splitlines() if line)
    if not cleaned_text:
        return []

    chunk_size = max(chunk_size, 1)
    overlap = min(max(chunk_overlap, 0), chunk_size - 1)
    chunks = []
    start = 0

    while start < len(cleaned_text):
        end = min(start + chunk_size, len(cleaned_text))
        chunk = cleaned_text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(cleaned_text):
            break
        start = end - overlap

    return chunks


def embed_chunks(filename: str, chunks: list[str]) -> list[list[float]]:
    return [
        embed_text(build_chunk_embedding_text(filename, index, chunk))
        for index, chunk in enumerate(chunks)
    ]


def build_chunk_embedding_text(filename: str, chunk_index: int, content: str) -> str:
    return f"Document: {filename}\nChunk: {chunk_index}\n{content}"


def rollback_upload(saved_path: Path, document: Document | None) -> None:
    saved_path.unlink(missing_ok=True)
    if document is None:
        return

    try:
        settings = get_settings()
        with psycopg.connect(settings.database_url) as connection:
            document_repository.delete_document(connection, document.document_id)
    except Exception:
        pass
