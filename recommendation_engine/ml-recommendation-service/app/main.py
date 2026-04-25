import json
import logging
import re

from fastapi import FastAPI, HTTPException
from redis import Redis

from app.config import (
    EPSILON,
    FAISS_INDEX_PATH,
    ITEM_EMBEDDINGS_PATH,
    ITEM_IDS_PATH,
    MIN_SIMILARITY_SCORE,
    MAPPER_ITEM_EMBEDDINGS_PATH,
    MAPPER_MOVIE2IDX_PATH,
    MOVIES_METADATA_CSV_PATH,
    REDIS_DB,
    REDIS_HOST,
    REDIS_MOVIE_GENRES_KEY_PREFIX,
    REDIS_MOVIE_META_KEY_PREFIX,
    REDIS_MOVIE_TITLE_KEY_PREFIX,
    REDIS_PORT,
    TOP_CANDIDATES_FOR_GENRES,
    TOP_GENRES_TO_RETURN,
    TOP_MOVIES_PER_GENRE,
    TOP_K_FAISS,
    USER_EMBEDDINGS_PATH,
    USER_IDS_PATH,
)
from app.loader import Artifacts, MapperArtifacts, load_artifacts, load_faiss_index, load_mapper_artifacts, load_movie_metadata_csv
from app.candidate_retrieval import retrieve_candidates
from app.genre_recommendation import build_genre_recommendations
from app.event_embedding_mapper import build_content_to_index_map, prepare_events_with_embeddings
from app.event_weight_computation import process_event_batch
from app.event_vector_aggregation import build_user_vector
from app.event_vector_readiness import build_faiss_ready_vector
from app.movie_metadata_store import CompositeMovieMetadataStore, InMemoryMovieMetadataStore, RedisMovieMetadataStore
from app.redis_store import RedisEventStore
from app.schemas import (
    EmbeddedEventsResponse,
    FaissReadyResponse,
    CandidateRetrievalRequest,
    CandidateRetrievalResponse,
    GenreRecommendationRequest,
    GenreRecommendationResponse,
    FinalRecommendationRequest,
    FinalRecommendationResponse,
    HealthResponse,
    RankRequest,
    RankResponse,
    ScoreRequest,
    ScoreResponse,
    UserEventPayload,
    UserEventsResponse,
    UserVectorResponse,
    WeightedEventsResponse,
)
from app.scorer import ModelScorer

app = FastAPI(title="ML Recommendation Service", version="0.1.0")
logger = logging.getLogger(__name__)

artifacts: Artifacts | None = None
scorer: ModelScorer | None = None
redis_store: RedisEventStore | None = None
content_to_index_map: dict[str, int] = {}
mapper_artifacts: MapperArtifacts | None = None
faiss_index = None
idx_to_movie_id_map: dict[int, str] = {}
movie_metadata_store: CompositeMovieMetadataStore | None = None


def _fallback_recommendations_response(user_id: str) -> FinalRecommendationResponse:
    return FinalRecommendationResponse(
        userId=user_id,
        topGenres=[],
        moviesByGenre=[],
        meta={
            "candidatesRetrieved": 0,
            "candidatesUsed": 0,
            "isFallback": True,
        },
    )


def _extract_year(title: str) -> int | None:
    match = re.search(r"\((\d{4})\)\s*$", title)
    if match is None:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


