# schemas

Pydantic request/response models, mirroring each feature area in `api/v1/`.

## Files

- `auth.py`, `tenant.py`, `discover.py`, `graph.py`, `validate.py`, `pathfinder.py`, `insightai.py`, `reports.py`, `watch.py`

Each schema module pairs with the identically-named router in `api/v1/` and, where applicable, the underlying model in `models/`.
