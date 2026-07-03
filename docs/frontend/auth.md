# auth

React Context-based auth/authorization state and route guards (not a routing library).

## Files

- `AuthContext.tsx` — holds the logged-in `User`, exposes `login`/`logout`/`refreshUser`, persists tokens to `localStorage`, bootstraps the session on mount via `getCurrentUser()`.
- `EnvironmentContext.tsx` — tracks a dev/prod environment toggle (admin-only, persisted in `localStorage`, forced to `dev` for non-admins — server still enforces this).
- `RequireAuth.tsx` — route guard redirecting unauthenticated users to `/login`.
- `RequireAdmin.tsx` — route guard redirecting non-admins away from admin-only routes.

## Notes

Both route guards are explicitly UX conveniences — real enforcement happens server-side (`backend/app/auth/dependencies.py`).
