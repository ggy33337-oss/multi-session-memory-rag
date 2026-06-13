from fastapi import APIRouter, Depends

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.memory_manager import MemoryManager, get_memory_manager


router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    memory_manager: MemoryManager = Depends(get_memory_manager),
) -> ChatResponse:
    return memory_manager.chat(request.message)

