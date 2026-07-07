import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Drawer,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import VisibilityIcon from "@mui/icons-material/Visibility";
import CloseIcon from "@mui/icons-material/Close";
import { exportDiscoveredResources, getDiscoveredResources } from "../api/reports";
import { listScopes, listTenants } from "../api/tenants";
import type { CloudProvider, DiscoveredResource, Scope, Tenant } from "../api/types";

const PROVIDERS: { value: CloudProvider; label: string }[] = [
  { value: "aws", label: "AWS" },
  { value: "azure", label: "Azure" },
  { value: "gcp", label: "GCP" },
  { value: "oci", label: "OCI" },
];

const RESOURCE_TYPES = [
  "network",
  "subnet",
  "route_table",
  "route",
  "gateway",
  "firewall",
  "security_group",
  "network_interface",
  "load_balancer",
  "endpoint",
  "compute_instance",
  "peering_connection",
  "public_ip",
];

export function ReportsPage() {
  const [provider, setProvider] = useState<CloudProvider>("aws");
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<string>("");
  const [scopes, setScopes] = useState<Scope[]>([]);
  const [selectedScopeId, setSelectedScopeId] = useState<string>("");
  const [resourceType, setResourceType] = useState<string>("");

  const [resources, setResources] = useState<DiscoveredResource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [detailResource, setDetailResource] = useState<DiscoveredResource | null>(null);

  // Switching providers resets the tenant/scope filters - a subscription
  // picked under Azure has no meaning once the tab moves to AWS.
  useEffect(() => {
    setSelectedTenantId("");
    setSelectedScopeId("");
    listTenants(provider).then(setTenants).catch(() => setTenants([]));
  }, [provider]);

  useEffect(() => {
    setSelectedScopeId("");
    if (!selectedTenantId) {
      setScopes([]);
      return;
    }
    listScopes(selectedTenantId).then(setScopes).catch(() => setScopes([]));
  }, [selectedTenantId]);

  const filters = useMemo(
    () => ({
      provider,
      tenant_id: selectedTenantId || undefined,
      scope_id: selectedScopeId || undefined,
      resource_type: resourceType || undefined,
    }),
    [provider, selectedTenantId, selectedScopeId, resourceType],
  );

  useEffect(() => {
    setIsLoading(true);
    getDiscoveredResources(filters)
      .then((data) => {
        setResources(data);
        setError(null);
      })
      .catch(() => setError("Failed to load discovered resources."))
      .finally(() => setIsLoading(false));
  }, [filters]);

  async function handleExport() {
    setIsExporting(true);
    try {
      await exportDiscoveredResources(filters);
    } catch {
      setError("Failed to export discovered resources.");
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Reports
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Browse NAVIXA Discover's current inventory across every tenant, filter by tenant/subscription,
        and export the result.
      </Typography>

      <Tabs
        value={provider}
        onChange={(_e, value: CloudProvider) => setProvider(value)}
        sx={{ mb: 2, borderBottom: 1, borderColor: "divider" }}
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

      <Stack direction="row" spacing={2} sx={{ mb: 2, flexWrap: "wrap", alignItems: "center" }}>
        <TextField
          select
          label="Tenant"
          value={selectedTenantId}
          onChange={(e) => setSelectedTenantId(e.target.value)}
          size="small"
          sx={{ minWidth: 220 }}
        >
          <MenuItem value="">All tenants</MenuItem>
          {tenants.map((t) => (
            <MenuItem key={t.id} value={t.id}>
              {t.tenant_name}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Subscription / Account"
          value={selectedScopeId}
          onChange={(e) => setSelectedScopeId(e.target.value)}
          size="small"
          sx={{ minWidth: 220 }}
          disabled={!selectedTenantId}
        >
          <MenuItem value="">All scopes</MenuItem>
          {scopes.map((s) => (
            <MenuItem key={s.id} value={s.id}>
              {s.display_name}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Resource Type"
          value={resourceType}
          onChange={(e) => setResourceType(e.target.value)}
          size="small"
          sx={{ minWidth: 200 }}
        >
          <MenuItem value="">All types</MenuItem>
          {RESOURCE_TYPES.map((t) => (
            <MenuItem key={t} value={t}>
              {t}
            </MenuItem>
          ))}
        </TextField>
        <Box sx={{ flexGrow: 1 }} />
        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={handleExport}
          disabled={isExporting || resources.length === 0}
        >
          {isExporting ? "Exporting..." : "Export CSV"}
        </Button>
      </Stack>

      {isLoading && (
        <Stack direction="row" spacing={2} sx={{ alignItems: "center", py: 2 }}>
          <CircularProgress size={24} />
          <Typography>Loading discovered resources...</Typography>
        </Stack>
      )}

      {!isLoading && resources.length === 0 && (
        <Alert severity="info">
          No discovered resources match these filters yet. Run an audit job under NAVIXA Discover,
          or widen the filters above.
        </Alert>
      )}

      {!isLoading && resources.length > 0 && (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Type</TableCell>
                <TableCell>Name / Native ID</TableCell>
                <TableCell>Tenant</TableCell>
                <TableCell>Subscription / Account</TableCell>
                <TableCell>Collected</TableCell>
                <TableCell align="right">Detail</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {resources.map((resource) => (
                <TableRow key={resource.id} hover>
                  <TableCell>
                    <Chip label={resource.resource_type} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>{resource.name || resource.native_id}</TableCell>
                  <TableCell>{resource.tenant_name}</TableCell>
                  <TableCell>{resource.scope_display_name}</TableCell>
                  <TableCell>{new Date(resource.collected_at).toLocaleString()}</TableCell>
                  <TableCell align="right">
                    <IconButton size="small" onClick={() => setDetailResource(resource)}>
                      <VisibilityIcon fontSize="small" />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Drawer anchor="right" open={Boolean(detailResource)} onClose={() => setDetailResource(null)}>
        <Box sx={{ width: 480, p: 3 }}>
          <Stack direction="row" sx={{ alignItems: "center", justifyContent: "space-between", mb: 2 }}>
            <Typography variant="h6">Resource Detail</Typography>
            <IconButton size="small" onClick={() => setDetailResource(null)}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Stack>
          {detailResource && (
            <Stack spacing={1.5}>
              <DetailField label="Type" value={detailResource.resource_type} />
              <DetailField label="Name" value={detailResource.name || "-"} />
              <DetailField label="Native ID" value={detailResource.native_id} />
              <DetailField label="Provider" value={detailResource.provider} />
              <DetailField label="Tenant" value={detailResource.tenant_name} />
              <DetailField
                label="Subscription / Account"
                value={`${detailResource.scope_display_name} (${detailResource.scope_type})`}
              />
              <DetailField
                label="Collected"
                value={new Date(detailResource.collected_at).toLocaleString()}
              />
              <Typography variant="subtitle2" sx={{ mt: 1 }}>
                Raw attributes
              </Typography>
              <Box
                component="pre"
                sx={{
                  backgroundColor: "background.default",
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 1,
                  p: 1.5,
                  fontSize: 12,
                  overflow: "auto",
                  maxHeight: "50vh",
                }}
              >
                {JSON.stringify(detailResource.attributes, null, 2)}
              </Box>
            </Stack>
          )}
        </Box>
      </Drawer>
    </Box>
  );
}

function DetailField({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body2">{value}</Typography>
    </Box>
  );
}
