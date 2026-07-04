import { useEffect, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  Link,
  List,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import DeleteIcon from "@mui/icons-material/Delete";
import { useEnvironment } from "../auth/EnvironmentContext";
import {
  createConnection,
  deleteConnection,
  listConnections,
  pollDeviceFlow,
  startDeviceFlow,
  updateConnectionConfig,
  type DeviceFlowStart,
} from "../api/tenants";
import type { CloudProvider, EnvironmentConnection } from "../api/types";

const CONNECTABLE: Record<CloudProvider, boolean> = {
  aws: true,
  azure: true,
  gcp: false,
  oci: false,
};

// Azure always signs in via a device code + standard Microsoft login using
// Azure CLI's own well-known client - no login URL/region needed. Only
// AWS's IAM Identity Center requires the customer's own start URL and
// region before "Connect" can work.
const REQUIRES_CONFIG: Record<CloudProvider, boolean> = {
  aws: true,
  azure: false,
  gcp: false,
  oci: false,
};

const PROVIDERS: CloudProvider[] = ["aws", "azure", "gcp", "oci"];

const PROVIDER_LABELS: Record<CloudProvider, string> = {
  aws: "AWS",
  azure: "Azure",
  gcp: "GCP",
  oci: "OCI",
};

export function ConnectionsPage() {
  const { environment } = useEnvironment();
  const [connections, setConnections] = useState<EnvironmentConnection[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [addingProvider, setAddingProvider] = useState<CloudProvider | null>(null);
  const [newName, setNewName] = useState("");
  const [newSsoLoginUrl, setNewSsoLoginUrl] = useState("");
  const [newRegion, setNewRegion] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const [editing, setEditing] = useState<EnvironmentConnection | null>(null);
  const [ssoLoginUrl, setSsoLoginUrl] = useState("");
  const [region, setRegion] = useState("");

  const [deviceFlow, setDeviceFlow] = useState<DeviceFlowStart | null>(null);
  const [deviceFlowConnectionId, setDeviceFlowConnectionId] = useState<string | null>(null);
  const [deviceFlowMessage, setDeviceFlowMessage] = useState<string | null>(null);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  function reload() {
    listConnections(environment)
      .then(setConnections)
      .catch(() => setError("Failed to load connections."));
  }

  useEffect(reload, [environment]);

  useEffect(() => {
    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
    };
  }, []);

  function openAdd(provider: CloudProvider) {
    setAddingProvider(provider);
    setNewName("");
    setNewSsoLoginUrl("");
    setNewRegion("");
  }

  async function handleCreateConnection() {
    if (!addingProvider || !newName.trim()) return;
    setIsSaving(true);
    try {
      const connection = await createConnection(environment, addingProvider, newName.trim());
      if (REQUIRES_CONFIG[addingProvider]) {
        await updateConnectionConfig(environment, connection.id, {
          sso_login_url: newSsoLoginUrl || null,
          region: newRegion || null,
        });
      }
      setAddingProvider(null);
      reload();
    } catch {
      setError("Failed to create connection. The name may already be in use for this provider.");
    } finally {
      setIsSaving(false);
    }
  }

  function openEdit(connection: EnvironmentConnection) {
    setEditing(connection);
    setSsoLoginUrl(connection.sso_login_url ?? "");
    setRegion(connection.region ?? "");
  }

  async function handleSaveConfig() {
    if (!editing) return;
    setIsSaving(true);
    try {
      await updateConnectionConfig(environment, editing.id, {
        sso_login_url: ssoLoginUrl || null,
        region: region || null,
      });
      setEditing(null);
      reload();
    } catch {
      setError("Failed to save connection settings.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete(connection: EnvironmentConnection) {
    if (!window.confirm(`Remove the "${connection.name}" connection? Tenants imported through it will keep their data but lose sync access until reconnected.`)) {
      return;
    }
    try {
      await deleteConnection(environment, connection.id);
      reload();
    } catch {
      setError("Failed to delete connection.");
    }
  }

  function stopPolling() {
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
  }

  function handleCancelDeviceFlow() {
    stopPolling();
    setDeviceFlow(null);
    setDeviceFlowConnectionId(null);
    setDeviceFlowMessage(null);
  }

  async function handleConnect(connection: EnvironmentConnection) {
    setError(null);
    setDeviceFlowMessage(null);
    if (connection.provider === "aws" && !connection.sso_login_url) {
      setError("Set this connection's IAM Identity Center start URL first (use Configure).");
      return;
    }
    try {
      const flow = await startDeviceFlow(environment, connection.id, connection.provider as "aws" | "azure");
      setDeviceFlow(flow);
      setDeviceFlowConnectionId(connection.id);

      pollTimer.current = setInterval(async () => {
        try {
          const result = await pollDeviceFlow(
            environment,
            connection.id,
            connection.provider as "aws" | "azure",
            flow.flow_id,
          );
          if (result.status === "complete") {
            stopPolling();
            setDeviceFlow(null);
            setDeviceFlowConnectionId(null);
            reload();
          } else if (result.status === "error" || result.status === "expired") {
            stopPolling();
            setDeviceFlowMessage(result.message || "Sign-in failed or expired. Please try again.");
          }
        } catch {
          stopPolling();
          setDeviceFlowMessage("Lost connection while checking sign-in status.");
        }
      }, flow.interval * 1000);
    } catch {
      setError("Failed to start sign-in.");
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Connections
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Add one connection per cloud account you want to audit in the <strong>{environment}</strong>{" "}
        environment — e.g. separate Azure connections for different signed-in accounts. Each
        connection's tenants/subscriptions are fetched using its own credentials.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {PROVIDERS.map((provider) => {
          const providerConnections = connections.filter((c) => c.provider === provider);
          return (
            <Card key={provider} variant="outlined">
              <CardContent>
                <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1 }}>
                  <Typography variant="h6">{PROVIDER_LABELS[provider]}</Typography>
                  <Tooltip
                    title={
                      CONNECTABLE[provider]
                        ? `Add a new ${PROVIDER_LABELS[provider]} connection`
                        : `Not yet supported for ${PROVIDER_LABELS[provider]}`
                    }
                  >
                    <span>
                      <Button
                        size="small"
                        startIcon={<AddIcon />}
                        disabled={!CONNECTABLE[provider]}
                        onClick={() => openAdd(provider)}
                      >
                        Add Connection
                      </Button>
                    </span>
                  </Tooltip>
                </Box>

                {providerConnections.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    No connections yet.
                  </Typography>
                ) : (
                  <List disablePadding>
                    {providerConnections.map((connection, index) => (
                      <Box key={connection.id}>
                        {index > 0 && <Divider component="li" />}
                        <Box
                          sx={{
                            display: "flex",
                            flexWrap: "wrap",
                            alignItems: "center",
                            justifyContent: "space-between",
                            gap: 1.5,
                            py: 1.5,
                          }}
                        >
                          <Box sx={{ minWidth: 0, flex: "1 1 240px" }}>
                            <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                              <Typography variant="subtitle2" noWrap>
                                {connection.name}
                              </Typography>
                              <Chip
                                label={environment}
                                size="small"
                                variant="outlined"
                                sx={{ height: 20, textTransform: "uppercase", fontSize: "0.65rem" }}
                              />
                              {connection.connected ? (
                                <Chip
                                  icon={<CheckCircleIcon fontSize="small" />}
                                  label="Connected"
                                  size="small"
                                  color="success"
                                  variant="outlined"
                                />
                              ) : (
                                <Chip
                                  icon={<CancelIcon fontSize="small" />}
                                  label="Not connected"
                                  size="small"
                                  variant="outlined"
                                />
                              )}
                            </Box>
                            <Typography variant="body2" color="text.secondary" noWrap>
                              {REQUIRES_CONFIG[connection.provider]
                                ? [connection.sso_login_url, connection.region].filter(Boolean).join(" · ") ||
                                  "Not configured"
                                : "Device code sign-in"}
                            </Typography>
                          </Box>
                          <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexShrink: 0 }}>
                            {REQUIRES_CONFIG[connection.provider] && (
                              <Button size="small" onClick={() => openEdit(connection)}>
                                Configure
                              </Button>
                            )}
                            <Button
                              size="small"
                              variant="contained"
                              onClick={() => handleConnect(connection)}
                            >
                              {connection.connected ? "Revalidate" : "Connect"}
                            </Button>
                            <IconButton
                              size="small"
                              aria-label="Delete connection"
                              onClick={() => handleDelete(connection)}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Box>
                        </Box>
                      </Box>
                    ))}
                  </List>
                )}
              </CardContent>
            </Card>
          );
        })}
      </Box>

      <Dialog open={Boolean(addingProvider)} onClose={() => setAddingProvider(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Add {addingProvider ? PROVIDER_LABELS[addingProvider] : ""} Connection</DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            label="Connection name"
            placeholder="e.g. example@abc.com"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            fullWidth
            autoFocus
            helperText="A label to tell this connection apart from others — typically the account you'll sign in with."
          />
          {addingProvider && REQUIRES_CONFIG[addingProvider] && (
            <>
              <TextField
                label="IAM Identity Center Start URL"
                value={newSsoLoginUrl}
                onChange={(e) => setNewSsoLoginUrl(e.target.value)}
                fullWidth
              />
              <TextField
                label="Region"
                placeholder="ap-south-1"
                value={newRegion}
                onChange={(e) => setNewRegion(e.target.value)}
                fullWidth
              />
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddingProvider(null)}>Cancel</Button>
          <Button variant="contained" onClick={handleCreateConnection} disabled={isSaving || !newName.trim()}>
            Add
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(editing)} onClose={() => setEditing(null)} maxWidth="sm" fullWidth>
        <DialogTitle>
          Configure {editing?.name}
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          <TextField
            label={editing?.provider === "aws" ? "IAM Identity Center Start URL" : "SSO Login URL"}
            value={ssoLoginUrl}
            onChange={(e) => setSsoLoginUrl(e.target.value)}
            fullWidth
            autoFocus
          />
          <TextField
            label="Region"
            placeholder={editing?.provider === "aws" ? "ap-south-1" : "eastus"}
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditing(null)}>Cancel</Button>
          <Button variant="contained" onClick={handleSaveConfig} disabled={isSaving}>
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(deviceFlow)} onClose={handleCancelDeviceFlow} maxWidth="xs" fullWidth>
        <DialogTitle>
          {(() => {
            const target = connections.find((c) => c.id === deviceFlowConnectionId);
            const providerLabel = target ? PROVIDER_LABELS[target.provider] : "";
            return `Sign in to ${providerLabel}${target ? ` — ${target.name}` : ""}`;
          })()}
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, alignItems: "center", pt: 1 }}>
          {deviceFlowMessage ? (
            <Alert severity="error" sx={{ width: "100%" }}>
              {deviceFlowMessage}
            </Alert>
          ) : (
            <>
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: "center" }}>
                Go to{" "}
                <Link href={deviceFlow?.verification_uri} target="_blank" rel="noopener">
                  {deviceFlow?.verification_uri}
                </Link>{" "}
                and enter this code:
              </Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, letterSpacing: 2 }}>
                {deviceFlow?.user_code}
              </Typography>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <CircularProgress size={16} />
                <Typography variant="caption" color="text.secondary">
                  Waiting for sign-in to complete...
                </Typography>
              </Box>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelDeviceFlow}>
            {deviceFlowMessage ? "Close" : "Cancel"}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
