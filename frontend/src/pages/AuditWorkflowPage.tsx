import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
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
  Step,
  StepLabel,
  Stepper,
  TextField,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useEnvironment } from "../auth/EnvironmentContext";
import { listScopes, listTenants } from "../api/tenants";
import { createAuditJob, getJobResources, getJobStatus } from "../api/discover";
import { getFindings, runValidation } from "../api/validate";
import { listAIProviders } from "../api/insightai";
import type {
  AIProviderName,
  AIProviderStatus,
  AnalysisMode,
  CloudProvider,
  Finding,
  JobStatus,
  NetworkResource,
  Scope,
  Tenant,
} from "../api/types";

const AI_PROVIDER_LABELS: Record<AIProviderName, string> = {
  claude: "Claude",
  openai: "OpenAI",
  azure_openai: "Azure OpenAI",
  gemini: "Gemini",
  bedrock: "AWS Bedrock",
};

const CLOUD_TYPES: { value: CloudProvider; label: string }[] = [
  { value: "azure", label: "Azure" },
  { value: "aws", label: "AWS" },
  { value: "gcp", label: "GCP" },
  { value: "oci", label: "OCI" },
];

const RESOURCE_TYPE_OPTIONS: { value: string; label: string; required?: boolean; awsOnly?: boolean }[] = [
  { value: "network", label: "Networks (VPC / VNet)", required: true },
  { value: "subnet", label: "Subnets" },
  { value: "route_table", label: "Route Tables" },
  { value: "security_group", label: "Security Groups" },
  { value: "gateway", label: "Gateways", awsOnly: true },
  { value: "peering_connection", label: "Peering Connections" },
];

const SETUP_STEPS = ["Cloud Type", "Tenant", "Subscription", "Resource Types"];
const LIFECYCLE_STEPS = ["Discover", "Validate", "Complete"];

const TERMINAL_JOB_STATUSES = ["completed", "partial", "failed"];

