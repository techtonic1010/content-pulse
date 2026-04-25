from typing import Any

import numpy as np

EPSILON = 1e-8
EXPECTED_DIM = 128


def validate_user_vector(user_vector: Any) -> tuple[np.ndarray | None, str | None]:
    if user_vector is None:
        return None, "missing_user_vector"

    try:
        vector = np.asarray(user_vector, dtype=np.float64)
    except Exception:
        return None, "invalid_user_vector"

    if vector.shape != (EXPECTED_DIM,):
        return None, "invalid_user_vector_shape"

    if not np.isfinite(vector).all():
        return None, "invalid_user_vector_values"

    return vector, None


def normalize_vector(user_vector: np.ndarray, epsilon: float = EPSILON) -> tuple[np.ndarray | None, float]:
    norm = float(np.linalg.norm(user_vector))
    if norm <= epsilon:
        return None, norm

    normalized = user_vector / norm
    if not np.isfinite(normalized).all():
        return None, norm

    return normalized, norm


def prepare_query(user_vector: np.ndarray) -> np.ndarray:
    return user_vector.reshape(1, EXPECTED_DIM).astype(np.float32)


def query_faiss(index: Any, user_query: np.ndarray, k: int, nprobe: int | None = None) -> tuple[np.ndarray, np.ndarray, int]:
    if index is None:
        raise RuntimeError("faiss_index_not_loaded")

    n_items = int(index.ntotal)
    effective_k = max(0, min(int(k), n_items))

    if nprobe is not None and hasattr(index, "nprobe"):
        index.nprobe = int(nprobe)

    if effective_k == 0:
        return np.empty((1, 0), dtype=np.float32), np.empty((1, 0), dtype=np.int64), 0

    scores, indices = index.search(user_query, effective_k)
    return scores, indices, effective_k


def format_results(scores: np.ndarray, indices: np.ndarray) -> tuple[list[int], list[float]]:
    if scores.ndim == 2:
        flat_scores = scores[0]
    else:
        flat_scores = scores

    if indices.ndim == 2:
        flat_indices = indices[0]
    else:
        flat_indices = indices

    result_indices: list[int] = []
    result_scores: list[float] = []
    seen: set[int] = set()

    for idx_value, score_value in zip(flat_indices, flat_scores):
        idx_int = int(idx_value)
        if idx_int < 0:
            continue
        if idx_int in seen:
            continue
        seen.add(idx_int)
        result_indices.append(idx_int)
        result_scores.append(float(score_value))

    return result_indices, result_scores


def retrieve_candidates(
    index: Any,
    user_vector: Any,
    k: int = 5,
    candidate_pool_k: int = 50,
    nprobe: int | None = None,
) -> dict[str, Any]:
    validated_vector, validation_error = validate_user_vector(user_vector)
    if validation_error:
        return {
            "indices": [],
            "scores": [],
            "k": 0,
            "vector_norm": 0.0,
            "is_normalized": False,
            "reason": validation_error,
            "debug": {},
        }

    normalized_vector, vector_norm = normalize_vector(validated_vector)
    if normalized_vector is None:
        return {
            "indices": [],
            "scores": [],
            "k": 0,
            "vector_norm": vector_norm,
            "is_normalized": False,
            "reason": "zero_or_degenerate_user_vector",
            "debug": {},
        }

    if index is None:
        raise RuntimeError("faiss_index_not_loaded")

    requested_k = max(0, int(k))
    requested_pool_k = max(requested_k, int(candidate_pool_k))

    query_vector = prepare_query(normalized_vector)
    scores, indices, _ = query_faiss(index, query_vector, requested_pool_k, nprobe=nprobe)
    formatted_indices, formatted_scores = format_results(scores, indices)

    effective_k = min(requested_k, len(formatted_indices))
    final_indices = formatted_indices[:effective_k]
    final_scores = formatted_scores[:effective_k]

    debug = {}
    if final_scores:
        scores_array = np.asarray(final_scores, dtype=np.float64)
        debug = {
            "top_score": float(scores_array.max()),
            "min_score": float(scores_array.min()),
            "mean_score": float(scores_array.mean()),
            "candidate_pool_k": float(requested_pool_k),
        }

    return {
        "indices": final_indices,
        "scores": final_scores,
        "k": effective_k,
        "vector_norm": vector_norm,
        "is_normalized": True,
        "reason": None,
        "debug": debug,
    }