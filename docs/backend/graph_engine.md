# graph_engine — NAVIXA Graph

Persistent topology storage in Neo4j.

## Files

- `schema.py` — resource-type-to-Neo4j-label vocabulary and relationship constants.
- `session.py` — Neo4j driver singleton.
- `writer.py` — builds/executes Cypher `MERGE` statements to sync an audit job's normalized inventory into the `navixa_graph`.
- `queries.py` — read-side Cypher backing the Graph API (`api/v1/graph.py`).

## Notes

Consumes `NetworkResource` records produced by `collectors/` (via `normalization.py`) and written after each Discover run (see `workers/tasks.py`).
