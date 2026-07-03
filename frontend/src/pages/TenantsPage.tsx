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
  Stack,
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
import BusinessOutlinedIcon from "@mui/icons-material/BusinessOutlined";
import LayersOutlinedIcon from "@mui/icons-material/LayersOutlined";
import DomainDisabledOutlinedIcon from "@mui/icons-material/DomainDisabledOutlined";
import CloudQueueIcon from "@mui/icons-material/CloudQueue";
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

  const scopeLabel = SCOPE_TYPES_BY_PROVIDER[provider];
  const scopeLabelCap = scopeLabel.charAt(0).toUpperCase() + scopeLabel.slice(1);

  return (
    <Box
      sx={{
        py: 2.5,
        px: 3,
        ml: { xs: 0, sm: 6 },
        mr: 2,
        mb: 2,
        bgcolor: "background.default",
        borderRadius: 2,
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 1.5 }}>
        <LayersOutlinedIcon fontSize="small" color="action" />
        <Typography variant="subtitle2">{scopeLabelCap}s</Typography>
        <Chip label={scopes.length} size="small" sx={{ height: 20, fontSize: "0.7rem" }} />
      </Stack>
      {scopes.length > 0 ? (
        <TableContainer component={Paper} variant="outlined" sx={{ mb: 1.5 }}>
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
                  <TableCell sx={{ fontFamily: "monospace", fontSize: "0.8rem" }}>
                    {scope.external_scope_id}
                  </TableCell>
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
        </TableContainer>
      ) : (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          No {scopeLabel}s added yet.
        </Typography>
      )}
      {isAdmin && (
        <Stack direction="row" spacing={1}>
          <Button size="small" onClick={() => setDialogOpen(true)}>
            Add {scopeLabel}
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
        </Stack>
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
        <DialogTitle>Add {scopeLabel}</DialogTitle>
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
      <TableRow
        hover
        onClick={() => setExpanded((v) => !v)}
        sx={{ cursor: "pointer", bgcolor: expanded ? "action.selected" : undefined }}
      >
        <TableCell width={48}>
          <IconButton size="small">
            {expanded ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
          </IconButton>
        </TableCell>
        <TableCell>
          <Stack direction="row" spacing={1.25} sx={{ alignItems: "center" }}>
            <Box
              sx={{
                width: 32,
                height: 32,
                borderRadius: 1.5,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                bgcolor: "rgba(11, 61, 145, 0.08)",
                color: "primary.main",
                flexShrink: 0,
              }}
            >
              <BusinessOutlinedIcon fontSize="small" />
            </Box>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              {tenant.tenant_name}
            </Typography>
          </Stack>
        </TableCell>
        <TableCell sx={{ fontFamily: "monospace", fontSize: "0.8rem", color: "text.secondary" }}>
          {tenant.external_tenant_id}
        </TableCell>
        <TableCell>
          <Chip
            label={tenant.auth_mode === "delegated" ? "Delegated (SSO)" : "App-only"}
            size="small"
            variant="outlined"
          />
        </TableCell>
        <TableCell align="right" onClick={(e) => e.stopPropagation()}>
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

  const activeProviderLabel = PROVIDERS.find((p) => p.value === activeProvider)?.label;

  return (
    <Box>
      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "flex-start", mb: 3 }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            Tenant Registry
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Cloud tenants and their subscriptions/accounts, grouped by provider for the{" "}
            <strong>{environment}</strong> environment.
          </Typography>
        </Box>
        {isAdmin && (
          <Button variant="contained" onClick={handleAddClick} sx={{ flexShrink: 0 }}>
            Add Tenant
          </Button>
        )}
      </Stack>

      <Paper variant="outlined" sx={{ mb: 3 }}>
        <Tabs
          value={activeProvider}
          onChange={(_e, value: CloudProvider) => setActiveProvider(value)}
          sx={{ px: 1, borderBottom: "1px solid", borderColor: "divider" }}
        >
          {PROVIDERS.map((p) => (
            <Tab key={p.value} value={p.value} label={p.label} icon={<CloudQueueIcon fontSize="small" />} iconPosition="start" sx={{ minHeight: 48 }} />
          ))}
        </Tabs>

        <Box sx={{ p: tenants.length === 0 ? 0 : 2 }}>
          {error && (
            <Alert severity="error" sx={{ m: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {tenants.length === 0 ? (
            <Stack spacing={1.5} sx={{ alignItems: "center", py: 8, px: 3 }}>
              <DomainDisabledOutlinedIcon sx={{ fontSize: 40, color: "text.disabled" }} />
              <Typography variant="body1" color="text.secondary" sx={{ textAlign: "center" }}>
                No {activeProviderLabel} tenants registered for the {environment} environment yet.
              </Typography>
              {isAdmin && (
                <Button variant="outlined" size="small" onClick={handleAddClick}>
                  Add {activeProviderLabel} Tenant
                </Button>
              )}
            </Stack>
          ) : (
            <TableContainer>
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
        </Box>
      </Paper>

      <AzureImportDialog
        open={azureDialogOpen}
        environment={environment}
        onClose={() => setAzureDialogOpen(false)}
        onImported={reload}
      />

      <Dialog open={manualDialogOpen} onClose={() => setManualDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add {activeProviderLabel} Tenant</DialogTitle>
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
