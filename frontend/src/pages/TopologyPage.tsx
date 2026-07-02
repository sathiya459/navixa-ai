import { useEffect, useMemo, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import ReactFlow, { Background, Controls, type Edge, type Node } from "reactflow";
import "reactflow/dist/style.css";
import { Alert, Box, Paper, Typography } from "@mui/material";
import { getJobResources } from "../api/discover";
import type { NetworkResource } from "../api/types";
import { buildTopology } from "./topology/buildTopology";

interface TopologyLocationState {
  hubIds?: string[];
}

export function TopologyPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const location = useLocation();

  const [resources, setResources] = useState<NetworkResource[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    getJobResources(jobId)
      .then(setResources)
      .catch(() => setError("Failed to load discovery results for this job."));
  }, [jobId]);

  const { nodes, edges } = useMemo<{ nodes: Node[]; edges: Edge[] }>(() => {
    const hubIds = (location.state as TopologyLocationState | null)?.hubIds ?? [];
    return buildTopology(resources, hubIds);
  }, [resources, location.state]);

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        NAVIXA Topology
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Hub-and-Spoke diagram derived from NAVIXA Discover results for this audit job.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {!error && nodes.length === 0 && (
        <Alert severity="info">No network resources found for this job yet.</Alert>
      )}

      {nodes.length > 0 && (
        <Paper variant="outlined" sx={{ height: 500 }}>
          <ReactFlow nodes={nodes} edges={edges} fitView>
            <Background />
            <Controls />
          </ReactFlow>
        </Paper>
      )}
    </Box>
  );
}
