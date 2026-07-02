import { useEffect, useState } from "react";
import axios from "axios";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControlLabel,
  IconButton,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import DeleteIcon from "@mui/icons-material/Delete";
import SyncIcon from "@mui/icons-material/Sync";
import {
  createScope,
  createTenant,
  deleteTenant,
  getAvailableAccounts,
  listScopes,
  listTenants,
  type ScopeCreatePayload,
  type TenantCreatePayload,
} from "../api/tenants";
import type {
  AvailableAccount,
  CloudAuthMode,
  CloudProvider,
  Scope,
  ScopeType,
  Tenant,
} from "../api/types";

const ACCOUNT_SYNC_SUPPORTED: Record<CloudProvider, boolean> = {
  aws: true,
  azure: true,
  gcp: false,
  oci: false,
};

const PROVIDERS: { value: CloudProvider; label: string }[] = [
  { value: "aws", label: "AWS" },
  { value: "azure", label: "Azure" },
  { value: "gcp", label: "GCP" },
  { value: "oci", label: "OCI" },
];

const SCOPE_TYPES_BY_PROVIDER: Record<CloudProvider, ScopeType> = {
  aws: "account",
  azure: "subscription",
  gcp: "project",
  oci: "compartment",
};

const AUTH_MODES: { value: CloudAuthMode; label: string; description: string }[] = [
  { value: "delegated", label: "Delegated (SSO)", description: "Uses your own az/aws/gcloud/oci CLI login" },
  { value: "app_only", label: "App-only", description: "Uses a registered app / service account (headless)" },
];