@app.on_event("startup")
def on_startup() -> None:
    global artifacts
    global scorer
    global redis_store
    global content_to_index_map
    global mapper_artifacts
    global faiss_index
    global idx_to_movie_id_map
    global movie_metadata_store

    redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    try:
        redis_store = RedisEventStore(redis_client)
        redis_store.ping()
    except Exception:
        redis_store = None
        logger.exception("Failed to connect to Redis backend")

    metadata_stores = []
    try:
        metadata_stores.append(
            RedisMovieMetadataStore(
                redis_client=redis_client,
                meta_key_prefix=REDIS_MOVIE_META_KEY_PREFIX,
                genres_key_prefix=REDIS_MOVIE_GENRES_KEY_PREFIX,
                title_key_prefix=REDIS_MOVIE_TITLE_KEY_PREFIX,
            )
        )
    except Exception:
        logger.exception("Failed to initialize Redis metadata store")

    try:
        csv_metadata = load_movie_metadata_csv(MOVIES_METADATA_CSV_PATH)
        metadata_stores.append(InMemoryMovieMetadataStore(csv_metadata))
    except FileNotFoundError:
        logger.warning("Movie metadata CSV not found: %s", MOVIES_METADATA_CSV_PATH)

    movie_metadata_store = CompositeMovieMetadataStore(metadata_stores) if metadata_stores else None

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
        content_to_index_map = build_content_to_index_map(artifacts.item_ids)
    except FileNotFoundError:
        artifacts = None
        scorer = None
        content_to_index_map = {}

    try:
        mapper_artifacts = load_mapper_artifacts(
            MAPPER_ITEM_EMBEDDINGS_PATH,
            MAPPER_MOVIE2IDX_PATH,
        )
        # movie2idx is the source of truth for Phase 3.1 mapping.
        content_to_index_map = dict(mapper_artifacts.movie2idx)
    except (FileNotFoundError, ValueError):
        mapper_artifacts = None
        logger.exception("Failed to load mapper artifacts for event->embedding mapping")

    idx_to_movie_id_map = {}
    if mapper_artifacts is not None:
        for movie_id, idx in mapper_artifacts.movie2idx.items():
            try:
                idx_to_movie_id_map[int(idx)] = str(movie_id)
            except Exception:
                continue

    try:
        faiss_index = load_faiss_index(FAISS_INDEX_PATH)
    except (FileNotFoundError, RuntimeError):
        faiss_index = None
        logger.warning("FAISS index not loaded. Candidate retrieval endpoint will return a clear error.")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", artifacts_loaded=artifacts is not None)


@app.get("/events/{user_id}", response_model=UserEventsResponse)
def get_user_events(user_id: str, limit: int = 50) -> UserEventsResponse:
    if redis_store is None:
        raise HTTPException(status_code=503, detail="Redis backend is not available")

    raw_events = redis_store.get_user_events(user_id, limit=limit)
    parsed_events: list[UserEventPayload] = []
    for raw_event in raw_events:
        try:
            parsed_events.append(UserEventPayload.model_validate(json.loads(raw_event)))
        except Exception:
            logger.warning("Skipping invalid event for user_id=%s payload=%s", user_id, raw_event)

    return UserEventsResponse(
        user_id=user_id,
        event_count=len(parsed_events),
        events=parsed_events,
    )


@app.get("/events/{user_id}/embedded", response_model=EmbeddedEventsResponse)
def get_user_events_with_embeddings(user_id: str, limit: int = 50) -> EmbeddedEventsResponse:
    if redis_store is None:
        raise HTTPException(status_code=503, detail="Redis backend is not available")
    if mapper_artifacts is None:
        raise HTTPException(status_code=503, detail="Mapper artifacts not loaded")

    result = prepare_events_with_embeddings(
        user_id=user_id,
        redis_store=redis_store,
        item_embeddings=mapper_artifacts.item_embeddings,
        content_to_index=content_to_index_map,
        limit=limit,
    )
    return EmbeddedEventsResponse(
        user_id=user_id,
        valid_events=result["valid_events"],
        metadata=result["metadata"],
    )


@app.get("/events/{user_id}/weighted", response_model=WeightedEventsResponse)
def get_user_events_with_weights(user_id: str, limit: int = 50) -> WeightedEventsResponse:
    if redis_store is None:
        raise HTTPException(status_code=503, detail="Redis backend is not available")
    if mapper_artifacts is None:
        raise HTTPException(status_code=503, detail="Mapper artifacts not loaded")

    phase31_result = prepare_events_with_embeddings(
        user_id=user_id,
        redis_store=redis_store,
        item_embeddings=mapper_artifacts.item_embeddings,
        content_to_index=content_to_index_map,
        limit=limit,
    )
    phase32_result = process_event_batch(phase31_result["valid_events"])

    weighted_events = []
    for event in phase32_result["weighted_events"]:
        weighted_events.append(
            {
                "contentId": event["contentId"],
                "eventType": event["eventType"],
                "timestamp": event["timestamp"],
                "embedding": event["embedding"].tolist(),
                "event_type_weight": event["event_type_weight"],
                "completion_weight": event["completion_weight"],
                "recency_weight": event["recency_weight"],
                "final_weight": event["final_weight"],
            }
        )

    return WeightedEventsResponse(
        user_id=user_id,
        weighted_events=weighted_events,
        metadata=phase32_result["metadata"],
    )


