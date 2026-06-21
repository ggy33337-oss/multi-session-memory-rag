from pydantic import BaseModel


class Document(BaseModel):
    document_id: int
    filename: str
    content_type: str
    file_path: str
    chunk_count: int
    created_at: str


class DocumentChunk(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    content: str
    chunk_index: int
    created_at: str


class DocumentUploadResponse(BaseModel):
    document: Document
    chunk_count: int


class DocumentSearchResult(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    chunk_index: int
    content: str
