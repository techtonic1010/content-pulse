from fastapi import FastAPI, HTTPException

from app.config import ITEM_EMBEDDINGS_PATH, ITEM_IDS_PATH, USER_EMBEDDINGS_PATH, USER_IDS_PATH
from app.loader import Artifacts, load_artifacts
from app.schemas import HealthResponse, RankRequest, RankResponse, ScoreRequest, ScoreResponse
from app.scorer import ModelScorer

app = FastAPI(title="ML Recommendation Service", version="0.1.0")

artifacts: Artifacts | None = None
scorer: ModelScorer | None = None


@app.on_event("startup")
def on_startup() -> None:
    global artifacts
    global scorer
    try:
        artifacts = load_artifacts(
            USER_EMBEDDINGS_PATH,
            ITEM_EMBEDDINGS_PATH,
            USER_IDS_PATH,
            ITEM_IDS_PATH,
        )
        scorer = ModelScorer.from_artifacts(
            artifacts.user_embeddings,
            artifacts.item_embeddings,
            artifacts.user_ids,
            artifacts.item_ids,
        )
    except FileNotFoundError:
        artifacts = None
        scorer = None


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", artifacts_loaded=artifacts is not None)


@app.post("/rank", response_model=RankResponse)
def rank(payload: RankRequest) -> RankResponse:
    if artifacts is None:
        raise HTTPException(status_code=503, detail="Artifacts not loaded")

    _ = payload.user_id
    return RankResponse(message="ML ranking endpoint scaffold ready")


@app.post("/score", response_model=ScoreResponse)
def score(payload: ScoreRequest) -> ScoreResponse:
    if scorer is None:
        raise HTTPException(status_code=503, detail="Artifacts not loaded")

    value = scorer.get_score(payload.user_id, payload.item_id)
    if value is None:
        raise HTTPException(status_code=404, detail="User or item not found in embeddings")

    return ScoreResponse(user_id=payload.user_id, item_id=payload.item_id, score=value)