@app.get("/events/{user_id}/vector", response_model=UserVectorResponse)
def get_user_vector(user_id: str, limit: int = 50) -> UserVectorResponse:
    if redis_store is None:
        raise HTTPException(status_code=503, detail="Redis backend is not available")
    if mapper_artifacts is None:
        raise HTTPException(status_code=503, detail="Mapper artifacts not loaded")

    phase31_result = prepare_events_with_embeddings(
        user_id=user_id,
        redis_store=redis_store,
        item_embeddings=mapper_artifacts.item_embeddings,
        content_to_index=content_to_index_map,
        limit=limit,
    )
    phase32_result = process_event_batch(phase31_result["valid_events"])
    phase33_result = build_user_vector(phase32_result["weighted_events"])

    vector_payload = None
    if phase33_result["final_user_vector"] is not None:
        vector_payload = phase33_result["final_user_vector"].tolist()

    return UserVectorResponse(
        user_id=user_id,
        final_user_vector=vector_payload,
        metadata=phase33_result["metadata"],
    )


@app.get("/events/{user_id}/faiss-ready", response_model=FaissReadyResponse)
def get_faiss_ready_user_vector(user_id: str, limit: int = 50) -> FaissReadyResponse:
    if redis_store is None:
        raise HTTPException(status_code=503, detail="Redis backend is not available")
    if mapper_artifacts is None:
        raise HTTPException(status_code=503, detail="Mapper artifacts not loaded")

    phase31_result = prepare_events_with_embeddings(
        user_id=user_id,
        redis_store=redis_store,
        item_embeddings=mapper_artifacts.item_embeddings,
        content_to_index=content_to_index_map,
        limit=limit,
    )
    phase32_result = process_event_batch(phase31_result["valid_events"])
    phase33_result = build_user_vector(phase32_result["weighted_events"])
    phase34_result = build_faiss_ready_vector(
        raw_vector=phase33_result["final_user_vector"],
        metadata=phase33_result["metadata"],
        fallback_vector=None,
    )

    return FaissReadyResponse(
        user_id=user_id,
        user_vector=phase34_result["user_vector"].tolist(),
        is_faiss_ready=phase34_result["is_faiss_ready"],
        fallback_used=phase34_result["fallback_used"],
        reason=phase34_result["reason"],
        event_counts=phase34_result["event_counts"],
        vector_stats=phase34_result["vector_stats"],
        debug=phase34_result["debug"],
    )


@app.post("/faiss/candidates", response_model=CandidateRetrievalResponse)
def get_faiss_candidates(payload: CandidateRetrievalRequest) -> CandidateRetrievalResponse:
    if faiss_index is None:
        raise HTTPException(status_code=503, detail="FAISS index not loaded")

    result = retrieve_candidates(
        index=faiss_index,
        user_vector=payload.user_vector,
        k=payload.k,
        candidate_pool_k=payload.candidate_pool_k,
        nprobe=payload.nprobe,
    )

    return CandidateRetrievalResponse(
        indices=result["indices"],
        scores=result["scores"],
        k=result["k"],
        vector_norm=result["vector_norm"],
        is_normalized=result["is_normalized"],
        reason=result["reason"],
        debug=result["debug"],
    )


