import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  IconButton,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import VisibilityIcon from "@mui/icons-material/Visibility";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutlined";
import AssignmentOutlinedIcon from "@mui/icons-material/AssignmentOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutlined";
import PendingActionsOutlinedIcon from "@mui/icons-material/PendingActionsOutlined";
import { useAuth } from "../auth/AuthContext";
import { deleteAuditJob, getJobStatus, listAuditJobs } from "../api/discover";
import { listScopes } from "../api/tenants";
import type { AuditJobListItem, AuditJobStatus, JobStatus, Scope } from "../api/types";

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

const STATUS_COLOR: Record<AuditJobStatus, "default" | "success" | "warning" | "error" | "info"> = {
  queued: "default",
  discovering: "info",
  graphing: "info",
  validating: "info",
  pathfinding: "info",
  analyzing: "info",
  reporting: "info",
  completed: "success",
  failed: "error",
  partial: "warning",
};

const RESOURCE_STATUS_COLOR: Record<string, "default" | "success" | "warning" | "error"> = {
  success: "success",
  partial: "warning",
  failed: "error",
};

const TERMINAL_STATUSES: AuditJobStatus[] = ["completed", "failed", "partial"];

function ProgressDialog({
  job,
  onClose,
}: {
  job: AuditJobListItem | null;
  onClose: () => void;
}) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [scopeNames, setScopeNames] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!job) return;
    setStatus(null);
    setError(null);

    listScopes(job.tenant_id)
      .then((scopes: Scope[]) => {
        setScopeNames(Object.fromEntries(scopes.map((s) => [s.id, s.display_name])));
      })
      .catch(() => {
        // Non-fatal: falls back to showing raw scope IDs.
      });

    function poll() {
      getJobStatus(job!.id)
        .then((data) => {
          setStatus(data);
          if (TERMINAL_STATUSES.includes(data.status) && pollTimer.current) {
            clearInterval(pollTimer.current);
            pollTimer.current = null;
          }
        })
        .catch(() => setError("Failed to load job progress."));
    }

    poll();
    pollTimer.current = setInterval(poll, 2000);
    return () => {
      if (pollTimer.current) clearInterval(pollTimer.current);
      pollTimer.current = null;
    };
  }, [job]);

  const isRunning = status && !TERMINAL_STATUSES.includes(status.status);

  return (
    <Dialog open={Boolean(job)} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Discovery Progress
        {job && (
          <Typography variant="body2" color="text.secondary">
            {job.tenant_name}
          </Typography>
        )}
      </DialogTitle>
      <DialogContent>
        {error && <Alert severity="error">{error}</Alert>}
        {!error && !status && (
          <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", py: 2 }}>
            <CircularProgress size={20} />
            <Typography variant="body2">Loading progress...</Typography>
          </Stack>
        )}
        {status && (
          <Box>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 2 }}>
              <Typography variant="body2">Overall status:</Typography>
              <Chip
                label={status.status}
                size="small"
                color={STATUS_COLOR[status.status]}
              />
              {isRunning && <CircularProgress size={14} />}
            </Stack>

            {status.scopes.map((scope) => (
              <Box key={scope.scope_id} sx={{ mb: 2 }}>
                <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 1 }}>
                  <Typography variant="subtitle2">
                    {scopeNames[scope.scope_id] || scope.scope_id}
                  </Typography>
                  <Chip label={scope.status} size="small" variant="outlined" />
                </Stack>
                {scope.resource_statuses.length > 0 ? (
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Resource Type</TableCell>
                          <TableCell>Status</TableCell>
                          <TableCell align="right">Items</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {scope.resource_statuses.map((rs) => (
                          <TableRow key={rs.resource_type}>
                            <TableCell>{rs.resource_type}</TableCell>
                            <TableCell>
                              <Chip
                                label={rs.status}
                                size="small"
                                color={RESOURCE_STATUS_COLOR[rs.status] ?? "default"}
                              />
                              {rs.error_detail && (
                                <Typography
                                  variant="caption"
                                  color="error"
                                  sx={{ display: "block", mt: 0.5 }}
                                >
                                  {rs.error_detail}
                                </Typography>
                              )}
                            </TableCell>
                            <TableCell align="right">{rs.items_collected}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    Waiting for resource collection to start...
                  </Typography>
                )}
              </Box>
            ))}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}

export function AuditJobsPage() {
  const { user } = useAuth();
  const isAdmin = Boolean(user?.roles.includes("admin"));
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<AuditJobListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [progressJob, setProgressJob] = useState<AuditJobListItem | null>(null);

  function reload() {
    listAuditJobs()
      .then(setJobs)
      .catch(() => setError("Failed to load audit jobs."));
  }

  useEffect(reload, []);

  async function handleConfirmDelete() {
    if (!pendingDeleteId) return;
    setIsDeleting(true);
    try {
      await deleteAuditJob(pendingDeleteId);
      setPendingDeleteId(null);
      reload();
    } catch (err) {
      const message = axios.isAxiosError(err) ? err.response?.data?.detail : undefined;
      setError(typeof message === "string" ? message : "Failed to delete audit job.");
      setPendingDeleteId(null);
    } finally {
      setIsDeleting(false);
    }
  }

  const completedCount = jobs.filter((j) => j.status === "completed").length;
  const runningCount = jobs.filter(
    (j) => !["completed", "failed", "partial"].includes(j.status),
  ).length;

  return (
    <Box>
      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "flex-start", mb: 3 }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            Audit Jobs
          </Typography>
          <Typography variant="body1" color="text.secondary">
            History of NAVIXA Discover / Validate runs across all tenants.
          </Typography>
        </Box>
        {isAdmin && (
          <Button
            variant="contained"
            startIcon={<AddCircleOutlineIcon />}
            onClick={() => navigate("/audits/new")}
            sx={{ flexShrink: 0 }}
          >
            New Audit
          </Button>
        )}
      </Stack>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard icon={<AssignmentOutlinedIcon />} label="Total Jobs" value={jobs.length} />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard icon={<CheckCircleOutlineIcon />} label="Completed" value={completedCount} />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard icon={<PendingActionsOutlinedIcon />} label="In Progress" value={runningCount} />
        </Grid>
      </Grid>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {jobs.length === 0 && !error ? (
        <Paper variant="outlined" sx={{ py: 8, textAlign: "center" }}>
          <Typography variant="body1" color="text.secondary" sx={{ mb: isAdmin ? 2 : 0 }}>
            No audit jobs yet.
          </Typography>
          {isAdmin && (
            <Button variant="outlined" size="small" onClick={() => navigate("/audits/new")}>
              Start a New Audit
            </Button>
          )}
        </Paper>
      ) : (
        <TableContainer component={Paper} variant="outlined">
          <Table>
            <TableHead>
              <TableRow>
                <TableCell width="30%">Tenant</TableCell>
                <TableCell width="15%">Status</TableCell>
                <TableCell width="10%">Scopes</TableCell>
                <TableCell width="25%">Created</TableCell>
                <TableCell width="20%" align="right">
                  Actions
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {jobs.map((job) => (
                <TableRow
                  key={job.id}
                  hover
                  onClick={() => setProgressJob(job)}
                  sx={{ cursor: "pointer" }}
                >
                  <TableCell>{job.tenant_name}</TableCell>
                  <TableCell>
                    <Chip label={job.status} size="small" color={STATUS_COLOR[job.status]} />
                  </TableCell>
                  <TableCell>{job.scope_count}</TableCell>
                  <TableCell>{new Date(job.created_at).toLocaleString()}</TableCell>
                  <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                    <IconButton
                      size="small"
                      title="View Progress"
                      onClick={() => setProgressJob(job)}
                    >
                      <VisibilityIcon fontSize="small" />
                    </IconButton>
                    <IconButton
                      size="small"
                      title="View Topology"
                      onClick={() => navigate(`/audits/${job.id}/topology`)}
                    >
                      <AccountTreeIcon fontSize="small" />
                    </IconButton>
                    {isAdmin && (
                      <IconButton
                        size="small"
                        title="Delete"
                        onClick={() => setPendingDeleteId(job.id)}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <ProgressDialog job={progressJob} onClose={() => setProgressJob(null)} />

      <Dialog open={Boolean(pendingDeleteId)} onClose={() => setPendingDeleteId(null)}>
        <DialogTitle>Delete Audit Job</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            This permanently deletes the job, its collected resources, and any findings generated
            from it. This cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPendingDeleteId(null)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={handleConfirmDelete} disabled={isDeleting}>
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
