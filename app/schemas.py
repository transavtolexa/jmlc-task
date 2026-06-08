from pydantic import BaseModel, Field


class RestoreRequest(BaseModel):
    text: str = Field(..., min_length=1, examples=["куплюайфон14про"])


class RestoreResponse(BaseModel):
    text: str
    restored: str

