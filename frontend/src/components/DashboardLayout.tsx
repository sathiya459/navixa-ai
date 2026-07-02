import { Outlet, useNavigate } from "react-router-dom";
import {
  AppBar,
  Box,
  Button,
  Container,
  Toolbar,
  Typography,
} from "@mui/material";
import { useAuth } from "../auth/AuthContext";

export function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      <AppBar position="static" color="primary" elevation={0}>
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 700 }}>
            NAVIXA AI
            <Typography component="span" variant="body2" sx={{ ml: 1.5, opacity: 0.85 }}>
              Multi-Cloud Network Architecture Intelligence Platform
            </Typography>
          </Typography>
          <Button color="inherit" onClick={() => navigate("/dashboard")}>
            Dashboard
          </Button>
          <Button color="inherit" onClick={() => navigate("/tenants")}>
            Tenants
          </Button>
          <Button color="inherit" onClick={() => navigate("/audits/new")}>
            New Audit
          </Button>
          {user && (
            <Typography variant="body2" sx={{ mx: 2 }}>
              {user.email} ({user.roles.join(", ")})
            </Typography>
          )}
          <Button color="inherit" onClick={handleLogout}>
            Sign Out
          </Button>
        </Toolbar>
      </AppBar>
      <Container maxWidth="lg" sx={{ py: 4, flexGrow: 1 }}>
        <Outlet />
      </Container>
    </Box>
  );
}
