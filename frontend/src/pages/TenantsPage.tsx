import { useEffect, useState } from "react";
import axios from "axios";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Grid,
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
import DeleteIcon from "@mui/icons-material/Delete";
import SyncIcon from "@mui/icons-material/Sync";
import BusinessOutlinedIcon from "@mui/icons-material/BusinessOutlined";
import LayersOutlinedIcon from "@mui/icons-material/LayersOutlined";
import DomainDisabledOutlinedIcon from "@mui/icons-material/DomainDisabledOutlined";
import CloudQueueIcon from "@mui/icons-material/CloudQueue";
import LayersIcon from "@mui/icons-material/Layers";
import { useAuth } from "../auth/AuthContext";
import { useEnvironment } from "../auth/EnvironmentContext";
import {
  createScope,
  createTenant,
  deleteTenant,
  getAvailableAccounts,
  getAvailableTenants,
  importTenants,
  listConnections,
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
  EnvironmentConnection,
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

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <Paper variant="outlined" sx={{ p: 2.5, display: "flex", alignItems: "center", gap: 2 }}>
      <Box
        sx={{
          width: 44,
          height: 44,
          borderRadius: 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "rgba(11, 61, 145, 0.08)",
          color: "primary.main",
          flexShrink: 0,
        }}
      >
        {icon}
      </Box>
      <Box>
        <Typography variant="h5">{value}</Typography>
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
      </Box>
    </Paper>
  );
}

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
    <Box>
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