export function AuditWorkflowPage() {
  const navigate = useNavigate();
  const { environment } = useEnvironment();

  // --- Setup wizard state ---
  const [setupStep, setSetupStep] = useState(0);
  const [provider, setProvider] = useState<CloudProvider>("azure");
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState("");
  const [scopes, setScopes] = useState<Scope[]>([]);
  const [selectedScopeIds, setSelectedScopeIds] = useState<string[]>([]);
  const [selectedResourceTypes, setSelectedResourceTypes] = useState<string[]>(
    RESOURCE_TYPE_OPTIONS.map((r) => r.value),
  );

  // --- Lifecycle state (once a job exists) ---
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [hubCandidates, setHubCandidates] = useState<NetworkResource[]>([]);
  const [selectedHubIds, setSelectedHubIds] = useState<string[]>([]);
  const [hubsConfirmed, setHubsConfirmed] = useState(false);
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("rule_engine");
  const [aiProviders, setAiProviders] = useState<AIProviderStatus[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<AIProviderName | "">("");
  const [findings, setFindings] = useState<Finding[]>([]);
  const [findingsLoaded, setFindingsLoaded] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTenants(provider, environment)
      .then(setTenants)
      .catch(() => setError("Failed to load tenants."));
    setSelectedTenantId("");
    setScopes([]);
    setSelectedScopeIds([]);
  }, [provider, environment]);

  useEffect(() => {
    listAIProviders()
      .then(setAiProviders)
      .catch(() => {
        // Non-fatal: only Admins can list providers; default to rule_engine.
      });
  }, []);

  useEffect(() => {
    if (!selectedTenantId) return;
    listScopes(selectedTenantId).then(setScopes).catch(() => setError("Failed to load scopes."));
  }, [selectedTenantId]);

  const discoveryDone = Boolean(jobStatus && TERMINAL_JOB_STATUSES.includes(jobStatus.status));

  useEffect(() => {
    if (!jobId || discoveryDone) return;
    const interval = setInterval(() => {
      getJobStatus(jobId).then(setJobStatus);
    }, 2000);
    return () => clearInterval(interval);
  }, [jobId, discoveryDone]);

  useEffect(() => {
    if (!jobId || !discoveryDone || hubsConfirmed) return;
    getJobResources(jobId, { resource_type: "network" })
      .then((resources) => {
        setHubCandidates(resources);
      })
      .catch(() => setError("Failed to load discovered networks."));
  }, [jobId, discoveryDone, hubsConfirmed]);

  function toggleScope(scopeId: string) {
    setSelectedScopeIds((prev) =>
      prev.includes(scopeId) ? prev.filter((id) => id !== scopeId) : [...prev, scopeId],
    );
  }

  function toggleResourceType(value: string) {
    setSelectedResourceTypes((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value],
    );
  }

  function toggleHub(nativeId: string) {
    setSelectedHubIds((prev) =>
      prev.includes(nativeId) ? prev.filter((id) => id !== nativeId) : [...prev, nativeId],
    );
  }

  async function handleRunDiscovery() {
    setIsLoading(true);
    setError(null);
    try {
      const job = await createAuditJob(
        selectedTenantId,
        selectedScopeIds,
        undefined,
        selectedResourceTypes,
      );
      setJobId(job.id);
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
      await runValidation(
        jobId,
        selectedHubIds,
        analysisMode,
        analysisMode === "ai" ? (selectedProvider as AIProviderName) : undefined,
      );
      const results = await getFindings(jobId);
      setFindings(results);
      setFindingsLoaded(true);
    } catch (err) {
      const message = axios.isAxiosError(err)
        ? (err.response?.data?.detail ?? "Failed to run validation.")
        : "Failed to run validation.";
      setError(typeof message === "string" ? message : "Failed to run validation.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleClose() {
    navigate("/audits");
  }

  const lifecycleActiveStep = !discoveryDone ? 0 : findingsLoaded ? 2 : 1;

  return (
    <Dialog open onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        New Audit
        <IconButton onClick={handleClose} size="small">
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {!jobId ? (
          <Box>
            <Stepper activeStep={setupStep} sx={{ mb: 3 }}>
              {SETUP_STEPS.map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>

            {setupStep === 0 && (
              <Stack spacing={2}>
                <TextField
                  select
                  label="Cloud Type"
                  value={provider}
                  onChange={(e) => setProvider(e.target.value as CloudProvider)}
                  fullWidth
                >
                  {CLOUD_TYPES.map((c) => (
                    <MenuItem key={c.value} value={c.value}>
                      {c.label}
                    </MenuItem>
                  ))}
                </TextField>
                <Box>
                  <Button variant="contained" onClick={() => setSetupStep(1)}>
                    Next
                  </Button>
                </Box>
              </Stack>
            )}

            {setupStep === 1 && (
              <Stack spacing={2}>
                <TextField
                  select
                  label="Cloud Tenant"
                  value={selectedTenantId}
                  onChange={(e) => setSelectedTenantId(e.target.value)}
                  fullWidth
                  helperText={tenants.length === 0 ? `No ${provider.toUpperCase()} tenants registered for ${environment}` : undefined}
                >
                  {tenants.map((tenant) => (
                    <MenuItem key={tenant.id} value={tenant.id}>
                      {tenant.tenant_name}
                    </MenuItem>
                  ))}
                </TextField>
                <Stack direction="row" spacing={2}>
                  <Button onClick={() => setSetupStep(0)}>Back</Button>
                  <Button
                    variant="contained"
                    disabled={!selectedTenantId}
                    onClick={() => setSetupStep(2)}
                  >
                    Next
                  </Button>
                </Stack>
              </Stack>
            )}

            {setupStep === 2 && (
              <Stack spacing={2}>
                <Typography variant="body2" color="text.secondary">
                  Select one or more subscriptions/accounts to include in this audit.
                </Typography>
                <List dense>
                  {scopes.map((scope) => (
                    <ListItem key={scope.id} disablePadding>
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={selectedScopeIds.includes(scope.id)}
                            onChange={() => toggleScope(scope.id)}
                          />
                        }
                        label={
                          <ListItemText primary={scope.display_name} secondary={scope.external_scope_id} />
                        }
                      />
                    </ListItem>
                  ))}
                  {scopes.length === 0 && (
                    <Typography variant="body2" color="text.secondary">
                      No subscriptions/accounts registered for this tenant.
                    </Typography>
                  )}
                </List>
                <Stack direction="row" spacing={2}>
                  <Button onClick={() => setSetupStep(1)}>Back</Button>
                  <Button
                    variant="contained"
                    disabled={selectedScopeIds.length === 0}
                    onClick={() => setSetupStep(3)}
                  >
                    Next
                  </Button>
                </Stack>
              </Stack>
            )}

            {setupStep === 3 && (
              <Stack spacing={2}>
                <Typography variant="body2" color="text.secondary">
                  Choose which resource/service types NAVIXA Discover should collect. Networks are
                  always included since they're required for hub designation.
                </Typography>
                <List dense>
                  {RESOURCE_TYPE_OPTIONS.filter((r) => !r.awsOnly || provider === "aws").map((r) => (
                    <ListItem key={r.value} disablePadding>
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={selectedResourceTypes.includes(r.value)}
                            disabled={r.required}
                            onChange={() => toggleResourceType(r.value)}
                          />
                        }
                        label={r.label}
                      />
                    </ListItem>
                  ))}
                </List>
                <Stack direction="row" spacing={2}>
                  <Button onClick={() => setSetupStep(2)}>Back</Button>
                  <Button variant="contained" onClick={handleRunDiscovery} disabled={isLoading}>
                    {isLoading ? "Starting..." : "Run Discover"}
                  </Button>
                </Stack>
              </Stack>
            )}
          </Box>
        ) : (
          <Box>
            <Stepper activeStep={lifecycleActiveStep} sx={{ mb: 3 }}>
              {LIFECYCLE_STEPS.map((label) => (
                <Step key={label}>
                  <StepLabel>{label}</StepLabel>
                </Step>
              ))}
            </Stepper>

            {!discoveryDone && (
              <Stack direction="row" spacing={2} sx={{ alignItems: "center", py: 2 }}>
                <CircularProgress size={24} />
                <Typography>Discovering resources across selected scopes...</Typography>
              </Stack>
            )}

            {jobStatus?.scopes.map((scope) => (
              <Paper key={scope.scope_id} variant="outlined" sx={{ p: 2, mb: 1.5 }}>
                <Typography variant="subtitle2">Scope status: {scope.status}</Typography>
                <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", mt: 1 }}>
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
                </Stack>
              </Paper>
            ))}

            {discoveryDone && !hubsConfirmed && (
              <Stack spacing={2} sx={{ mt: 1 }}>
                <Typography variant="subtitle1">Select Hub Networks</Typography>
                <Typography variant="body2" color="text.secondary">
                  Choose which discovered VPCs/VNets are your Hub networks. Used by NAVIXA Validate
                  to detect unauthorized peering and hub-bypass routing.
                </Typography>
                <List dense>
                  {hubCandidates.map((resource) => (
                    <ListItem key={resource.id} disablePadding>
                      <FormControlLabel
                        control={
                          <Checkbox
                            checked={selectedHubIds.includes(resource.native_id)}
                            onChange={() => toggleHub(resource.native_id)}
                          />
                        }
                        label={
                          <ListItemText
                            primary={resource.name || resource.native_id}
                            secondary={resource.native_id}
                          />
                        }
                      />
                    </ListItem>
                  ))}
                  {hubCandidates.length === 0 && (
                    <Typography variant="body2" color="text.secondary">
                      No networks (VPCs/VNets) were discovered.
                    </Typography>
                  )}
                </List>
                <Box>
                  <Button variant="contained" onClick={() => setHubsConfirmed(true)}>
                    Confirm Hub Selection
                  </Button>
                </Box>
                {hubCandidates.length > 0 && selectedHubIds.length === 0 && (
                  <Typography variant="body2" color="text.secondary">
                    No hub selected — proceeding without a designated hub network is valid if
                    none of the discovered VPCs/VNets are actually your hub.
                  </Typography>
                )}
              </Stack>
            )}

            {discoveryDone && hubsConfirmed && !findingsLoaded && (
              <Stack spacing={2} sx={{ mt: 1 }}>
                <Typography variant="subtitle1">Analysis Mode</Typography>
                <TextField
                  select
                  label="How should findings be generated?"
                  value={analysisMode}
                  onChange={(e) => setAnalysisMode(e.target.value as AnalysisMode)}
                  sx={{ maxWidth: 420 }}
                >
                  <MenuItem value="rule_engine">Rule Engine (deterministic, NAVIXA Validate)</MenuItem>
                  <MenuItem value="ai">AI Analysis (LLM-based deviation detection)</MenuItem>
                </TextField>

                {analysisMode === "ai" && (
                  <TextField
                    select
                    label="AI Provider"
                    value={selectedProvider}
                    onChange={(e) => setSelectedProvider(e.target.value as AIProviderName)}
                    sx={{ maxWidth: 420 }}
                    helperText={
                      aiProviders.length === 0
                        ? "Could not load provider status"
                        : "Providers marked (not configured) will fail until an API key is set"
                    }
                  >
                    {aiProviders.map((p) => (
                      <MenuItem key={p.provider} value={p.provider}>
                        {AI_PROVIDER_LABELS[p.provider]}
                        {!p.configured ? " (not configured)" : ""}
                      </MenuItem>
                    ))}
                  </TextField>
                )}

                <Stack direction="row" spacing={2}>
                  <Button
                    variant="contained"
                    disabled={isLoading || (analysisMode === "ai" && !selectedProvider)}
                    onClick={handleRunValidation}
                  >
                    {isLoading ? "Running..." : "Run Validate"}
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={() => navigate(`/audits/${jobId}/topology`, { state: { hubIds: selectedHubIds } })}
                  >
                    View Topology
                  </Button>
                </Stack>
              </Stack>
            )}

            {findingsLoaded ? (
              <Stack spacing={2} sx={{ mt: 1 }}>
                <Typography variant="h6">NAVIXA Validate Findings ({findings.length})</Typography>
                {findings.length === 0 && (
                  <Alert severity="success">No Hub-and-Spoke violations detected.</Alert>
                )}
                {findings.map((finding) => (
                  <Paper key={finding.id} variant="outlined" sx={{ p: 2 }}>
                    <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
                      <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
                        {finding.title}
                      </Typography>
                      {finding.module === "ai_analysis" && (
                        <Chip label="AI" size="small" color="secondary" variant="outlined" />
                      )}
                      <Chip label={finding.severity} color="error" size="small" />
                    </Stack>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      {finding.description}
                    </Typography>
                  </Paper>
                ))}
                <Box>
                  <Button variant="contained" onClick={handleClose}>
                    Close
                  </Button>
                </Box>
              </Stack>
            ) : null}
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );
}
