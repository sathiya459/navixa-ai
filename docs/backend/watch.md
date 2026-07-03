# watch — NAVIXA Watch

Scheduled discovery and change detection between audit job snapshots.

## Files

- `diff.py` — pure, DB-free resource diffing logic.
- `service.py` — `run_change_detection`, `get_due_schedules`, `mark_schedule_run`; compares two audit jobs' snapshots into `ResourceChange` rows.

## Notes

Schedules are stored in `models/scheduled_discovery.py`; the actual scheduled runs are dispatched through `workers/` (Celery).
