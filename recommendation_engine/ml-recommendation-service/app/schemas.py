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


class UserEventPayload(BaseModel):
    userId: str
    contentId: str
    eventType: str
    completionRatio: float
    timestamp: int
    sessionId: str
    source: str
    contentType: str


class UserEventsResponse(BaseModel):
    user_id: str
    event_count: int
    events: list[UserEventPayload]


class EmbeddedEventPayload(BaseModel):
    contentId: str
    eventType: str
    completionRatio: float | None = None
    timestamp: int
    embedding: list[float]


class EmbeddedEventsMetadata(BaseModel):
    total_events_fetched: int
    total_valid_events: int
    total_skipped_events: int
    skipped_reasons_count: dict[str, int]


class EmbeddedEventsResponse(BaseModel):
    user_id: str
    valid_events: list[EmbeddedEventPayload]
    metadata: EmbeddedEventsMetadata


class WeightedEventPayload(BaseModel):
    contentId: str
    eventType: str
    timestamp: int
    embedding: list[float]
    event_type_weight: float
    completion_weight: float
    recency_weight: float
    final_weight: float


class WeightedEventsMetadata(BaseModel):
    total_events_received: int
    total_events_used: int
    total_events_skipped: int
    skipped_reasons_count: dict[str, int]


class WeightedEventsResponse(BaseModel):
    user_id: str
    weighted_events: list[WeightedEventPayload]
    metadata: WeightedEventsMetadata


class UserVectorMetadata(BaseModel):
    total_events_received: int
    total_events_used: int
    total_events_skipped: int
    raw_weight_sum: float
    l2_norm_before_normalization: float
    skipped_reasons_count: dict[str, int]
    vector_built: bool
    debug_trace: list[dict[str, object]]


class UserVectorResponse(BaseModel):
    user_id: str
    final_user_vector: list[float] | None
    metadata: UserVectorMetadata


class FaissEventCounts(BaseModel):
    received: int
    used: int
    skipped: int


class FaissVectorStats(BaseModel):
    norm_before_final: float
    norm_after_final: float
    has_nan: bool
    has_inf: bool


class FaissReadyResponse(BaseModel):
    user_id: str
    user_vector: list[float]
    is_faiss_ready: bool
    fallback_used: bool
    reason: str | None
    event_counts: FaissEventCounts
    vector_stats: FaissVectorStats
    debug: dict[str, object]


class CandidateRetrievalRequest(BaseModel):
    user_vector: list[float]
    k: int = 5
    candidate_pool_k: int = 50
    nprobe: int | None = None


class CandidateRetrievalResponse(BaseModel):
    indices: list[int]
    scores: list[float]
    k: int
    vector_norm: float
    is_normalized: bool
    reason: str | None
    debug: dict[str, float]


class GenreRecommendationRequest(BaseModel):
    top_indices: list[int]
    top_scores: list[float]
    is_normalized: bool
    vector_norm: float
    min_similarity_score: float | None = None
    top_candidates_for_genres: int | None = None
    top_genres_to_return: int | None = None
    movies_per_genre: int | None = None


class GenreCandidateMovie(BaseModel):
    movieId: str
    title: str
    genres: list[str]
    score: float
    faiss_index: int


class RankedGenreItem(BaseModel):
    genre: str
    raw_score: float
    normalized_score: float
    count: int


class GenreGroupedMovie(BaseModel):
    movieId: str
    title: str
    score: float


class GenreMovieGroup(BaseModel):
    genre: str
    movies: list[GenreGroupedMovie]


class GenreRecommendationsMetadata(BaseModel):
    validation_passed: bool
    validation_error: str | None
    total_input_candidates: int
    total_mapped_candidates: int
    total_with_metadata: int
    total_after_score_filter: int
    total_selected_for_genres: int
    skipped_reasons_count: dict[str, int]
    config_used: dict[str, float | int]
    todo: str


class GenreRecommendationResponse(BaseModel):
    candidates: list[GenreCandidateMovie]
    ranked_genres: list[RankedGenreItem]
    genre_groups: list[GenreMovieGroup]
    metadata: GenreRecommendationsMetadata


class FinalRecommendationRequest(BaseModel):
    userId: str = Field(..., min_length=1)


class FinalTopGenre(BaseModel):
    genre: str
    score: float
    reason: str


class FinalRecommendedMovie(BaseModel):
    movieId: str
    title: str
    score: float
    year: int | None = None


class FinalMoviesByGenre(BaseModel):
    genre: str
    movies: list[FinalRecommendedMovie]


class FinalRecommendationMeta(BaseModel):
    candidatesRetrieved: int
    candidatesUsed: int
    isFallback: bool


class FinalRecommendationResponse(BaseModel):
    userId: str
    topGenres: list[FinalTopGenre]
    moviesByGenre: list[FinalMoviesByGenre]
    meta: FinalRecommendationMeta
