from __future__ import annotations

from collections import defaultdict
from math import isfinite
from typing import Any

from app.config import EPSILON
from app.movie_metadata_store import MovieMetadataStore


def validate_faiss_output(
    top_indices: list[Any],
    top_scores: list[Any],
    is_normalized: bool,
    vector_norm: float,
    norm_tolerance: float = 1e-3,
) -> tuple[bool, str | None]:
    if len(top_indices) != len(top_scores):
        return False, "indices_scores_length_mismatch"

    if not is_normalized:
        return False, "user_vector_not_normalized"

    if not isfinite(vector_norm) or abs(vector_norm - 1.0) > norm_tolerance:
        return False, "invalid_vector_norm"

    for idx in top_indices:
        if not isinstance(idx, int):
            return False, "invalid_index_type"

    for score in top_scores:
        if not isinstance(score, (int, float)):
            return False, "invalid_score_type"
        if not isfinite(float(score)):
            return False, "invalid_score_value"

    return True, None


def map_indices_to_movie_ids(
    top_indices: list[int],
    top_scores: list[float],
    idx2movie: dict[int, str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    mapped: list[dict[str, Any]] = []
    skipped_reasons_count: dict[str, int] = defaultdict(int)

    for idx, score in zip(top_indices, top_scores):
        movie_id = idx2movie.get(int(idx))
        if movie_id is None:
            skipped_reasons_count["missing_idx2movie_mapping"] += 1
            continue

        mapped.append(
            {
                "faiss_index": int(idx),
                "movieId": str(movie_id),
                "score": float(score),
            }
        )

    return mapped, dict(skipped_reasons_count)


def fetch_movie_metadata(
    mapped_candidates: list[dict[str, Any]],
    metadata_store: MovieMetadataStore,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    enriched: list[dict[str, Any]] = []
    skipped_reasons_count: dict[str, int] = defaultdict(int)

    for candidate in mapped_candidates:
        movie_id = str(candidate["movieId"])
        metadata = metadata_store.get_movie_metadata(movie_id)
        if metadata is None:
            skipped_reasons_count["missing_movie_metadata"] += 1
            continue

        genres = metadata.get("genres")
        if not isinstance(genres, list) or not genres:
            genres = ["Unknown"]

        enriched.append(
            {
                "movieId": movie_id,
                "title": str(metadata.get("title") or f"movie_{movie_id}"),
                "genres": [str(genre) for genre in genres] or ["Unknown"],
                "score": float(candidate["score"]),
                "faiss_index": int(candidate["faiss_index"]),
            }
        )

    return enriched, dict(skipped_reasons_count)


def filter_candidates_by_score(candidates: list[dict[str, Any]], min_similarity_score: float) -> list[dict[str, Any]]:
    filtered = [candidate for candidate in candidates if float(candidate["score"]) >= float(min_similarity_score)]
    filtered.sort(key=lambda item: float(item["score"]), reverse=True)
    return filtered


def select_top_candidates(candidates: list[dict[str, Any]], limit: int = 50) -> list[dict[str, Any]]:
    safe_limit = max(0, int(limit))
    return candidates[:safe_limit]


def aggregate_genre_scores(candidates: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, int]]:
    raw_genre_scores: dict[str, float] = defaultdict(float)
    genre_counts: dict[str, int] = defaultdict(int)

    for candidate in candidates:
        score = float(candidate["score"])
        genres = candidate.get("genres") or ["Unknown"]
        for genre in genres:
            genre_key = str(genre)
            raw_genre_scores[genre_key] += score
            genre_counts[genre_key] += 1

    return dict(raw_genre_scores), dict(genre_counts)


def normalize_genre_scores(
    raw_genre_scores: dict[str, float],
    genre_counts: dict[str, int],
    epsilon: float = EPSILON,
) -> dict[str, float]:
    normalized_scores: dict[str, float] = {}
    for genre, raw_score in raw_genre_scores.items():
        count = int(genre_counts.get(genre, 0))
        normalized_scores[genre] = float(raw_score) / (count + float(epsilon))
    return normalized_scores


def rank_genres(
    normalized_genre_scores: dict[str, float],
    raw_genre_scores: dict[str, float],
    genre_counts: dict[str, int],
    limit: int,
) -> list[dict[str, Any]]:
    ranked = sorted(
        normalized_genre_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    safe_limit = max(0, int(limit))
    output: list[dict[str, Any]] = []
    for genre, normalized_score in ranked[:safe_limit]:
        output.append(
            {
                "genre": genre,
                "raw_score": float(raw_genre_scores.get(genre, 0.0)),
                "normalized_score": float(normalized_score),
                "count": int(genre_counts.get(genre, 0)),
            }
        )

    return output


def group_movies_by_genre(
    candidates: list[dict[str, Any]],
    top_genres: list[str],
    movies_per_genre: int,
) -> list[dict[str, Any]]:
    grouped: list[dict[str, Any]] = []
    per_genre_limit = max(0, int(movies_per_genre))

    for genre in top_genres:
        seen_movie_ids: set[str] = set()
        movies: list[dict[str, Any]] = []

        for candidate in candidates:
            genres = candidate.get("genres") or []
            if genre not in genres:
                continue

            movie_id = str(candidate["movieId"])
            if movie_id in seen_movie_ids:
                continue

            seen_movie_ids.add(movie_id)
            movies.append(
                {
                    "movieId": movie_id,
                    "title": str(candidate["title"]),
                    "score": float(candidate["score"]),
                }
            )

        movies.sort(key=lambda item: float(item["score"]), reverse=True)
        grouped.append(
            {
                "genre": genre,
                "movies": movies[:per_genre_limit],
            }
        )

    return grouped


def build_genre_recommendations(
    *,
    top_indices: list[int],
    top_scores: list[float],
    is_normalized: bool,
    vector_norm: float,
    idx2movie: dict[int, str],
    metadata_store: MovieMetadataStore,
    min_similarity_score: float,
    top_candidates_for_genres: int,
    top_genres_to_return: int,
    movies_per_genre: int,
) -> dict[str, Any]:
    is_valid, validation_error = validate_faiss_output(
        top_indices=top_indices,
        top_scores=top_scores,
        is_normalized=is_normalized,
        vector_norm=vector_norm,
    )

    metadata: dict[str, Any] = {
        "validation_passed": is_valid,
        "validation_error": validation_error,
        "total_input_candidates": len(top_indices),
        "total_mapped_candidates": 0,
        "total_with_metadata": 0,
        "total_after_score_filter": 0,
        "total_selected_for_genres": 0,
        "skipped_reasons_count": {},
        "config_used": {
            "min_similarity_score": float(min_similarity_score),
            "top_candidates_for_genres": int(top_candidates_for_genres),
            "top_genres_to_return": int(top_genres_to_return),
            "movies_per_genre": int(movies_per_genre),
            "epsilon": float(EPSILON),
        },
        "todo": "watched-item filtering hook is intentionally not applied in Phase 4B",
    }

    if not is_valid:
        return {
            "candidates": [],
            "ranked_genres": [],
            "genre_groups": [],
            "metadata": metadata,
        }

    mapped_candidates, mapping_skips = map_indices_to_movie_ids(top_indices, top_scores, idx2movie)
    metadata["total_mapped_candidates"] = len(mapped_candidates)

    enriched_candidates, metadata_skips = fetch_movie_metadata(mapped_candidates, metadata_store)
    metadata["total_with_metadata"] = len(enriched_candidates)

    filtered_candidates = filter_candidates_by_score(enriched_candidates, min_similarity_score)
    metadata["total_after_score_filter"] = len(filtered_candidates)

    selected_candidates = select_top_candidates(filtered_candidates, top_candidates_for_genres)
    metadata["total_selected_for_genres"] = len(selected_candidates)

    raw_genre_scores, genre_counts = aggregate_genre_scores(selected_candidates)
    normalized_genre_scores = normalize_genre_scores(raw_genre_scores, genre_counts, epsilon=EPSILON)
    ranked_genres = rank_genres(
        normalized_genre_scores=normalized_genre_scores,
        raw_genre_scores=raw_genre_scores,
        genre_counts=genre_counts,
        limit=top_genres_to_return,
    )

    top_genre_names = [item["genre"] for item in ranked_genres]
    grouped_movies = group_movies_by_genre(
        selected_candidates,
        top_genres=top_genre_names,
        movies_per_genre=movies_per_genre,
    )

    skipped_reasons_count: dict[str, int] = defaultdict(int)
    for source in (mapping_skips, metadata_skips):
        for reason, count in source.items():
            skipped_reasons_count[reason] += int(count)
    metadata["skipped_reasons_count"] = dict(skipped_reasons_count)

    # TODO(phase-4C): apply watched-item exclusion before final top-N ranking.
    return {
        "candidates": selected_candidates,
        "ranked_genres": ranked_genres,
        "genre_groups": grouped_movies,
        "metadata": metadata,
    }
