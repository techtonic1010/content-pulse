import json
from collections import Counter
from typing import Any

import numpy as np

from app.redis_store import RedisEventStore

SUPPORTED_EVENT_TYPES = {"COMPLETE", "PLAY", "CLICK", "SKIP"}


def fetch_user_events(redis_store: RedisEventStore, user_id: str, limit: int = 50) -> list[str]:
    return redis_store.get_user_events(user_id, limit=limit)


def parse_event(json_string: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        parsed = json.loads(json_string)
    except Exception:
        return None, "invalid_json"

    if not isinstance(parsed, dict):
        return None, "invalid_json"
    return parsed, None


def validate_event(parsed_event: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    content_id = parsed_event.get("contentId")
    if not isinstance(content_id, str) or not content_id.strip():
        return None, "missing_contentId"

    event_type = parsed_event.get("eventType")
    if not isinstance(event_type, str) or event_type not in SUPPORTED_EVENT_TYPES:
        return None, "invalid_eventType"

    timestamp_raw = parsed_event.get("timestamp")
    timestamp: int
    if isinstance(timestamp_raw, bool):
        return None, "invalid_timestamp"
    if isinstance(timestamp_raw, int):
        timestamp = timestamp_raw
    else:
        try:
            timestamp = int(timestamp_raw)
        except Exception:
            return None, "invalid_timestamp"

    completion_ratio = parsed_event.get("completionRatio")
    if completion_ratio is not None:
        try:
            completion_ratio = float(completion_ratio)
        except Exception:
            completion_ratio = None

    return {
        "contentId": content_id,
        "eventType": event_type,
        "completionRatio": completion_ratio,
        "timestamp": timestamp,
    }, None


def build_content_to_index_map(item_ids: np.ndarray) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for idx, raw_item_id in enumerate(item_ids):
        item_id = raw_item_id.item() if hasattr(raw_item_id, "item") else raw_item_id
        item_str = str(item_id)
        mapping[item_str] = idx

        if item_str.isdigit():
            mapping[f"movie_{item_str}"] = idx

    return mapping


def map_to_embedding(content_id: str, content_to_index: dict[str, int]) -> tuple[int | None, str | None]:
    # Direct lookup first (supports exact keys in mapping).
    if content_id in content_to_index:
        return int(content_to_index[content_id]), None

    # Support event keys shaped like movie_6 by extracting numeric movie id.
    normalized = content_id.strip()
    if normalized.startswith("movie_"):
        suffix = normalized[len("movie_"):]
        if suffix.isdigit():
            numeric_id = int(suffix)
            if numeric_id in content_to_index:
                return int(content_to_index[numeric_id]), None

    # Support plain digit strings like "6".
    if normalized.isdigit():
        numeric_id = int(normalized)
        if numeric_id in content_to_index:
            return int(content_to_index[numeric_id]), None

    return None, "embedding_not_found"


def build_valid_event_object(
    content_id: str,
    event_type: str,
    completion_ratio: float | None,
    timestamp: int,
    embedding: np.ndarray,
) -> dict[str, Any]:
    return {
        "contentId": content_id,
        "eventType": event_type,
        "completionRatio": completion_ratio,
        "timestamp": timestamp,
        "embedding": embedding.tolist(),
    }


def prepare_events_with_embeddings(
    user_id: str,
    redis_store: RedisEventStore,
    item_embeddings: np.ndarray,
    content_to_index: dict[str, int],
    limit: int = 50,
) -> dict[str, Any]:
    raw_events = fetch_user_events(redis_store, user_id, limit=limit)
    skipped_reasons = Counter()
    valid_events: list[dict[str, Any]] = []

    for raw_event in raw_events:
        parsed_event, parse_error = parse_event(raw_event)
        if parse_error:
            skipped_reasons[parse_error] += 1
            continue

        validated_event, validation_error = validate_event(parsed_event)
        if validation_error:
            skipped_reasons[validation_error] += 1
            continue

        content_id = validated_event["contentId"]
        embedding_index, map_error = map_to_embedding(content_id, content_to_index)
        if map_error:
            skipped_reasons[map_error] += 1
            continue

        embedding = item_embeddings[embedding_index]
        if getattr(embedding, "shape", None) != (128,):
            skipped_reasons["invalid_embedding_shape"] += 1
            continue

        valid_events.append(
            build_valid_event_object(
                content_id=validated_event["contentId"],
                event_type=validated_event["eventType"],
                completion_ratio=validated_event["completionRatio"],
                timestamp=validated_event["timestamp"],
                embedding=embedding,
            )
        )

    return {
        "valid_events": valid_events,
        "metadata": {
            "total_events_fetched": len(raw_events),
            "total_valid_events": len(valid_events),
            "total_skipped_events": len(raw_events) - len(valid_events),
            "skipped_reasons_count": dict(skipped_reasons),
        },
    }