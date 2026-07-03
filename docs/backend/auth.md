# auth

Local JWT authentication, Microsoft Entra ID SSO, and delegated cloud-auth token handling.

## Files

- `security.py` — bcrypt password hashing, JWT encode/decode.
- `dependencies.py` — FastAPI dependency injection for the current user (`get_current_user`, admin-only guards).
- `entra.py` — Microsoft Entra ID OIDC integration via MSAL.
- `sso_service.py` — SSO login flow; auto-provisions new SSO users as Reader by default.
- `pkce_store.py` — Redis-backed PKCE state store for the delegated cloud-auth popup flow.
- `token_encryption.py` — Fernet-based encryption of stored delegated cloud-SSO tokens at rest.

## Notes

RBAC is two roles: admin and reader (see `models/role.py`). Delegated cloud auth (used by `collectors/` for per-user cloud SSO sessions) is distinct from the app's own JWT auth — it lets Discover collectors act on behalf of a signed-in user's cloud session rather than a static root credential.
