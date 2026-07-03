# tenant_registry

Cloud tenant/scope registry, sync, and connection management.

## Files

- `service.py` — CRUD for `CloudTenant`/`CloudScope`.
- `account_sync.py` — diffs cloud-side accounts/subscriptions against registered scopes using delegated SSO.
- `azure_import.py` — Azure tenant auto-discovery/onboarding.
- `connection_service.py` — manages `EnvironmentConnection` root-credential sessions per environment + provider.

## Notes

This is where the two credential modes live side by side: `connection_service.py` handles static root credentials, while `account_sync.py` uses the delegated SSO path from `auth/`.
