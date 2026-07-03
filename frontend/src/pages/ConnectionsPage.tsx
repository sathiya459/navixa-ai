import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Paper,
  Tooltip,
  Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel";
import { apiClient } from "../api/client";
import { useEnvironment } from "../auth/EnvironmentContext";
import { listConnections, upsertConnection } from "../api/tenants";
import type { CloudProvider, EnvironmentConnection } from "../api/types";

const CONNECTABLE: Record<CloudProvider, boolean> = {
  aws: true,
  azure: true,
  gcp: false,
  oci: false,
};

// Azure always signs in via standard login.microsoftonline.com using
// NAVIXA's own app registration (or an optional advanced override) - no
// login URL/region needed. Only AWS's IAM Identity Center requires the
// customer's own start URL + region before "Connect" can work.
const REQUIRES_CONFIG: Record<CloudProvider, boolean> = {
  aws: true,
  azure: false,
  gcp: false,
  oci: false,
};

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
  const [editing, setEditing] = useState<EnvironmentConnection | null>(null);
  const [ssoLoginUrl, setSsoLoginUrl] = useState("");
  const [region, setRegion] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  function reload() {
    listConnections(environment)
      .then(setConnections)
      .catch(() => setError("Failed to load connections."));
  }

  useEffect(reload, [environment]);

  function openEdit(connection: EnvironmentConnection) {
    setEditing(connection);
    setSsoLoginUrl(connection.sso_login_url ?? "");
    setRegion(connection.region ?? "");
  }

  async function handleSaveConfig() {
    if (!editing) return;
    setIsSaving(true);
    try {
      await upsertConnection(environment, editing.provider, {
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

  async function handleConnect(connection: EnvironmentConnection) {
    setError(null);
    // Open synchronously (before the await below) so browsers don't block
    // it as an unrequested popup, then navigate it once we have the real
    // authorize URL. The start endpoint requires Admin auth, which a plain
    // window.open(url) can't attach - it has to go through apiClient.
    const popup = window.open("", "navixa-sso", "width=520,height=680");
    if (!popup) {
      setError("Please allow popups for this site to connect via SSO.");
      return;
    }
    try {
      const { data } = await apiClient.get<{ authorize_url: string }>(
        `/connections/${environment}/${connection.provider}/delegated-auth/start`,
      );
      popup.location.href = data.authorize_url;
    } catch {
      popup.close();
      setError("Failed to start sign-in. Check the connection's configuration.");
      return;
    }

    function onMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type !== "navixa-sso-complete") return;
      window.removeEventListener("message", onMessage);
      reload();
    }
    window.addEventListener("message", onMessage);
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Connections
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        One root-credential SSO connection per cloud provider for the{" "}
        <strong>{environment}</strong> environment — reused for Sync Accounts and audit jobs
        across every tenant in this environment.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Provider</TableCell>
              <TableCell>SSO Login URL</TableCell>
              <TableCell>Region</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {connections.map((connection) => (
              <TableRow key={connection.provider} hover>
                <TableCell>{PROVIDER_LABELS[connection.provider]}</TableCell>
                <TableCell>
                  {REQUIRES_CONFIG[connection.provider]
                    ? connection.sso_login_url || "—"
                    : "Microsoft login (login.microsoftonline.com)"}
                </TableCell>
                <TableCell>
                  {REQUIRES_CONFIG[connection.provider] ? connection.region || "—" : "—"}
                </TableCell>
                <TableCell>
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
                </TableCell>
                <TableCell align="right">
                  {REQUIRES_CONFIG[connection.provider] && (
                    <Button size="small" onClick={() => openEdit(connection)} sx={{ mr: 1 }}>
                      Configure
                    </Button>
                  )}
                  <Tooltip
                    title={
                      CONNECTABLE[connection.provider]
                        ? "Sign in via SSO for this environment"
                        : `Not yet supported for ${PROVIDER_LABELS[connection.provider]}`
                    }
                  >
                    <span>
                      <Button
                        size="small"
                        variant="contained"
                        disabled={!CONNECTABLE[connection.provider]}
                        onClick={() => handleConnect(connection)}
                      >
                        Connect
                      </Button>
                    </span>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={Boolean(editing)} onClose={() => setEditing(null)} maxWidth="sm" fullWidth>
        <DialogTitle>
          Configure {editing ? PROVIDER_LABELS[editing.provider] : ""} Connection
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
    </Box>
  );
}
