import { useNavigate } from "react-router-dom";
import { Box, Button, Card, CardActions, CardContent, Typography } from "@mui/material";

export function DashboardHomePage() {
  const navigate = useNavigate();

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Multi-Cloud Network Architecture Intelligence Platform
      </Typography>
      <Card sx={{ maxWidth: 420 }}>
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
    </Box>
  );
}
