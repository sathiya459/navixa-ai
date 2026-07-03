import { useEffect, useState } from "react";
import axios from "axios";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Tab,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import DeleteIcon from "@mui/icons-material/Delete";
import SyncIcon from "@mui/icons-material/Sync";
import { useAuth } from "../auth/AuthContext";
import { useEnvironment } from "../auth/EnvironmentContext";
import {
  createScope,
  createTenant,
  deleteTenant,
  getAvailableAccounts,
  getAvailableTenants,
  importTenants,
  listScopes,
  listTenants,
  type ScopeCreatePayload,
  type TenantCreatePayload,
} from "../api/tenants";
import type {
  AvailableAccount,
  AvailableTenant,
  CloudAuthMode,
  CloudProvider,
  Scope,
  ScopeType,
  Tenant,
} from "../api/types";

const PROVIDERS: { value: CloudProvider; label: string }[] = [
  { value: "azure", label: "Azure" },
  { value: "aws", label: "AWS" },
  { value: "gcp", label: "GCP" },
  { value: "oci", label: "OCI" },
];

const ACCOUNT_SYNC_SUPPORTED: Record<CloudProvider, boolean> = {
  aws: true,
  azure: true,
  gcp: false,
  oci: false,
};

const SCOPE_TYPES_BY_PROVIDER: Record<CloudProvider, ScopeType> = {
  aws: "account",
  azure: "subscription",
  gcp: "project",
  oci: "compartment",
};

const AUTH_MODES: { value: CloudAuthMode; label: string; description: string }[] = [
  {
    value: "delegated",
    label: "Delegated (SSO)",
    description: "Uses the environment's shared root-credential SSO connection",
  },
  { value: "app_only", label: "App-only", description: "Uses a registered app / service account (headless)" },
];

