# api

Thin axios wrapper modules, one per backend domain, built on a shared client.

## Files

- `client.ts` — creates the `apiClient` axios instance (base URL from `VITE_API_BASE_URL`); attaches the bearer token from `localStorage`; response interceptors handle 401 (clear tokens, redirect to `/login`) and delegated cloud-auth 409s (opens a popup, waits for a `postMessage` from the backend's delegated-auth flow, then retries the original request).
- `types.ts` — shared TS interfaces/unions (`CloudProvider`, `Tenant`, `User`, `NetworkResource`, `Finding`, etc.).
- `auth.ts` — login/me/logout.
- `tenants.ts` — cloud tenant management.
- `discover.ts` — audit job CRUD + resource fetch for NAVIXA Discover.
- `validate.ts` — runs rule-engine/AI validation and fetches findings.
- `insightai.ts` — lists configured AI providers.
