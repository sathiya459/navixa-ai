import { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
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
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useAuth } from "../auth/AuthContext";
import { getJobResources } from "../api/discover";
import { getFindings, runValidation } from "../api/validate";
import { listAIProviders } from "../api/insightai";
import type {
  AIProviderName,
  AIProviderStatus,
  AnalysisMode,
  Finding,
  NetworkResource,
} from "../api/types";

const AI_PROVIDER_LABELS: Record<AIProviderName, string> = {
  claude: "Claude",
  openai: "OpenAI",
  azure_openai: "Azure OpenAI",
  gemini: "Gemini",
  bedrock: "AWS Bedrock",
};

interface ValidationLocationState {
  hubIds?: string[];
}

export function ValidationResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = Boolean(user?.roles.includes("admin"));

  const initialHubIds = (location.state as ValidationLocationState | null)?.hubIds ?? [];

  const [findings, setFindings] = useState<Finding[]>([]);
  const [findingsLoaded, setFindingsLoaded] = useState(false);
  const [hubCandidates, setHubCandidates] = useState<NetworkResource[]>([]);
  const [selectedHubIds, setSelectedHubIds] = useState<string[]>(initialHubIds);
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("rule_engine");
  const [aiProviders, setAiProviders] = useState<AIProviderStatus[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<AIProviderName | "">("");
  const [showRunForm, setShowRunForm] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    setIsLoading(true);
    getFindings(jobId)
      .then((results) => {
        setFindings(results);
        setFindingsLoaded(true);
        setShowRunForm(results.length === 0);
      })
      .catch(() => setError("Failed to load validation findings."))
      .finally(() => setIsLoading(false));
  }, [jobId]);

  useEffect(() => {
    if (!jobId || !showRunForm) return;
    getJobResources(jobId, { resource_type: "network" })
      .then(setHubCandidates)
      .catch(() => setError("Failed to load discovered networks."));
  }, [jobId, showRunForm]);

  useEffect(() => {
    if (!showRunForm) return;
    listAIProviders()
      .then(setAiProviders)
      .catch(() => {
        // Non-fatal: only Admins can list providers; default to rule_engine.
      });
  }, [showRunForm]);

  function toggleHub(nativeId: string) {
    setSelectedHubIds((prev) =>
      prev.includes(nativeId) ? prev.filter((id) => id !== nativeId) : [...prev, nativeId],
    );
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
      setShowRunForm(false);
    } catch (err) {
      const message = axios.isAxiosError(err)
        ? (err.response?.data?.detail ?? "Failed to run validation.")
        : "Failed to run validation.";
      setError(typeof message === "string" ? message : "Failed to run validation.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Hub & Spoke Validation
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        NAVIXA Validate findings for this audit job.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {isLoading && !findingsLoaded && (
        <Stack direction="row" spacing={2} sx={{ alignItems: "center", py: 2 }}>
          <CircularProgress size={24} />
          <Typography>Loading...</Typography>
        </Stack>
      )}

      {findingsLoaded && !showRunForm && (
        <Stack spacing={2}>
          <Typography variant="h6">Findings ({findings.length})</Typography>
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
          {isAdmin && (
            <Box>
              <Button variant="outlined" onClick={() => setShowRunForm(true)}>
                Re-run Validation
              </Button>
            </Box>
          )}
        </Stack>
      )}

      {showRunForm && (
        <Stack spacing={2} sx={{ mt: 1 }}>
          {!isAdmin ? (
            <Alert severity="info">Only admins can run Hub & Spoke Validation.</Alert>
          ) : (
            <>
              <Typography variant="subtitle1">Select Hub Networks</Typography>
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
                    No networks (VPCs/VNets) were discovered for this job.
                  </Typography>
                )}
              </List>

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
                {findingsLoaded && (
                  <Button onClick={() => setShowRunForm(false)}>Cancel</Button>
                )}
              </Stack>
            </>
          )}
        </Stack>
      )}

      <Box sx={{ mt: 3 }}>
        <Button onClick={() => navigate("/audits")}>Back to Audit Jobs</Button>
      </Box>
    </Box>
  );
}
