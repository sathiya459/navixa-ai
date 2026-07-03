# internet_path_engine — NAVIXA Pathfinder

Internet ingress/egress exposure analysis.

## Files

- `analyzer.py` — exposure analysis over the NetworkX graph at the gateway and security-group level.
- `service.py` — `run_pathfinder(direction)`, where direction is ingress, egress, or both.

## Notes

Shares the in-memory NetworkX graph-building approach used by `hub_spoke_validator/`, applied to a different analysis question (what's reachable from/to the internet, not hub-spoke compliance).
