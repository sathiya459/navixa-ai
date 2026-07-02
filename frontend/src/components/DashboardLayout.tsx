import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  AppBar,
  Avatar,
  Box,
  Chip,
  Container,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Toolbar,
  Typography,
} from "@mui/material";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import BusinessOutlinedIcon from "@mui/icons-material/BusinessOutlined";
import AssignmentOutlinedIcon from "@mui/icons-material/AssignmentOutlined";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutlined";
import LogoutIcon from "@mui/icons-material/Logout";
import HubIcon from "@mui/icons-material/Hub";
import { useAuth } from "../auth/AuthContext";

const DRAWER_WIDTH = 240;

const NAV_ITEMS = [
  { label: "Dashboard", path: "/dashboard", icon: <DashboardOutlinedIcon fontSize="small" /> },
  { label: "Tenants", path: "/tenants", icon: <BusinessOutlinedIcon fontSize="small" /> },
  { label: "Audit Jobs", path: "/audits", icon: <AssignmentOutlinedIcon fontSize="small" /> },
  { label: "New Audit", path: "/audits/new", icon: <AddCircleOutlineIcon fontSize="small" /> },
];

export function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);

  function handleLogout() {
    setMenuAnchor(null);
    logout();
    navigate("/login");
  }

  const initials = user?.email ? user.email.slice(0, 2).toUpperCase() : "?";

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <AppBar
        position="fixed"
        sx={{ zIndex: (theme) => theme.zIndex.drawer + 1, width: "100%" }}
      >
        <Toolbar sx={{ gap: 1.5 }}>
          <HubIcon color="primary" />
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            NAVIXA AI
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
            Multi-Cloud Network Architecture Intelligence Platform
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          {user && (
            <>
              <IconButton onClick={(e) => setMenuAnchor(e.currentTarget)} size="small">
                <Avatar sx={{ width: 34, height: 34, fontSize: 14 }}>{initials}</Avatar>
              </IconButton>
              <Menu
                anchorEl={menuAnchor}
                open={Boolean(menuAnchor)}
                onClose={() => setMenuAnchor(null)}
                anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
                transformOrigin={{ vertical: "top", horizontal: "right" }}
              >
                <Box sx={{ px: 2, py: 1, minWidth: 220 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {user.email}
                  </Typography>
                  <Chip
                    label={user.roles.join(", ")}
                    size="small"
                    variant="outlined"
                    sx={{ mt: 0.5 }}
                  />
                </Box>
                <Divider />
                <MenuItem onClick={handleLogout}>
                  <ListItemIcon>
                    <LogoutIcon fontSize="small" />
                  </ListItemIcon>
                  Sign Out
                </MenuItem>
              </Menu>
            </>
          )}
        </Toolbar>
      </AppBar>

      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: { width: DRAWER_WIDTH, boxSizing: "border-box" },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: "auto", p: 1.5 }}>
          <List>
            {NAV_ITEMS.map((item) => (
              <ListItemButton
                key={item.path}
                component={NavLink}
                to={item.path}
                selected={location.pathname === item.path}
              >
                <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
                <ListItemText
                  slotProps={{ primary: { variant: "body2", sx: { fontWeight: 600 } } }}
                  primary={item.label}
                />
              </ListItemButton>
            ))}
          </List>
        </Box>
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, minWidth: 0 }}>
        <Toolbar />
        <Container maxWidth="xl" sx={{ py: 4 }}>
          <Outlet />
        </Container>
      </Box>
    </Box>
  );
}
