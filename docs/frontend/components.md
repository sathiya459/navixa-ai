# components

Shared UI shell components.

## Files

- `DashboardLayout.tsx` — the app shell: fixed `AppBar` (branding, dev/prod environment toggle for admins, user avatar menu with logout) plus a permanent `Drawer` sidebar built from a `NAV_ITEMS` config array (Dashboard, Tenants, Audit Jobs, Connections — admin-only), and a `Container`/`Outlet` for routed page content.