@app.post("/faiss/genre-recommendations", response_model=GenreRecommendationResponse)
def get_genre_recommendations(payload: GenreRecommendationRequest) -> GenreRecommendationResponse:
    if movie_metadata_store is None:
        raise HTTPException(status_code=503, detail="Movie metadata store is not initialized")

    if not idx_to_movie_id_map:
        raise HTTPException(status_code=503, detail="idx2movie mapping not loaded")

    result = build_genre_recommendations(
        top_indices=payload.top_indices,
        top_scores=payload.top_scores,
        is_normalized=payload.is_normalized,
        vector_norm=payload.vector_norm,
        idx2movie=idx_to_movie_id_map,
        metadata_store=movie_metadata_store,
        min_similarity_score=payload.min_similarity_score if payload.min_similarity_score is not None else MIN_SIMILARITY_SCORE,
        top_candidates_for_genres=payload.top_candidates_for_genres if payload.top_candidates_for_genres is not None else TOP_CANDIDATES_FOR_GENRES,
        top_genres_to_return=payload.top_genres_to_return if payload.top_genres_to_return is not None else TOP_GENRES_TO_RETURN,
        movies_per_genre=payload.movies_per_genre if payload.movies_per_genre is not None else TOP_MOVIES_PER_GENRE,
    )

    return GenreRecommendationResponse(
        candidates=result["candidates"],
        ranked_genres=result["ranked_genres"],
        genre_groups=result["genre_groups"],
        metadata=result["metadata"],
    )


@app.post("/recommendations", response_model=FinalRecommendationResponse)
def get_recommendations(payload: FinalRecommendationRequest) -> FinalRecommendationResponse:
    user_id = payload.userId.strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="userId must not be empty")

    if redis_store is None or mapper_artifacts is None or faiss_index is None or movie_metadata_store is None or not idx_to_movie_id_map:
        return _fallback_recommendations_response(user_id)

    try:
        phase31_result = prepare_events_with_embeddings(
            user_id=user_id,
            redis_store=redis_store,
            item_embeddings=mapper_artifacts.item_embeddings,
            content_to_index=content_to_index_map,
            limit=50,
        )
        phase32_result = process_event_batch(phase31_result["valid_events"])
        phase33_result = build_user_vector(phase32_result["weighted_events"])
        phase34_result = build_faiss_ready_vector(
            raw_vector=phase33_result["final_user_vector"],
            metadata=phase33_result["metadata"],
            fallback_vector=None,
        )

        if not phase34_result["is_faiss_ready"]:
            return _fallback_recommendations_response(user_id)

        retrieval_result = retrieve_candidates(
            index=faiss_index,
            user_vector=phase34_result["user_vector"],
            k=TOP_CANDIDATES_FOR_GENRES,
            candidate_pool_k=TOP_K_FAISS,
            nprobe=None,
        )

        if retrieval_result.get("reason") is not None:
            return _fallback_recommendations_response(user_id)

        genre_result = build_genre_recommendations(
            top_indices=retrieval_result["indices"],
            top_scores=retrieval_result["scores"],
            is_normalized=bool(retrieval_result["is_normalized"]),
            vector_norm=float(retrieval_result["vector_norm"]),
            idx2movie=idx_to_movie_id_map,
            metadata_store=movie_metadata_store,
            min_similarity_score=MIN_SIMILARITY_SCORE,
            top_candidates_for_genres=TOP_CANDIDATES_FOR_GENRES,
            top_genres_to_return=TOP_GENRES_TO_RETURN,
            movies_per_genre=TOP_MOVIES_PER_GENRE,
        )

        top_genres = []
        for item in genre_result["ranked_genres"]:
            top_genres.append(
                {
                    "genre": item["genre"],
                    "score": float(item["normalized_score"]),
                    "reason": "Based on recent viewing patterns",
                }
            )

        movies_by_genre = []
        for group in genre_result["genre_groups"]:
            movies = []
            for movie in group["movies"]:
                title = str(movie["title"])
                movies.append(
                    {
                        "movieId": str(movie["movieId"]),
                        "title": title,
                        "score": float(movie["score"]),
                        "year": _extract_year(title),
                    }
                )
            movies_by_genre.append(
                {
                    "genre": group["genre"],
                    "movies": movies,
                }
            )

        return FinalRecommendationResponse(
            userId=user_id,
            topGenres=top_genres,
            moviesByGenre=movies_by_genre,
            meta={
                "candidatesRetrieved": int(retrieval_result.get("debug", {}).get("candidate_pool_k", 0)),
                "candidatesUsed": int(genre_result["metadata"].get("total_selected_for_genres", 0)),
                "isFallback": False,
            },
        )
    except Exception:
        logger.exception("Failed to build recommendations for user_id=%s", user_id)
        return _fallback_recommendations_response(user_id)


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
