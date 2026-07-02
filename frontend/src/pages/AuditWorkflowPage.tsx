import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  FormControlLabel,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  Paper,
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from "@mui/material";
import { listScopes, listTenants } from "../api/tenants";
import { createAuditJob, getJobStatus } from "../api/discover";
import { getFindings, runValidation } from "../api/validate";
import type { Finding, JobStatus, Scope, Tenant } from "../api/types";

const STEPS = [
  "Select Tenant",
  "Select Account / Subscription / Project",
  "Select Hub Network",
  "Run NAVIXA Discover",
  "Run NAVIXA Validate",
];

export function AuditWorkflowPage() {
  const [activeStep, setActiveStep] = useState(0);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState("");

  const [scopes, setScopes] = useState<Scope[]>([]);
  const [selectedScopeIds, setSelectedScopeIds] = useState<string[]>([]);

  const [hubIdsInput, setHubIdsInput] = useState("");

  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTenants().then(setTenants).catch(() => setError("Failed to load tenants."));
  }, []);

  useEffect(() => {
    if (!selectedTenantId) return;
    listScopes(selectedTenantId).then(setScopes).catch(() => setError("Failed to load scopes."));
  }, [selectedTenantId]);

  useEffect(() => {
    if (!jobId || activeStep !== 3) return;
    const interval = setInterval(() => {
      getJobStatus(jobId).then((status) => {
        setJobStatus(status);
        if (status.status === "completed" || status.status === "partial" || status.status === "failed") {
          clearInterval(interval);
        }
      });
    }, 2000);
    return () => clearInterval(interval);
  }, [jobId, activeStep]);

  function toggleScope(scopeId: string) {
    setSelectedScopeIds((prev) =>
      prev.includes(scopeId) ? prev.filter((id) => id !== scopeId) : [...prev, scopeId],
    );
  }

  async function handleRunDiscovery() {
    setIsLoading(true);
    setError(null);
    try {
      const hubIds = hubIdsInput
        .split(",")
        .map((id) => id.trim())
        .filter(Boolean);
      const job = await createAuditJob(selectedTenantId, selectedScopeIds, hubIds);
      setJobId(job.id);
      setActiveStep(3);
    } catch {
      setError("Failed to start discovery job.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleRunValidation() {
    if (!jobId) return;
    setIsLoading(true);
    setError(null);
    try {
      const hubIds = hubIdsInput
        .split(",")
        .map((id) => id.trim())
        .filter(Boolean);
      await runValidation(jobId, hubIds);
      const results = await getFindings(jobId);
      setFindings(results);
      setActiveStep(4);
    } catch {
      setError("Failed to run validation.");
    } finally {
      setIsLoading(false);
    }
  }

  const selectedTenant = tenants.find((t) => t.id === selectedTenantId);
  const discoveryDone =
    jobStatus?.status === "completed" || jobStatus?.status === "partial" || jobStatus?.status === "failed";

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        New Audit
      </Typography>
      <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
        {STEPS.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        {activeStep === 0 && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <TextField
              select
              label="Cloud Tenant"
              value={selectedTenantId}
              onChange={(e) => setSelectedTenantId(e.target.value)}
              fullWidth
            >
              {tenants.map((tenant) => (
                <MenuItem key={tenant.id} value={tenant.id}>
                  {tenant.tenant_name} ({tenant.provider.toUpperCase()})
                </MenuItem>
              ))}
            </TextField>
            <Box>
              <Button
                variant="contained"
                disabled={!selectedTenantId}
                onClick={() => setActiveStep(1)}
              >
                Next
              </Button>
            </Box>
          </Box>
        )}

        {activeStep === 1 && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <Typography variant="subtitle2">
              Authenticated to {selectedTenant?.tenant_name} via Cloud SSO
            </Typography>
            <List>
              {scopes.map((scope) => (
                <ListItem key={scope.id} disablePadding>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={selectedScopeIds.includes(scope.id)}
                        onChange={() => toggleScope(scope.id)}
                      />
                    }
                    label={<ListItemText primary={scope.display_name} secondary={scope.external_scope_id} />}
                  />
                </ListItem>
              ))}
            </List>
            <Box sx={{ display: "flex", gap: 2 }}>
              <Button onClick={() => setActiveStep(0)}>Back</Button>
              <Button
                variant="contained"
                disabled={selectedScopeIds.length === 0}
                onClick={() => setActiveStep(2)}
              >
                Next
              </Button>
            </Box>
          </Box>
        )}

        {activeStep === 2 && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Enter the native IDs of the approved Hub VPCs/VNets (comma-separated). These are
              used by NAVIXA Validate to detect unauthorized peering and hub-bypass routing.
            </Typography>
            <TextField
              label="Hub VPC/VNet IDs"
              placeholder="vpc-0123abcd, vpc-0456efgh"
              value={hubIdsInput}
              onChange={(e) => setHubIdsInput(e.target.value)}
              fullWidth
            />
            <Box sx={{ display: "flex", gap: 2 }}>
              <Button onClick={() => setActiveStep(1)}>Back</Button>
              <Button variant="contained" onClick={handleRunDiscovery} disabled={isLoading}>
                {isLoading ? "Starting..." : "Run NAVIXA Discover"}
              </Button>
            </Box>
          </Box>
        )}

        {activeStep === 3 && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {!discoveryDone ? (
              <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
                <CircularProgress size={24} />
                <Typography>Discovering resources across selected scopes...</Typography>
              </Box>
            ) : (
              <Typography color={jobStatus?.status === "failed" ? "error" : "text.primary"}>
                Discovery finished with status: {jobStatus?.status}
              </Typography>
            )}
            {jobStatus?.scopes.map((scope) => (
              <Paper key={scope.scope_id} variant="outlined" sx={{ p: 2 }}>
                <Typography variant="subtitle2">Scope status: {scope.status}</Typography>
                <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mt: 1 }}>
                  {scope.resource_statuses.map((rs) => (
                    <Chip
                      key={rs.resource_type}
                      label={`${rs.resource_type}: ${rs.items_collected} (${rs.status})`}
                      color={
                        rs.status === "success" ? "success" : rs.status === "partial" ? "warning" : "error"
                      }
                      size="small"
                    />
                  ))}
                </Box>
              </Paper>
            ))}
            <Box sx={{ display: "flex", gap: 2 }}>
              <Button
                variant="contained"
                disabled={!discoveryDone || isLoading}
                onClick={handleRunValidation}
              >
                {isLoading ? "Running..." : "Run NAVIXA Validate"}
              </Button>
            </Box>
          </Box>
        )}

        {activeStep === 4 && (
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <Typography variant="h6">
              NAVIXA Validate Findings ({findings.length})
            </Typography>
            {findings.length === 0 && (
              <Alert severity="success">No Hub-and-Spoke violations detected.</Alert>
            )}
            {findings.map((finding) => (
              <Paper key={finding.id} variant="outlined" sx={{ p: 2 }}>
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <Typography variant="subtitle1">{finding.title}</Typography>
                  <Chip label={finding.severity} color="error" size="small" />
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  {finding.description}
                </Typography>
              </Paper>
            ))}
          </Box>
        )}
      </Paper>
    </Box>
  );
}
