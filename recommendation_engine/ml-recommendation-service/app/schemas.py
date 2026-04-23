from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    artifacts_loaded: bool


class RankRequest(BaseModel):
    user_id: str = Field(..., min_length=1)


class RankResponse(BaseModel):
    message: str


class ScoreRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    item_id: str = Field(..., min_length=1)


class ScoreResponse(BaseModel):
    user_id: str
    item_id: str
    score: float
