from __future__ import annotations

import json
from typing import Any, Protocol


class MovieMetadataStore(Protocol):
    def get_movie_metadata(self, movie_id: str) -> dict[str, Any] | None:
        ...


def _normalize_genres(raw_genres: Any) -> list[str]:
    if isinstance(raw_genres, list):
        genres = [str(genre).strip() for genre in raw_genres if str(genre).strip()]
    elif isinstance(raw_genres, str):
        genres = [genre.strip() for genre in raw_genres.split("|") if genre.strip()]
    else:
        genres = []

    if not genres:
        return ["Unknown"]
    return genres


class RedisMovieMetadataStore:
    def __init__(
        self,
        redis_client: Any,
        meta_key_prefix: str = "movie_meta:",
        genres_key_prefix: str = "movie_genres:",
        title_key_prefix: str = "movie_title:",
    ) -> None:
        self._client = redis_client
        self._meta_key_prefix = meta_key_prefix
        self._genres_key_prefix = genres_key_prefix
        self._title_key_prefix = title_key_prefix

    def get_movie_metadata(self, movie_id: str) -> dict[str, Any] | None:
        # Preferred shape: movie_meta:{movieId} JSON with at least title and genres.
        raw_meta = self._client.get(f"{self._meta_key_prefix}{movie_id}")
        if raw_meta:
            try:
                parsed = json.loads(str(raw_meta))
                title = str(parsed.get("title") or "")
                genres = _normalize_genres(parsed.get("genres"))
                if title:
                    return {
                        "movieId": movie_id,
                        "title": title,
                        "genres": genres,
                    }
            except Exception:
                return None

        raw_genres = self._client.get(f"{self._genres_key_prefix}{movie_id}")
        if not raw_genres:
            return None

        raw_title = self._client.get(f"{self._title_key_prefix}{movie_id}")
        title = str(raw_title or f"movie_{movie_id}")
        genres = _normalize_genres(raw_genres)
        return {
            "movieId": movie_id,
            "title": title,
            "genres": genres,
        }


class InMemoryMovieMetadataStore:
    def __init__(self, metadata_by_movie_id: dict[str, dict[str, Any]]) -> None:
        self._metadata_by_movie_id = metadata_by_movie_id

    def get_movie_metadata(self, movie_id: str) -> dict[str, Any] | None:
        metadata = self._metadata_by_movie_id.get(str(movie_id))
        if metadata is None:
            return None
        return {
            "movieId": str(movie_id),
            "title": str(metadata.get("title") or f"movie_{movie_id}"),
            "genres": _normalize_genres(metadata.get("genres")),
        }


class CompositeMovieMetadataStore:
    def __init__(self, stores: list[MovieMetadataStore]) -> None:
        self._stores = stores

    def get_movie_metadata(self, movie_id: str) -> dict[str, Any] | None:
        for store in self._stores:
            metadata = store.get_movie_metadata(movie_id)
            if metadata is not None:
                return metadata
        return None
