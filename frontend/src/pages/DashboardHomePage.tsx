import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Chip,
  Grid,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import BusinessOutlinedIcon from "@mui/icons-material/BusinessOutlined";
import AssignmentOutlinedIcon from "@mui/icons-material/AssignmentOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutlined";
import { listTenants } from "../api/tenants";
import { listAuditJobs } from "../api/discover";
import type { AuditJobListItem, AuditJobStatus, Tenant } from "../api/types";

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

function SummaryCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
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

export function DashboardHomePage() {
  const navigate = useNavigate();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [jobs, setJobs] = useState<AuditJobListItem[]>([]);

  useEffect(() => {
    listTenants().then(setTenants).catch(() => setTenants([]));
    listAuditJobs().then(setJobs).catch(() => setJobs([]));
  }, []);

  const completedJobs = jobs.filter((j) => j.status === "completed").length;
  const recentJobs = jobs.slice(0, 5);

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Multi-Cloud Network Architecture Intelligence Platform
      </Typography>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <SummaryCard
            icon={<BusinessOutlinedIcon />}
            label="Registered Tenants"
            value={tenants.length}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <SummaryCard
            icon={<AssignmentOutlinedIcon />}
            label="Audit Jobs Run"
            value={jobs.length}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <SummaryCard
            icon={<CheckCircleOutlineIcon />}
            label="Completed Jobs"
            value={completedJobs}
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 7 }}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle1" sx={{ mb: 1.5 }}>
              Recent Audit Jobs
            </Typography>
            {recentJobs.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                No audit jobs yet.
              </Typography>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Tenant</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Created</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {recentJobs.map((job) => (
                    <TableRow
                      key={job.id}
                      hover
                      sx={{ cursor: "pointer" }}
                      onClick={() => navigate("/audits")}
                    >
                      <TableCell>{job.tenant_name}</TableCell>
                      <TableCell>
                        <Chip label={job.status} size="small" color={STATUS_COLOR[job.status]} />
                      </TableCell>
                      <TableCell>{new Date(job.created_at).toLocaleDateString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </Paper>
        </Grid>
        <Grid size={{ xs: 12, md: 5 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">Start a New Audit</Typography>
              <Typography variant="body2" color="text.secondary">
                Select a cloud provider, tenant, and account scope, then run NAVIXA Discover and
                NAVIXA Validate.
              </Typography>
            </CardContent>
            <CardActions>
              <Button size="small" onClick={() => navigate("/audits/new")}>
                Get Started
              </Button>
            </CardActions>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
