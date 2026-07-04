# NAVIXA AI — Instructions for Claude

## Documentation maintenance

Whenever you make a code or configuration change, update the corresponding
markdown doc in `docs/` in the same turn — do not ask for confirmation first.

- Backend module changes (`backend/app/<module>/...`) → `docs/backend/<module>.md`
- Frontend module changes (`frontend/src/<module>/...`) → `docs/frontend/<module>.md`
- Changes to local dev startup/services/ports/env → `docs/RUNNING.md`
- New modules or top-level architecture/stack changes → `docs/README.md`

If no doc file exists yet for a changed area, create one following the existing
style in `docs/backend/` or `docs/frontend/`. Keep updates scoped to what actually
changed — don't rewrite unrelated sections.
