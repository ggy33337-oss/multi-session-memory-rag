from pydantic import BaseModel


class Turn(BaseModel):
    turn_id: int
    turn_index: int
    user: str
    assistant: str
    created_at: str
