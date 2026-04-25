from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = BASE_DIR / "artifacts"
APP_DIR = BASE_DIR / "app"
EMBEDDINGS_DIR = APP_DIR / "embeddings"

def _resolve_artifact(filename: str) -> Path:
	artifact_path = ARTIFACT_DIR / filename
	if artifact_path.exists():
		return artifact_path
	return BASE_DIR / filename


USER_EMBEDDINGS_PATH = _resolve_artifact("user_embeddings.npy")
ITEM_EMBEDDINGS_PATH = _resolve_artifact("item_embeddings.npy")
USER_IDS_PATH = _resolve_artifact("user_ids.npy")
ITEM_IDS_PATH = _resolve_artifact("item_ids.npy")

MAPPER_ITEM_EMBEDDINGS_PATH = EMBEDDINGS_DIR / "item_embeddings (2).npy"
MAPPER_MOVIE2IDX_PATH = EMBEDDINGS_DIR / "movie2idx.pkl"
FAISS_INDEX_PATH = EMBEDDINGS_DIR / "item_index.faiss"
MOVIES_METADATA_CSV_PATH = Path(os.getenv("MOVIES_METADATA_CSV_PATH", str(BASE_DIR.parent.parent / "movie_lens_samll_dataset" / "movies.csv")))

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

REDIS_MOVIE_META_KEY_PREFIX = os.getenv("REDIS_MOVIE_META_KEY_PREFIX", "movie_meta:")
REDIS_MOVIE_GENRES_KEY_PREFIX = os.getenv("REDIS_MOVIE_GENRES_KEY_PREFIX", "movie_genres:")
REDIS_MOVIE_TITLE_KEY_PREFIX = os.getenv("REDIS_MOVIE_TITLE_KEY_PREFIX", "movie_title:")

TOP_K_FAISS = int(os.getenv("TOP_K_FAISS", "300"))
MIN_SIMILARITY_SCORE = float(os.getenv("MIN_SIMILARITY_SCORE", "0.0"))
TOP_CANDIDATES_FOR_GENRES = int(os.getenv("TOP_CANDIDATES_FOR_GENRES", "50"))
TOP_GENRES_TO_RETURN = int(os.getenv("TOP_GENRES_TO_RETURN", "5"))
TOP_MOVIES_PER_GENRE = int(os.getenv("TOP_MOVIES_PER_GENRE", "5"))
EPSILON = float(os.getenv("EPSILON", "1e-8"))
