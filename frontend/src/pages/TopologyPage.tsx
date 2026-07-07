import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import ReactFlow, {
  Background,
  Controls,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import FullscreenIcon from "@mui/icons-material/Fullscreen";
import FullscreenExitIcon from "@mui/icons-material/FullscreenExit";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import { useAuth } from "../auth/AuthContext";
import { getJobTopology, syncJobTopology } from "../api/graph";
import { generateInsights, getInsights, listAIProviders } from "../api/insightai";
import type { AIProviderName, AIProviderStatus, GraphEdge, GraphNode } from "../api/types";
import { mapGraphToFlow } from "./topology/mapGraphToFlow";
import { TopologyNode } from "./topology/TopologyNode";
import { exportTopologyToPdf } from "./topology/exportTopology";

const NODE_TYPES = { topology: TopologyNode };

const AI_PROVIDER_LABELS: Record<AIProviderName, string> = {
  claude: "Claude",
  openai: "OpenAI",
  azure_openai: "Azure OpenAI",
  gemini: "Gemini",
  bedrock: "AWS Bedrock",
};

export function TopologyPage() {
  return (
    <ReactFlowProvider>
      <TopologyPageInner />
    </ReactFlowProvider>
  );
}

function TopologyPageInner() {
  const { jobId } = useParams<{ jobId: string }>();
  const { user } = useAuth();
  const isAdmin = Boolean(user?.roles.includes("admin"));

  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [graphEdges, setGraphEdges] = useState<GraphEdge[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [aiProviders, setAiProviders] = useState<AIProviderStatus[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<AIProviderName | "">("");
  const [explanation, setExplanation] = useState<string | null>(null);
  const [isExplaining, setIsExplaining] = useState(false);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const reactFlowInstance = useReactFlow();

  useEffect(() => {
    const handler = () => setIsFullscreen(document.fullscreenElement === containerRef.current);
    document.addEventListener("fullscreenchange", handler);
    return () => document.removeEventListener("fullscreenchange", handler);
  }, []);

  function toggleFullscreen() {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      containerRef.current?.requestFullscreen();
    }
  }

  async function handleExportPdf() {
    setIsExporting(true);
    try {
      await exportTopologyToPdf(reactFlowInstance);
    } finally {
      setIsExporting(false);
    }
  }

  const loadTopology = useCallback(() => {
    if (!jobId) return;
    setIsLoading(true);
    getJobTopology(jobId)
      .then((topology) => {
        setGraphNodes(topology.nodes);
        setGraphEdges(topology.edges);
        setError(null);
      })
      .catch(() => setError("Failed to load topology for this job."))
      .finally(() => setIsLoading(false));
  }, [jobId]);

  useEffect(() => {
    loadTopology();
  }, [loadTopology]);

  useEffect(() => {
    listAIProviders()
      .then(setAiProviders)
      .catch(() => {
        // Non-fatal: only Admins can list providers.
      });
  }, []);

  useEffect(() => {
    if (!jobId) return;
    getInsights(jobId, "topology_explanation")
      .then((insights) => {
        if (insights.length > 0) {
          setExplanation(insights[insights.length - 1].content);
        }
      })
      .catch(() => {
        // Non-fatal: explanation panel simply stays empty.
      });
  }, [jobId]);

  async function handleSync() {
    if (!jobId) return;
    setIsSyncing(true);
    setError(null);
    try {
      const topology = await syncJobTopology(jobId);
      setGraphNodes(topology.nodes);
      setGraphEdges(topology.edges);
    } catch {
      setError("Failed to sync topology to the graph.");
    } finally {
      setIsSyncing(false);
    }
  }

  async function handleExplain() {
    if (!jobId || !selectedProvider) return;
    setIsExplaining(true);
    setError(null);
    try {
      await generateInsights(jobId, selectedProvider, ["topology_explanation"]);
      const insights = await getInsights(jobId, "topology_explanation");
      setExplanation(insights.length > 0 ? insights[insights.length - 1].content : null);
    } catch {
      setError("Failed to generate an AI explanation of this topology.");
    } finally {
      setIsExplaining(false);
    }
  }

  const { nodes, edges } = useMemo<{ nodes: Node[]; edges: Edge[] }>(
    () => mapGraphToFlow(graphNodes, graphEdges),
    [graphNodes, graphEdges],
  );

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        NAVIXA Topology
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Hub-and-spoke diagram served from NAVIXA Graph (Neo4j) for this audit job.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {isLoading && (
        <Stack direction="row" spacing={2} sx={{ alignItems: "center", py: 2 }}>
          <CircularProgress size={24} />
          <Typography>Loading topology...</Typography>
        </Stack>
      )}

      {!isLoading && nodes.length === 0 && (
        <Stack spacing={2} sx={{ mb: 2 }}>
          <Alert severity="info">
            No graph data found for this job yet. This job may predate NAVIXA Graph sync, or
            hasn't been synced since its last Discover run.
          </Alert>
          {isAdmin && (
            <Box>
              <Button variant="contained" onClick={handleSync} disabled={isSyncing}>
                {isSyncing ? "Syncing..." : "Sync Topology to Graph"}
              </Button>
            </Box>
          )}
        </Stack>
      )}

      {!isLoading && nodes.length > 0 && isAdmin && (
        <Stack direction="row" spacing={2} sx={{ mb: 2, alignItems: "center", flexWrap: "wrap" }}>
          <Button variant="outlined" onClick={handleSync} disabled={isSyncing}>
            {isSyncing ? "Syncing..." : "Re-sync Topology"}
          </Button>
          <TextField
            select
            label="AI Provider"
            value={selectedProvider}
            onChange={(e) => setSelectedProvider(e.target.value as AIProviderName)}
            sx={{ minWidth: 220 }}
            size="small"
          >
            {aiProviders.map((p) => (
              <MenuItem key={p.provider} value={p.provider}>
                {AI_PROVIDER_LABELS[p.provider]}
                {!p.configured ? " (not configured)" : ""}
              </MenuItem>
            ))}
          </TextField>
          <Button
            variant="contained"
            onClick={handleExplain}
            disabled={isExplaining || !selectedProvider}
          >
            {isExplaining ? "Explaining..." : "Explain with AI"}
          </Button>
        </Stack>
      )}

      {explanation && (
        <Alert severity="info" sx={{ mb: 2, whiteSpace: "pre-line" }}>
          {explanation}
        </Alert>
      )}

      {nodes.length > 0 && (
        <Paper
          ref={containerRef}
          variant="outlined"
          sx={{
            height: isFullscreen ? "100vh" : 500,
            position: "relative",
            backgroundColor: "background.default",
          }}
        >
          <Stack
            direction="row"
            spacing={1}
            sx={{ position: "absolute", top: 8, right: 8, zIndex: 5 }}
          >
            <Tooltip title="Download PDF">
              <span>
                <IconButton size="small" onClick={handleExportPdf} disabled={isExporting}>
                  <PictureAsPdfIcon fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
            <Tooltip title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}>
              <IconButton size="small" onClick={toggleFullscreen}>
                {isFullscreen ? <FullscreenExitIcon fontSize="small" /> : <FullscreenIcon fontSize="small" />}
              </IconButton>
            </Tooltip>
          </Stack>
          <ReactFlow nodes={nodes} edges={edges} nodeTypes={NODE_TYPES} fitView>
            <Background />
            <Controls />
          </ReactFlow>
        </Paper>
      )}
    </Box>
  );
}
