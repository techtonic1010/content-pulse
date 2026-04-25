from typing import Any

import numpy as np

EPSILON = 1e-8
EXPECTED_DIM = 128


def validate_vector_shape(vector: np.ndarray, expected_dim: int = EXPECTED_DIM) -> bool:
    return isinstance(vector, np.ndarray) and vector.shape == (expected_dim,)


def validate_vector_values(vector: np.ndarray) -> tuple[bool, bool, bool]:
    has_nan = bool(np.isnan(vector).any())
    has_inf = bool(np.isinf(vector).any())
    is_finite = bool(np.isfinite(vector).all())
    return is_finite, has_nan, has_inf


def compute_l2_norm(vector: np.ndarray) -> float:
    return float(np.linalg.norm(vector))


def l2_normalize(vector: np.ndarray, epsilon: float = EPSILON) -> tuple[np.ndarray | None, float]:
    norm = compute_l2_norm(vector)
    if norm <= epsilon:
        return None, norm

    normalized = vector / max(norm, epsilon)
    if not np.isfinite(normalized).all():
        return None, norm

    return normalized, norm


def build_readiness_response(
    user_vector: np.ndarray,
    is_faiss_ready: bool,
    fallback_used: bool,
    reason: str | None,
    metadata: dict[str, Any],
    norm_before_final: float,
) -> dict[str, Any]:
    _, has_nan, has_inf = validate_vector_values(user_vector)
    norm_after_final = compute_l2_norm(user_vector)

    event_counts = {
        "received": int(metadata.get("total_events_received", 0)),
        "used": int(metadata.get("total_events_used", 0)),
        "skipped": int(metadata.get("total_events_skipped", 0)),
    }

    return {
        "user_vector": user_vector.astype(np.float32),
        "is_faiss_ready": is_faiss_ready,
        "fallback_used": fallback_used,
        "reason": reason,
        "event_counts": event_counts,
        "vector_stats": {
            "norm_before_final": norm_before_final,
            "norm_after_final": norm_after_final,
            "has_nan": has_nan,
            "has_inf": has_inf,
        },
        "debug": {
            "skipped_reasons_count": metadata.get("skipped_reasons_count", {}),
            "raw_weight_sum": float(metadata.get("raw_weight_sum", 0.0)),
            "l2_norm_before_normalization": float(metadata.get("l2_norm_before_normalization", 0.0)),
            "vector_built": bool(metadata.get("vector_built", False)),
        },
    }


def _coerce_vector(vector: Any) -> np.ndarray | None:
    if vector is None:
        return None
    try:
        return np.asarray(vector, dtype=np.float64)
    except Exception:
        return None


def build_faiss_ready_vector(
    raw_vector: Any,
    metadata: dict[str, Any],
    fallback_vector: Any = None,
) -> dict[str, Any]:
    reason: str | None = None
    fallback_used = False

    vector = _coerce_vector(raw_vector)
    if vector is None:
        reason = "missing_vector"
    elif not validate_vector_shape(vector):
        reason = "invalid_vector_shape"
    else:
        is_finite, has_nan, has_inf = validate_vector_values(vector)
        if not is_finite:
            reason = "invalid_vector_values"

    norm_before_final = 0.0

    if reason is None and vector is not None:
        normalized, norm_before_final = l2_normalize(vector)
        if normalized is None:
            reason = "degenerate_vector_norm"
        else:
            return build_readiness_response(
                user_vector=normalized,
                is_faiss_ready=True,
                fallback_used=False,
                reason=None,
                metadata=metadata,
                norm_before_final=norm_before_final,
            )

    fallback_used = True
    fallback = _coerce_vector(fallback_vector)
    if fallback is not None and validate_vector_shape(fallback):
        is_finite, _, _ = validate_vector_values(fallback)
        if is_finite:
            fallback_normalized, norm_before_final = l2_normalize(fallback)
            if fallback_normalized is not None:
                return build_readiness_response(
                    user_vector=fallback_normalized,
                    is_faiss_ready=True,
                    fallback_used=fallback_used,
                    reason=reason,
                    metadata=metadata,
                    norm_before_final=norm_before_final,
                )

    zero_vector = np.zeros(EXPECTED_DIM, dtype=np.float64)
    norm_before_final = compute_l2_norm(zero_vector)
    return build_readiness_response(
        user_vector=zero_vector,
        is_faiss_ready=False,
        fallback_used=True,
        reason=reason or "fallback_vector_invalid",
        metadata=metadata,
        norm_before_final=norm_before_final,
    )
