# ML Recommendation Service

Standalone Python microservice for ML scoring/ranking.

## Purpose
- Load embedding artifacts (`.npy`) at startup
- Expose online ranking endpoint for candidate items
- Keep ML logic separate from Java services

## Structure
- `app/main.py`: FastAPI entrypoint
- `app/config.py`: runtime config
- `app/loader.py`: artifact loading
- `app/scorer.py`: hybrid scoring logic
- `app/schemas.py`: request/response models
- `artifacts/`: model files (`user_embeddings.npy`, `item_embeddings.npy`, etc.)

## Run
```bash
cd recommendation_engine/ml-recommendation-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8090 --reload
```

## Health check
```bash
curl http://localhost:8090/health
```
