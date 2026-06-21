from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=80)


class Session(BaseModel):
    session_id: int
    title: str
    created_at: str
    updated_at: str
    turn_count: int = 0
    last_message: str | None = None
