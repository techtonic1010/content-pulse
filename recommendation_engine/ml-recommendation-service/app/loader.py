from dataclasses import dataclass
from pathlib import Path
import pickle
import csv
from typing import Any

import numpy as np


@dataclass
class Artifacts:
    user_embeddings: np.ndarray
    item_embeddings: np.ndarray
    user_ids: np.ndarray
    item_ids: np.ndarray


@dataclass
class MapperArtifacts:
    item_embeddings: np.ndarray
    movie2idx: dict[Any, int]


def _load_array(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}")
    return np.load(path, allow_pickle=True)


def load_artifacts(user_embeddings_path: Path, item_embeddings_path: Path, user_ids_path: Path, item_ids_path: Path) -> Artifacts:
    return Artifacts(
        user_embeddings=_load_array(user_embeddings_path),
        item_embeddings=_load_array(item_embeddings_path),
        user_ids=_load_array(user_ids_path),
        item_ids=_load_array(item_ids_path),
    )


def _load_pickle(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}")
    with path.open("rb") as file_obj:
        return pickle.load(file_obj)


def load_mapper_artifacts(item_embeddings_path: Path, movie2idx_path: Path) -> MapperArtifacts:
    item_embeddings = _load_array(item_embeddings_path)
    movie2idx = _load_pickle(movie2idx_path)
    if not isinstance(movie2idx, dict):
        raise ValueError("movie2idx.pkl must contain a dictionary")
    return MapperArtifacts(item_embeddings=item_embeddings, movie2idx=movie2idx)


def load_faiss_index(index_path: Path):
    try:
        import faiss  # type: ignore
    except Exception as exc:
        raise RuntimeError("faiss_dependency_not_installed") from exc

    if not index_path.exists():
        raise FileNotFoundError(f"Missing artifact: {index_path}")

    return faiss.read_index(str(index_path))


def load_movie_metadata_csv(csv_path: Path) -> dict[str, dict[str, Any]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing metadata CSV: {csv_path}")

    metadata_by_movie_id: dict[str, dict[str, Any]] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            movie_id = str(row.get("movieId") or "").strip()
            if not movie_id:
                continue

            raw_title = str(row.get("title") or f"movie_{movie_id}").strip()
            raw_genres = str(row.get("genres") or "").strip()
            if not raw_genres or raw_genres == "(no genres listed)":
                genres = ["Unknown"]
            else:
                genres = [genre.strip() for genre in raw_genres.split("|") if genre.strip()]
                if not genres:
                    genres = ["Unknown"]

            metadata_by_movie_id[movie_id] = {
                "movieId": movie_id,
                "title": raw_title,
                "genres": genres,
            }

    return metadata_by_movie_id
