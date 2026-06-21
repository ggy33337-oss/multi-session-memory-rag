from fastapi import APIRouter, File, Query, Response, UploadFile, status

from app.schemas.document import Document, DocumentSearchResult, DocumentUploadResponse
from app.services import document_service


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentUploadResponse)
def upload_document(
    file: UploadFile = File(...),
) -> DocumentUploadResponse:
    return document_service.upload_document(file)


@router.get("", response_model=list[Document])
def list_documents() -> list[Document]:
    return document_service.list_documents()


@router.get("/search", response_model=list[DocumentSearchResult])
def search_documents(
    query: str = Query(..., min_length=1),
) -> list[DocumentSearchResult]:
    return document_service.search(query)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
) -> Response:
    document_service.delete_document(document_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_documents() -> Response:
    document_service.clear_documents()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
