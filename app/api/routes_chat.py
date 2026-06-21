from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services import memory_manager


router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return memory_manager.chat(request.session_id, request.message)
