# tenant_registry

Cloud tenant/scope registry, sync, and connection management.

## Files

- `service.py` — CRUD for `CloudTenant`/`CloudScope`.
- `account_sync.py` — diffs cloud-side accounts/subscriptions against registered scopes using delegated SSO.
- `azure_import.py` — Azure tenant auto-discovery/onboarding: lists the Azure AD tenants visible to a connection and imports selected ones along with their subscriptions (as scopes).
- `aws_import.py` — AWS account auto-discovery/onboarding. Unlike Azure AD (a real tenant can genuinely contain several subscriptions), AWS's delegated SSO session (IAM Identity Center `ListAccounts`) has no separate tenant concept — it's a flat list of accounts. So this collapses to **one `CloudTenant` per connection**, auto-created on first import (`external_tenant_id` is a synthetic `"aws-connection:{connection.id}"` — not a real AWS identifier, matching the manual "Add Tenant" dialog's own "AWS Organization ID or root account ID" placeholder in spirit but without requiring the user to actually know one), with each selected account added as an `account`-type `CloudScope` under that single tenant. This mirrors `account_sync.py`'s existing "Sync Accounts" feature (which already treats AWS accounts as scopes) and reuses its `list_sso_accounts` discovery call rather than duplicating tenant-per-account logic.
- `connection_service.py` — manages `EnvironmentConnection` root-credential sessions per environment + provider.

## Notes

This is where the two credential modes live side by side: `connection_service.py` handles static root credentials, while `account_sync.py` uses the delegated SSO path from `auth/`.

Tenant Registry's "Add Tenant" dialog auto-populates from the connection for AWS and Azure (`azure_import.py` / `aws_import.py`, exposed via `api/v1/connections.py`'s `/{provider}/available-tenants` and `/{provider}/import-tenants` routes); GCP/OCI still use the manual entry form since they have no import implementation yet. Note that for AWS these routes operate on accounts-to-become-scopes under one tenant, not tenant candidates — they keep the same names/shapes as Azure's routes for symmetry with the shared frontend dialog, but the semantics differ per provider (see `aws_import.py` above).

**One-AWS-tenant-per-connection is enforced at the DB level**, not just in application logic: migration `c3d4e5f6a7b8` adds a partial unique index on `cloud_tenants(connection_id) WHERE provider = 'aws'`. This exists because the application-level "find-or-create" check in `aws_import.import_tenants` is a classic check-then-act race — two near-simultaneous imports for the same connection (e.g. a fast double-click before the "Add Selected" button's disabled state takes effect) could both see no existing tenant and both create one, producing duplicate AWS tenants for one connection. This actually happened in practice. `import_tenants` catches the resulting `IntegrityError`, rolls back, and re-fetches the tenant that won the race, so the loser's request still succeeds by reusing it instead of erroring out.
