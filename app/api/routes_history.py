from fastapi import APIRouter, Query, Response, status

from app.schemas.history import Turn
from app.services import memory_manager


router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[Turn])
def list_history(
    session_id: int = Query(..., ge=1),
) -> list[Turn]:
    return memory_manager.list_history(session_id)


@router.get("/recent", response_model=list[Turn])
def list_recent_history(
    session_id: int = Query(..., ge=1),
    limit: int = Query(default=5, ge=1, le=100),
) -> list[Turn]:
    return memory_manager.list_recent_history(session_id, limit)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_history(
    session_id: int = Query(..., ge=1),
) -> Response:
    memory_manager.clear_history(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