function TenantListItem({
  tenant,
  selected,
  isAdmin,
  onSelect,
  onDelete,
}: {
  tenant: Tenant;
  selected: boolean;
  isAdmin: boolean;
  onSelect: () => void;
  onDelete: (tenantId: string) => void;
}) {
  return (
    <Paper
      variant="outlined"
      onClick={onSelect}
      sx={{
        p: 1.75,
        mb: 1.25,
        cursor: "pointer",
        borderColor: selected ? "primary.main" : "divider",
        borderWidth: selected ? 2 : 1,
        bgcolor: selected ? "rgba(11, 61, 145, 0.04)" : "background.paper",
      }}
    >
      <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
        <Box
          sx={{
            width: 36,
            height: 36,
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
        <Box sx={{ minWidth: 0, flexGrow: 1 }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }} noWrap>
            {tenant.tenant_name}
          </Typography>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ fontFamily: "monospace", display: "block" }}
            noWrap
          >
            {tenant.external_tenant_id}
          </Typography>
        </Box>
        {isAdmin && (
          <IconButton
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(tenant.id);
            }}
          >
            <DeleteIcon fontSize="small" />
          </IconButton>
        )}
      </Stack>
      <Chip
        label={tenant.auth_mode === "delegated" ? "Delegated (SSO)" : "App-only"}
        size="small"
        variant="outlined"
        sx={{ mt: 1 }}
      />
    </Paper>
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
  const [connections, setConnections] = useState<EnvironmentConnection[]>([]);
  const [connectionId, setConnectionId] = useState<string>("");
  const [availableTenants, setAvailableTenants] = useState<AvailableTenant[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isLoadingConnections, setIsLoadingConnections] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needsConnection, setNeedsConnection] = useState(false);

  useEffect(() => {
    if (!open) return;
    setConnectionId("");
    setAvailableTenants([]);
    setError(null);
    setNeedsConnection(false);
    setIsLoadingConnections(true);
    listConnections(environment)
      .then((all) => {
        const azureConnections = all.filter((c) => c.provider === "azure");
        setConnections(azureConnections);
        if (azureConnections.length === 1) setConnectionId(azureConnections[0].id);
      })
      .catch(() => setError("Failed to load Azure connections."))
      .finally(() => setIsLoadingConnections(false));
  }, [open, environment]);

  useEffect(() => {
    if (!open || !connectionId) return;
    setIsLoading(true);
    setError(null);
    setNeedsConnection(false);
    getAvailableTenants(environment, connectionId)
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
  }, [open, environment, connectionId]);

  function toggle(tenantId: string) {
    setSelectedIds((prev) =>
      prev.includes(tenantId) ? prev.filter((id) => id !== tenantId) : [...prev, tenantId],
    );
  }

  async function handleImport() {
    if (!connectionId) return;
    setIsImporting(true);
    try {
      await importTenants(environment, connectionId, selectedIds);
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
      <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {!isLoadingConnections && connections.length === 0 && (
          <Alert severity="warning">
            No Azure connections yet for the {environment} environment. Add one on the{" "}
            <strong>Connections</strong> page first, then try again.
          </Alert>
        )}
        {connections.length > 0 && (
          <TextField
            select
            label="Connection"
            value={connectionId}
            onChange={(e) => setConnectionId(e.target.value)}
            fullWidth
            helperText="Which signed-in Azure account to discover tenants from."
          >
            {connections.map((c) => (
              <MenuItem key={c.id} value={c.id}>
                {c.name}
              </MenuItem>
            ))}
          </TextField>
        )}
        {needsConnection && (
          <Alert severity="warning">
            Connect this Azure connection from the <strong>Connections</strong> page first (Azure
            sign-in requires a device code, shown there), then try again.
          </Alert>
        )}
        {error && <Alert severity="error">{error}</Alert>}
        {connectionId && !needsConnection && !error && isLoading && (
          <Typography variant="body2">Loading tenants visible to this connection...</Typography>
        )}
        {connectionId && !needsConnection && !error && !isLoading && availableTenants.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            No Azure AD tenants found for this connection.
          </Typography>
        )}
        {connectionId && !needsConnection && !error && !isLoading && availableTenants.length > 0 && (
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
        {connectionId && !needsConnection && (
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
  const [scopeCount, setScopeCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [manualDialogOpen, setManualDialogOpen] = useState(false);
  const [azureDialogOpen, setAzureDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [tenantName, setTenantName] = useState("");
  const [externalTenantId, setExternalTenantId] = useState("");
  const [region, setRegion] = useState("");
  const [authMode, setAuthMode] = useState<CloudAuthMode>("delegated");
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null);

  function reload() {
    listTenants(activeProvider, environment)
      .then((data) => {
        setTenants(data);
        setSelectedTenantId((current) =>
          data.some((t) => t.id === current) ? current : (data[0]?.id ?? null),
        );
        Promise.all(data.map((t) => listScopes(t.id)))
          .then((results) => setScopeCount(results.reduce((sum, s) => sum + s.length, 0)))
          .catch(() => setScopeCount(0));
      })
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
  const selectedTenant = tenants.find((t) => t.id === selectedTenantId) ?? null;

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

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 6 }}>
          <StatCard
            icon={<BusinessOutlinedIcon />}
            label={`${activeProviderLabel} Tenants (${environment})`}
            value={tenants.length}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6 }}>
          <StatCard icon={<LayersIcon />} label="Subscriptions / Accounts" value={scopeCount} />
        </Grid>
      </Grid>

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

        {error && (
          <Alert severity="error" sx={{ m: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Grid container sx={{ minHeight: 360 }}>
          <Grid
            size={{ xs: 12, md: 4 }}
            sx={{ p: 2, borderRight: { md: "1px solid" }, borderColor: { md: "divider" } }}
          >
            {tenants.length === 0 ? (
              <Stack spacing={1.5} sx={{ alignItems: "center", py: 6, px: 2 }}>
                <DomainDisabledOutlinedIcon sx={{ fontSize: 36, color: "text.disabled" }} />
                <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center" }}>
                  No {activeProviderLabel} tenants registered for the {environment} environment
                  yet.
                </Typography>
                {isAdmin && (
                  <Button variant="outlined" size="small" onClick={handleAddClick}>
                    Add {activeProviderLabel} Tenant
                  </Button>
                )}
              </Stack>
            ) : (
              tenants.map((tenant) => (
                <TenantListItem
                  key={tenant.id}
                  tenant={tenant}
                  selected={tenant.id === selectedTenantId}
                  isAdmin={isAdmin}
                  onSelect={() => setSelectedTenantId(tenant.id)}
                  onDelete={handleDeleteTenant}
                />
              ))
            )}
          </Grid>
          <Grid size={{ xs: 12, md: 8 }} sx={{ p: 3 }}>
            {selectedTenant ? (
              <>
                <Typography variant="h6" gutterBottom>
                  {selectedTenant.tenant_name}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ fontFamily: "monospace", mb: 2 }}
                >
                  {selectedTenant.external_tenant_id}
                </Typography>
                <TenantScopesRows
                  tenantId={selectedTenant.id}
                  provider={selectedTenant.provider}
                  isAdmin={isAdmin}
                />
              </>
            ) : (
              <Typography variant="body2" color="text.secondary">
                {tenants.length === 0
                  ? "Add a tenant to get started."
                  : "Select a tenant to view its subscriptions/accounts."}
              </Typography>
            )}
          </Grid>
        </Grid>
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
