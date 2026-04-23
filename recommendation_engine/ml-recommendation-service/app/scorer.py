from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence

import numpy as np


@dataclass
class ModelScorer:
    user_embeddings: np.ndarray
    item_embeddings: np.ndarray
    user_ids: np.ndarray
    item_ids: np.ndarray
    user_index: Dict[str, int]
    item_index: Dict[str, int]

    @classmethod
    def from_artifacts(
            cls,
            user_embeddings: np.ndarray,
            item_embeddings: np.ndarray,
            user_ids: np.ndarray,
            item_ids: np.ndarray,
    ) -> "ModelScorer":
        user_lookup = {str(uid): i for i, uid in enumerate(user_ids.tolist())}
        item_lookup = {str(iid): i for i, iid in enumerate(item_ids.tolist())}

        return cls(
            user_embeddings=user_embeddings,
            item_embeddings=item_embeddings,
            user_ids=user_ids,
            item_ids=item_ids,
            user_index=user_lookup,
            item_index=item_lookup,
        )

    def get_score(self, user_id: str, item_id: str) -> Optional[float]:
        user_key = str(user_id)
        item_key = str(item_id)

        if user_key not in self.user_index or item_key not in self.item_index:
            return None

        user_idx = self.user_index[user_key]
        item_idx = self.item_index[item_key]

        u_vec = self.user_embeddings[user_idx]

        # Support both common layouts for item embeddings.
        # If matrix is [latent_dim, item_count], use column access.
        # If matrix is [item_count, latent_dim], use row access.
        if self.item_embeddings.ndim != 2:
            return None

        if self.item_embeddings.shape[1] == len(self.item_ids):
            v_vec = self.item_embeddings[:, item_idx]
        elif self.item_embeddings.shape[0] == len(self.item_ids):
            v_vec = self.item_embeddings[item_idx]
        else:
            return None

        return float(np.dot(u_vec, v_vec))

    def rank_items(self, user_id: str, candidate_items: List[str]) -> List[str]:
        scores = []

        for item in candidate_items:
            score = self.get_score(user_id, item)

            if score is None:
                score = 0  # fallback

            scores.append((item, score))

        # sort descending
        scores.sort(key=lambda x: x[1], reverse=True)

        return [item for item, _ in scores]

    def content_score(self, user_genres: Mapping[str, float], item_genres: Sequence[str]) -> float:
        score = 0.0
        for genre in item_genres:
            score += float(user_genres.get(genre, 0.0))
        return score

    def final_score(
            self,
            user_id: str,
            item_id: str,
            user_genres: Mapping[str, float],
            item_genres: Sequence[str],
            popularity: float,
    ) -> float:
        cf = self.get_score(user_id, item_id) or 0.0
        cb = self.content_score(user_genres, item_genres)

        # normalize roughly (simple trick)
        cf = cf / 10.0
        cb = cb / 10.0

        return 0.6 * cf + 0.3 * cb + 0.1 * float(popularity)

    def rank(
            self,
            user_id: str,
            candidates: Sequence[str],
            user_genres: Mapping[str, float],
            item_data: Mapping[str, Mapping[str, object]],
    ) -> List[str]:
        results = []

        for item in candidates:
            if item not in item_data:
                continue

            data = item_data[item]
            genres_raw = data.get("genres", [])
            popularity_raw = data.get("popularity", 0.0)

            genres = genres_raw if isinstance(genres_raw, list) else []
            try:
                popularity = float(popularity_raw)
            except (TypeError, ValueError):
                popularity = 0.0

            score = self.final_score(
                user_id,
                item,
                user_genres,
                genres,
                popularity,
            )
            results.append((item, score))

        results.sort(key=lambda x: x[1], reverse=True)

        return [x[0] for x in results[:10]]
