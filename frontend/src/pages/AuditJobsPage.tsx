import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Paper,
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
import { useAuth } from "../auth/AuthContext";
import { deleteAuditJob, listAuditJobs } from "../api/discover";
import type { AuditJobListItem, AuditJobStatus } from "../api/types";

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

export function AuditJobsPage() {
  const { user } = useAuth();
  const isAdmin = Boolean(user?.roles.includes("admin"));
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<AuditJobListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

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

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Audit Jobs
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        History of NAVIXA Discover / Validate runs across all tenants.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {jobs.length === 0 && !error && (
        <Alert severity="info">No audit jobs yet. Start one from "New Audit".</Alert>
      )}

      {jobs.length > 0 && (
        <TableContainer component={Paper} variant="outlined">
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Tenant</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Scopes</TableCell>
                <TableCell>Created</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {jobs.map((job) => (
                <TableRow key={job.id} hover>
                  <TableCell>{job.tenant_name}</TableCell>
                  <TableCell>
                    <Chip label={job.status} size="small" color={STATUS_COLOR[job.status]} />
                  </TableCell>
                  <TableCell>{job.scope_count}</TableCell>
                  <TableCell>{new Date(job.created_at).toLocaleString()}</TableCell>
                  <TableCell align="right">
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