function TenantScopes({ tenantId, provider }: { tenantId: string; provider: CloudProvider }) {
  const [scopes, setScopes] = useState<Scope[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [externalScopeId, setExternalScopeId] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [syncDialogOpen, setSyncDialogOpen] = useState(false);
  const [availableAccounts, setAvailableAccounts] = useState<AvailableAccount[]>([]);
  const [selectedExternalIds, setSelectedExternalIds] = useState<string[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isAddingSelected, setIsAddingSelected] = useState(false);

  function reload() {
    listScopes(tenantId)
      .then(setScopes)
      .catch(() => setError("Failed to load scopes."));
  }

  useEffect(reload, [tenantId]);

  async function handleAddScope() {
    setIsSubmitting(true);
    try {
      const payload: ScopeCreatePayload = {
        scope_type: SCOPE_TYPES_BY_PROVIDER[provider],
        external_scope_id: externalScopeId,
        display_name: displayName,
      };
      await createScope(tenantId, payload);
      setDialogOpen(false);
      setExternalScopeId("");
      setDisplayName("");
      reload();
    } catch {
      setError("Failed to create scope.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleOpenSync() {
    setSyncDialogOpen(true);
    setIsSyncing(true);
    setError(null);
    try {
      const accounts = await getAvailableAccounts(tenantId);
      setAvailableAccounts(accounts);
      setSelectedExternalIds(accounts.filter((a) => !a.already_added).map((a) => a.external_id));
    } catch (err) {
      const message = axios.isAxiosError(err) ? err.response?.data?.detail : undefined;
      setError(typeof message === "string" ? message : "Failed to discover accounts.");
      setSyncDialogOpen(false);
    } finally {
      setIsSyncing(false);
    }
  }

  function toggleSelectedAccount(externalId: string) {
    setSelectedExternalIds((prev) =>
      prev.includes(externalId) ? prev.filter((id) => id !== externalId) : [...prev, externalId],
    );
  }

  async function handleAddSelectedAccounts() {
    setIsAddingSelected(true);
    try {
      const toAdd = availableAccounts.filter((a) => selectedExternalIds.includes(a.external_id));
      for (const account of toAdd) {
        await createScope(tenantId, {
          scope_type: SCOPE_TYPES_BY_PROVIDER[provider],
          external_scope_id: account.external_id,
          display_name: account.display_name,
        });
      }
      setSyncDialogOpen(false);
      reload();
    } catch {
      setError("Failed to add one or more accounts.");
    } finally {
      setIsAddingSelected(false);
    }
  }

  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      <List dense>
        {scopes.map((scope) => (
          <ListItem key={scope.id} disablePadding sx={{ py: 0.5 }}>
            <ListItemText
              primary={`${scope.display_name} (${scope.scope_type})`}
              secondary={scope.external_scope_id}
            />
            <Chip
              label={scope.is_active ? "active" : "inactive"}
              size="small"
              color={scope.is_active ? "success" : "default"}
            />
          </ListItem>
        ))}
        {scopes.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            No {SCOPE_TYPES_BY_PROVIDER[provider]}s added yet.
          </Typography>
        )}
      </List>
      <Box sx={{ display: "flex", gap: 1, mt: 1 }}>
        <Button size="small" onClick={() => setDialogOpen(true)}>
          Add {SCOPE_TYPES_BY_PROVIDER[provider]}
        </Button>
        <Tooltip
          title={
            ACCOUNT_SYNC_SUPPORTED[provider]
              ? "Check the cloud provider for accounts not yet registered"
              : `Account sync isn't supported for ${provider.toUpperCase()} yet`
          }
        >
          <span>
            <Button
              size="small"
              startIcon={<SyncIcon fontSize="small" />}
              onClick={handleOpenSync}
              disabled={!ACCOUNT_SYNC_SUPPORTED[provider]}
            >
              Sync Accounts
            </Button>
          </span>
        </Tooltip>
      </Box>

      <Dialog open={syncDialogOpen} onClose={() => setSyncDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Sync Accounts</DialogTitle>
        <DialogContent>
          {isSyncing && <Typography variant="body2">Checking cloud provider...</Typography>}
          {!isSyncing && availableAccounts.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              No accounts found under this tenant.
            </Typography>
          )}
          {!isSyncing && availableAccounts.length > 0 && (
            <List dense>
              {availableAccounts.map((account) => (
                <ListItem key={account.external_id} disablePadding>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={selectedExternalIds.includes(account.external_id)}
                        disabled={account.already_added}
                        onChange={() => toggleSelectedAccount(account.external_id)}
                      />
                    }
                    label={
                      <ListItemText
                        primary={account.display_name}
                        secondary={account.external_id}
                      />
                    }
                  />
                  {account.already_added && (
                    <Chip label="already added" size="small" sx={{ ml: 1 }} />
                  )}
                </ListItem>
              ))}
            </List>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSyncDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleAddSelectedAccounts}
            disabled={isSyncing || isAddingSelected || selectedExternalIds.length === 0}
          >
            Add Selected
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add {SCOPE_TYPES_BY_PROVIDER[provider]}</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            label="External ID"
            placeholder={provider === "aws" ? "111122223333" : "subscription/project ID"}
            value={externalScopeId}
            onChange={(e) => setExternalScopeId(e.target.value)}
            fullWidth
            autoFocus
          />
          <TextField
            label="Display Name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleAddScope}
            disabled={isSubmitting || !externalScopeId || !displayName}
          >
            Add
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export function TenantsPage() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [provider, setProvider] = useState<CloudProvider>("aws");
  const [tenantName, setTenantName] = useState("");
  const [externalTenantId, setExternalTenantId] = useState("");
  const [authMode, setAuthMode] = useState<CloudAuthMode>("delegated");
  const [ssoLoginUrl, setSsoLoginUrl] = useState("");
  const [appRegistrationClientId, setAppRegistrationClientId] = useState("");
  const [appRegistrationTenantId, setAppRegistrationTenantId] = useState("");

  function reload() {
    listTenants()
      .then(setTenants)
      .catch(() => setError("Failed to load tenants."));
  }

  useEffect(reload, []);

  async function handleAddTenant() {
    setIsSubmitting(true);
    try {
      const payload: TenantCreatePayload = {
        provider,
        tenant_name: tenantName,
        external_tenant_id: externalTenantId,
        auth_mode: authMode,
        ...(authMode === "delegated" && {
          sso_login_url: ssoLoginUrl || null,
          app_registration_client_id: appRegistrationClientId || null,
          app_registration_tenant_id: appRegistrationTenantId || null,
        }),
      };
      await createTenant(payload);
      setDialogOpen(false);
      setTenantName("");
      setExternalTenantId("");
      setSsoLoginUrl("");
      setAppRegistrationClientId("");
      setAppRegistrationTenantId("");
      reload();
    } catch {
      setError("Failed to create tenant.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteTenant(tenantId: string) {
    try {
      await deleteTenant(tenantId);
      reload();
    } catch (err) {
      const message = axios.isAxiosError(err) ? err.response?.data?.detail : undefined;
      setError(typeof message === "string" ? message : "Failed to delete tenant.");
    }
  }

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 3 }}>
        <Typography variant="h4">Tenant Registry</Typography>
        <Button variant="contained" onClick={() => setDialogOpen(true)}>
          Add Tenant
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {tenants.length === 0 && (
        <Alert severity="info">
          No cloud tenants registered yet. Click "Add Tenant" to register your first AWS, Azure,
          GCP, or OCI tenant.
        </Alert>
      )}

      {tenants.map((tenant) => (
        <Accordion key={tenant.id}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2, flexGrow: 1 }}>
              <Chip label={tenant.provider.toUpperCase()} size="small" color="primary" />
              <Typography sx={{ flexGrow: 1 }}>{tenant.tenant_name}</Typography>
              <Chip
                label={tenant.auth_mode === "delegated" ? "Delegated (SSO)" : "App-only"}
                size="small"
                variant="outlined"
              />
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteTenant(tenant.id);
                }}
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              External Tenant ID: {tenant.external_tenant_id}
            </Typography>
            <Divider sx={{ mb: 2 }} />
            <TenantScopes tenantId={tenant.id} provider={tenant.provider} />
          </AccordionDetails>
        </Accordion>
      ))}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Cloud Tenant</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            select
            label="Cloud Provider"
            value={provider}
            onChange={(e) => setProvider(e.target.value as CloudProvider)}
            fullWidth
          >
            {PROVIDERS.map((p) => (
              <MenuItem key={p.value} value={p.value}>
                {p.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Tenant Name"
            placeholder="e.g. Acme Corp Production"
            value={tenantName}
            onChange={(e) => setTenantName(e.target.value)}
            fullWidth
            autoFocus
          />
          <TextField
            label="External Tenant ID"
            placeholder={
              provider === "aws"
                ? "AWS Organization ID or root account ID"
                : provider === "azure"
                  ? "Entra Tenant ID (GUID)"
                  : provider === "gcp"
                    ? "GCP Organization ID"
                    : "OCI Tenancy OCID"
            }
            value={externalTenantId}
            onChange={(e) => setExternalTenantId(e.target.value)}
            fullWidth
          />
          <TextField
            select
            label="Cloud Auth Mode"
            value={authMode}
            onChange={(e) => setAuthMode(e.target.value as CloudAuthMode)}
            helperText={AUTH_MODES.find((m) => m.value === authMode)?.description}
            fullWidth
          >
            {AUTH_MODES.map((m) => (
              <MenuItem key={m.value} value={m.value}>
                {m.label}
              </MenuItem>
            ))}
          </TextField>

          {authMode === "delegated" && (
            <>
              <Divider />
              <Typography variant="subtitle2">SSO Sign-In Details</Typography>
              <Typography variant="body2" color="text.secondary">
                Used to authenticate this specific tenant via a popup SSO login for account sync
                and audit jobs — separate from your NAVIXA login.
              </Typography>
              <TextField
                label={provider === "aws" ? "IAM Identity Center Start URL" : "SSO Login URL"}
                placeholder={
                  provider === "aws"
                    ? "https://d-xxxxxxxxxx.awsapps.com/start"
                    : "https://login.microsoftonline.com/..."
                }
                value={ssoLoginUrl}
                onChange={(e) => setSsoLoginUrl(e.target.value)}
                fullWidth
              />
              {provider === "azure" && (
                <>
                  <TextField
                    label="App Registration Client ID (optional)"
                    helperText="Leave blank to use NAVIXA's shared app registration"
                    value={appRegistrationClientId}
                    onChange={(e) => setAppRegistrationClientId(e.target.value)}
                    fullWidth
                  />
                  <TextField
                    label="Entra Tenant ID for this app registration (optional)"
                    helperText="Defaults to the External Tenant ID above"
                    value={appRegistrationTenantId}
                    onChange={(e) => setAppRegistrationTenantId(e.target.value)}
                    fullWidth
                  />
                </>
              )}
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleAddTenant}
            disabled={isSubmitting || !tenantName || !externalTenantId}
          >
            Add Tenant
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
