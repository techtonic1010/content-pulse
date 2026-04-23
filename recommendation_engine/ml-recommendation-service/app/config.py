from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = BASE_DIR / "artifacts"

USER_EMBEDDINGS_PATH = ARTIFACT_DIR / "user_embeddings.npy"
ITEM_EMBEDDINGS_PATH = ARTIFACT_DIR / "item_embeddings.npy"
USER_IDS_PATH = ARTIFACT_DIR / "user_ids.npy"
ITEM_IDS_PATH = ARTIFACT_DIR / "item_ids.npy"
