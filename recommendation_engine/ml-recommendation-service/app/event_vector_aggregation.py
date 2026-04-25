from collections import Counter
from typing import Any

import numpy as np

EPSILON = 1e-8


def validate_weighted_event(event: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    embedding = event.get("embedding")
    if embedding is None:
        return None, "invalid_embedding"

    try:
        embedding_array = np.asarray(embedding, dtype=np.float64)
    except Exception:
        return None, "invalid_embedding"

    if embedding_array.shape != (128,):
        return None, "invalid_embedding"

    if not np.isfinite(embedding_array).all():
        return None, "invalid_embedding"

    weight = event.get("final_weight")
    try:
        weight_value = float(weight)
    except (TypeError, ValueError):
        return None, "invalid_final_weight"

    if not np.isfinite(weight_value):
        return None, "invalid_final_weight"

    return {
        "contentId": event.get("contentId"),
        "eventType": event.get("eventType"),
        "embedding": embedding_array,
        "final_weight": weight_value,
    }, None


def accumulate_weighted_embedding(accumulator: np.ndarray, embedding: np.ndarray, weight: float) -> tuple[np.ndarray, float]:
    contribution = weight * embedding
    accumulator += contribution
    contribution_norm = float(np.linalg.norm(contribution))
    return accumulator, contribution_norm


def compute_raw_user_vector(weighted_events: list[dict[str, Any]]) -> dict[str, Any]:
    weighted_sum = np.zeros(128, dtype=np.float64)
    denominator_sum = 0.0

    skipped_reasons_count = Counter()
    debug_trace: list[dict[str, Any]] = []
    total_used = 0

    for event in weighted_events:
        validated_event, validation_error = validate_weighted_event(event)
        if validation_error:
            skipped_reasons_count[validation_error] += 1
            debug_trace.append(
                {
                    "contentId": event.get("contentId"),
                    "eventType": event.get("eventType"),
                    "final_weight": event.get("final_weight"),
                    "skipped_reason": validation_error,
                }
            )
            continue

        final_weight = validated_event["final_weight"]
        weighted_sum, contribution_norm = accumulate_weighted_embedding(
            weighted_sum,
            validated_event["embedding"],
            final_weight,
        )
        denominator_sum += abs(final_weight)
        total_used += 1

        debug_trace.append(
            {
                "contentId": validated_event.get("contentId"),
                "eventType": validated_event.get("eventType"),
                "final_weight": final_weight,
                "contribution_norm": contribution_norm,
            }
        )

    raw_user_vector = weighted_sum / (denominator_sum + EPSILON)
    return {
        "raw_user_vector": raw_user_vector,
        "raw_weight_sum": denominator_sum,
        "total_used": total_used,
        "skipped_reasons_count": dict(skipped_reasons_count),
        "debug_trace": debug_trace,
    }


def l2_normalize(vector: np.ndarray) -> tuple[np.ndarray | None, float]:
    l2_norm = float(np.linalg.norm(vector))
    if l2_norm <= EPSILON:
        return None, l2_norm

    normalized = vector / (l2_norm + EPSILON)
    if not np.isfinite(normalized).all():
        return None, l2_norm

    return normalized, l2_norm


def build_user_vector(weighted_events: list[dict[str, Any]]) -> dict[str, Any]:
    total_received = len(weighted_events)

    raw_result = compute_raw_user_vector(weighted_events)
    raw_user_vector = raw_result["raw_user_vector"]
    normalized_vector, l2_norm_before_normalization = l2_normalize(raw_user_vector)

    vector_built = normalized_vector is not None
    final_vector = normalized_vector.astype(np.float32) if vector_built else None

    metadata = {
        "total_events_received": total_received,
        "total_events_used": raw_result["total_used"],
        "total_events_skipped": total_received - raw_result["total_used"],
        "raw_weight_sum": raw_result["raw_weight_sum"],
        "l2_norm_before_normalization": l2_norm_before_normalization,
        "skipped_reasons_count": raw_result["skipped_reasons_count"],
        "vector_built": vector_built,
        "debug_trace": raw_result["debug_trace"],
    }

    return {
        "final_user_vector": final_vector,
        "metadata": metadata,
    }
