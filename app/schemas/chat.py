from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Current user message.")
    session_id: int = Field(..., ge=1, description="Current conversation session.")


class ChatResponse(BaseModel):
    answer: str
    session_id: int
    turn_id: int
    turn_index: int
    retrieved_turn_ids: list[int]
    retrieved_turn_indexes: list[int]
    retrieved_document_chunk_ids: list[int] = Field(default_factory=list)
