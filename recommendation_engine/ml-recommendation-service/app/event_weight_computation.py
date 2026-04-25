import math
import time
from collections import Counter
from typing import Any

import numpy as np

EVENT_TYPE_WEIGHTS = {
    "COMPLETE": 3.0,
    "PLAY": 2.0,
    "CLICK": 1.0,
    "SKIP": -0.5,
}

HALF_LIFE_SECONDS = 7 * 24 * 3600
LAMBDA_DECAY = math.log(2) / HALF_LIFE_SECONDS


def get_event_type_weight(event_type: str) -> tuple[float | None, str | None]:
    weight = EVENT_TYPE_WEIGHTS.get(event_type)
    if weight is None:
        return None, "unsupported_event_type"
    return weight, None


def compute_completion_weight(completion_ratio: Any, event_type: str) -> tuple[float | None, str | None]:
    if completion_ratio is None:
        # Safe fallback explicitly requested for missing completionRatio.
        return 1.0, None

    if isinstance(completion_ratio, bool):
        return None, "invalid_completion_ratio"

    try:
        ratio = float(completion_ratio)
    except (TypeError, ValueError):
        return None, "invalid_completion_ratio"

    if ratio < 0.0 or ratio > 1.0:
        return None, "invalid_completion_ratio"

    return 0.3 + (0.7 * ratio), None


def compute_recency_weight(timestamp: Any, current_unix_time: int) -> tuple[float | None, str | None]:
    if isinstance(timestamp, bool):
        return None, "invalid_timestamp"

    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return None, "invalid_timestamp"

    age_seconds = current_unix_time - ts
    if age_seconds < 0:
        age_seconds = 0

    return math.exp(-LAMBDA_DECAY * age_seconds), None


def compute_final_weight(event_type_weight: float, completion_weight: float, recency_weight: float) -> float:
    return event_type_weight * completion_weight * recency_weight


def validate_weight_input(event: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    content_id = event.get("contentId")
    if not isinstance(content_id, str) or not content_id.strip():
        return None, "missing_contentId"

    event_type = event.get("eventType")
    if not isinstance(event_type, str) or not event_type.strip():
        return None, "unsupported_event_type"

    timestamp = event.get("timestamp")
    if timestamp is None:
        return None, "invalid_timestamp"

    embedding = event.get("embedding")
    if embedding is None:
        return None, "invalid_embedding"

    try:
        embedding_array = np.asarray(embedding, dtype=float)
    except Exception:
        return None, "invalid_embedding"

    if embedding_array.shape != (128,):
        return None, "invalid_embedding"

    return {
        "contentId": content_id,
        "eventType": event_type,
        "completionRatio": event.get("completionRatio"),
        "timestamp": timestamp,
        "embedding": embedding_array,
    }, None


def attach_weight_to_event(event: dict[str, Any], weight_components: dict[str, float]) -> dict[str, Any]:
    return {
        "contentId": event["contentId"],
        "eventType": event["eventType"],
        "timestamp": int(event["timestamp"]),
        "embedding": event["embedding"],
        "event_type_weight": weight_components["event_type_weight"],
        "completion_weight": weight_components["completion_weight"],
        "recency_weight": weight_components["recency_weight"],
        "final_weight": weight_components["final_weight"],
    }


def process_event_batch(events: list[dict[str, Any]], current_unix_time: int | None = None) -> dict[str, Any]:
    now_unix = int(time.time()) if current_unix_time is None else int(current_unix_time)

    weighted_events: list[dict[str, Any]] = []
    skipped_reasons_count = Counter()

    for event in events:
        validated_event, validation_error = validate_weight_input(event)
        if validation_error:
            skipped_reasons_count[validation_error] += 1
            continue

        event_type_weight, type_error = get_event_type_weight(validated_event["eventType"])
        if type_error:
            skipped_reasons_count[type_error] += 1
            continue

        completion_weight, completion_error = compute_completion_weight(
            validated_event["completionRatio"],
            validated_event["eventType"],
        )
        if completion_error:
            skipped_reasons_count[completion_error] += 1
            continue

        recency_weight, recency_error = compute_recency_weight(validated_event["timestamp"], now_unix)
        if recency_error:
            skipped_reasons_count[recency_error] += 1
            continue

        final_weight = compute_final_weight(event_type_weight, completion_weight, recency_weight)

        weighted_events.append(
            attach_weight_to_event(
                validated_event,
                {
                    "event_type_weight": event_type_weight,
                    "completion_weight": completion_weight,
                    "recency_weight": recency_weight,
                    "final_weight": final_weight,
                },
            )
        )

    return {
        "weighted_events": weighted_events,
        "metadata": {
            "total_events_received": len(events),
            "total_events_used": len(weighted_events),
            "total_events_skipped": len(events) - len(weighted_events),
            "skipped_reasons_count": dict(skipped_reasons_count),
        },
    }
