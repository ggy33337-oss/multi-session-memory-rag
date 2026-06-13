from fastapi import APIRouter, Depends, Query, Response, status

from app.schemas.history import Turn
from app.services.memory_manager import MemoryManager, get_memory_manager


router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=list[Turn])
def list_history(
    memory_manager: MemoryManager = Depends(get_memory_manager),
) -> list[Turn]:
    return memory_manager.list_history()


@router.get("/recent", response_model=list[Turn])
def list_recent_history(
    limit: int = Query(default=5, ge=1, le=100),
    memory_manager: MemoryManager = Depends(get_memory_manager),
) -> list[Turn]:
    return memory_manager.list_recent_history(limit)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_history(
    memory_manager: MemoryManager = Depends(get_memory_manager),
) -> Response:
    memory_manager.clear_history()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

