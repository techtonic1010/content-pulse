from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Artifacts:
    user_embeddings: np.ndarray
    item_embeddings: np.ndarray
    user_ids: np.ndarray
    item_ids: np.ndarray


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
