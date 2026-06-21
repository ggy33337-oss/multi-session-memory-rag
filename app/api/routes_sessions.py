from fastapi import APIRouter, Response, status

from app.schemas.session import Session, SessionCreateRequest
from app.services import memory_manager


router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[Session])
def list_sessions() -> list[Session]:
    return memory_manager.list_sessions()


@router.post("", response_model=Session, status_code=status.HTTP_201_CREATED)
def create_session(request: SessionCreateRequest) -> Session:
    return memory_manager.create_session(request.title)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int) -> Response:
    memory_manager.delete_session(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
