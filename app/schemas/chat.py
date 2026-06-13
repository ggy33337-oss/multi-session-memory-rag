from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Current user message.")


class ChatResponse(BaseModel):
    answer: str
    turn_id: int
    retrieved_turn_ids: list[int]