function TenantScopesRows({
  tenantId,
  provider,
  isAdmin,
}: {
  tenantId: string;
  provider: CloudProvider;
  isAdmin: boolean;
}) {
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
    <Box sx={{ py: 2, px: 4, bgcolor: "action.hover" }}>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        {SCOPE_TYPES_BY_PROVIDER[provider].charAt(0).toUpperCase() +
          SCOPE_TYPES_BY_PROVIDER[provider].slice(1)}
        s
      </Typography>
      {scopes.length > 0 ? (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>External ID</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {scopes.map((scope) => (
              <TableRow key={scope.id}>
                <TableCell>{scope.display_name}</TableCell>
                <TableCell>{scope.external_scope_id}</TableCell>
                <TableCell>
                  <Chip
                    label={scope.is_active ? "active" : "inactive"}
                    size="small"
                    color={scope.is_active ? "success" : "default"}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <Typography variant="body2" color="text.secondary">
          No {SCOPE_TYPES_BY_PROVIDER[provider]}s added yet.
        </Typography>
      )}
      {isAdmin && (
        <Box sx={{ display: "flex", gap: 1, mt: 1.5 }}>
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
      )}

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

function TenantRow({
  tenant,
  isAdmin,
  onDelete,
}: {
  tenant: Tenant;
  isAdmin: boolean;
  onDelete: (tenantId: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <TableRow hover>
        <TableCell width={48}>
          <IconButton size="small" onClick={() => setExpanded((v) => !v)}>
            {expanded ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell>{tenant.tenant_name}</TableCell>
        <TableCell>{tenant.external_tenant_id}</TableCell>
        <TableCell>
          <Chip
            label={tenant.auth_mode === "delegated" ? "Delegated (SSO)" : "App-only"}
            size="small"
            variant="outlined"
          />
        </TableCell>
        <TableCell align="right">
          {isAdmin && (
            <IconButton size="small" onClick={() => onDelete(tenant.id)}>
              <DeleteIcon fontSize="small" />
            </IconButton>
          )}
        </TableCell>
      </TableRow>
      <TableRow>
        <TableCell colSpan={5} sx={{ p: 0, borderBottom: expanded ? undefined : "none" }}>
          <Collapse in={expanded} timeout="auto" unmountOnExit>
            <TenantScopesRows tenantId={tenant.id} provider={tenant.provider} isAdmin={isAdmin} />
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
}

function AzureImportDialog({
  open,
  environment,
  onClose,
  onImported,
}: {
  open: boolean;
  environment: "dev" | "prod";
  onClose: () => void;
  onImported: () => void;
}) {
  const [availableTenants, setAvailableTenants] = useState<AvailableTenant[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needsConnection, setNeedsConnection] = useState(false);

  useEffect(() => {
    if (!open) return;
    setIsLoading(true);
    setError(null);
    setNeedsConnection(false);
    getAvailableTenants(environment)
      .then((tenants) => {
        setAvailableTenants(tenants);
        setSelectedIds(tenants.filter((t) => !t.already_added).map((t) => t.tenant_id));
      })
      .catch((err) => {
        const detail = axios.isAxiosError(err) ? err.response?.data?.detail : undefined;
        if (detail?.code === "delegated_auth_required") {
          setNeedsConnection(true);
        } else {
          setError("Failed to load available tenants.");
        }
      })
      .finally(() => setIsLoading(false));
  }, [open, environment]);

  function toggle(tenantId: string) {
    setSelectedIds((prev) =>
      prev.includes(tenantId) ? prev.filter((id) => id !== tenantId) : [...prev, tenantId],
    );
  }

  async function handleImport() {
    setIsImporting(true);
    try {
      await importTenants(environment, selectedIds);
      onImported();
      onClose();
    } catch {
      setError("Failed to import selected tenant(s).");
    } finally {
      setIsImporting(false);
    }
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add Azure Tenant</DialogTitle>
      <DialogContent>
        {needsConnection && (
          <Alert severity="warning">
            Connect the {environment} environment's Azure account from the{" "}
            <strong>Connections</strong> page first (Azure sign-in requires a device code, shown
            there), then try again.
          </Alert>
        )}
        {error && <Alert severity="error">{error}</Alert>}
        {!needsConnection && !error && isLoading && (
          <Typography variant="body2">Loading tenants visible to this connection...</Typography>
        )}
        {!needsConnection && !error && !isLoading && availableTenants.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            No Azure AD tenants found for this connection.
          </Typography>
        )}
        {!needsConnection && !error && !isLoading && availableTenants.length > 0 && (
          <List dense>
            {availableTenants.map((tenant) => (
              <ListItem key={tenant.tenant_id} disablePadding>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={selectedIds.includes(tenant.tenant_id)}
                      disabled={tenant.already_added}
                      onChange={() => toggle(tenant.tenant_id)}
                    />
                  }
                  label={
                    <ListItemText primary={tenant.display_name} secondary={tenant.tenant_id} />
                  }
                />
                {tenant.already_added && (
                  <Chip label="already added" size="small" sx={{ ml: 1 }} />
                )}
              </ListItem>
            ))}
          </List>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        {!needsConnection && (
          <Button
            variant="contained"
            onClick={handleImport}
            disabled={isLoading || isImporting || selectedIds.length === 0}
          >
            Add Selected
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}

export function TenantsPage() {
  const { user } = useAuth();
  const { environment } = useEnvironment();
  const isAdmin = Boolean(user?.roles.includes("admin"));

  const [activeProvider, setActiveProvider] = useState<CloudProvider>("azure");
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [manualDialogOpen, setManualDialogOpen] = useState(false);
  const [azureDialogOpen, setAzureDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [tenantName, setTenantName] = useState("");
  const [externalTenantId, setExternalTenantId] = useState("");
  const [region, setRegion] = useState("");
  const [authMode, setAuthMode] = useState<CloudAuthMode>("delegated");

  function reload() {
    listTenants(activeProvider, environment)
      .then(setTenants)
      .catch(() => setError("Failed to load tenants."));
  }

  useEffect(reload, [activeProvider, environment]);

  async function handleAddTenant() {
    setIsSubmitting(true);
    try {
      const payload: TenantCreatePayload = {
        provider: activeProvider,
        environment,
        tenant_name: tenantName,
        external_tenant_id: externalTenantId,
        auth_mode: authMode,
        region_info: region ? { default_region: region } : null,
      };
      await createTenant(payload);
      setManualDialogOpen(false);
      setTenantName("");
      setExternalTenantId("");
      setRegion("");
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

  function handleAddClick() {
    if (activeProvider === "azure") {
      setAzureDialogOpen(true);
    } else {
      setManualDialogOpen(true);
    }
  }

  return (
    <Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
        <Typography variant="h4">Tenant Registry</Typography>
        {isAdmin && (
          <Button variant="contained" onClick={handleAddClick}>
            Add Tenant
          </Button>
        )}
      </Box>

      <Tabs
        value={activeProvider}
        onChange={(_e, value: CloudProvider) => setActiveProvider(value)}
        sx={{ mb: 2 }}
      >
        {PROVIDERS.map((p) => (
          <Tab key={p.value} value={p.value} label={p.label} />
        ))}
      </Tabs>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {tenants.length === 0 ? (
        <Alert severity="info">
          No {PROVIDERS.find((p) => p.value === activeProvider)?.label} tenants registered for the{" "}
          {environment} environment yet.
        </Alert>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table>
            <TableHead>
              <TableRow>
                <TableCell width={48} />
                <TableCell>Tenant Name</TableCell>
                <TableCell>External Tenant ID</TableCell>
                <TableCell>Auth Mode</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {tenants.map((tenant) => (
                <TenantRow
                  key={tenant.id}
                  tenant={tenant}
                  isAdmin={isAdmin}
                  onDelete={handleDeleteTenant}
                />
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <AzureImportDialog
        open={azureDialogOpen}
        environment={environment}
        onClose={() => setAzureDialogOpen(false)}
        onImported={reload}
      />

      <Dialog open={manualDialogOpen} onClose={() => setManualDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add {PROVIDERS.find((p) => p.value === activeProvider)?.label} Tenant</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
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
              activeProvider === "aws"
                ? "AWS Organization ID or root account ID"
                : activeProvider === "gcp"
                  ? "GCP Organization ID"
                  : "OCI Tenancy OCID"
            }
            value={externalTenantId}
            onChange={(e) => setExternalTenantId(e.target.value)}
            fullWidth
          />
          <TextField
            label="Default Region"
            placeholder={activeProvider === "aws" ? "ap-south-1" : "us-ashburn-1"}
            value={region}
            onChange={(e) => setRegion(e.target.value)}
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
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setManualDialogOpen(false)}>Cancel</Button>
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
