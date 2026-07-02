import { useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Divider,
  IconButton,
  InputAdornment,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import HubIcon from "@mui/icons-material/Hub";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import PublicIcon from "@mui/icons-material/Public";
import InsightsIcon from "@mui/icons-material/Insights";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import { useAuth } from "../auth/AuthContext";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

const SSO_ERROR_MESSAGES: Record<string, string> = {
  sso_not_configured: "SSO is not configured on this deployment.",
  account_disabled: "Your account has been disabled. Contact an administrator.",
};

const FEATURES = [
  { icon: <PublicIcon fontSize="small" />, text: "Unified visibility across AWS, Azure, GCP and OCI" },
  { icon: <InsightsIcon fontSize="small" />, text: "AI-assisted deviation detection and reporting" },
  { icon: <ShieldOutlinedIcon fontSize="small" />, text: "Hub-and-spoke architecture validation" },
];

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(() => {
    const ssoError = searchParams.get("error");
    if (!ssoError) return null;
    return SSO_ERROR_MESSAGES[ssoError] ?? `Sign-in failed: ${ssoError}`;
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch {
      setError("Invalid email or password.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <Box
        sx={{
          display: { xs: "none", md: "flex" },
          flexDirection: "column",
          justifyContent: "center",
          width: "45%",
          px: 8,
          color: "#fff",
          background: "linear-gradient(155deg, #0B3D91 0%, #072a66 100%)",
        }}
      >
        <Stack direction="row" spacing={1.5} sx={{ alignItems: "center", mb: 4 }}>
          <HubIcon fontSize="large" />
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            NAVIXA AI
          </Typography>
        </Stack>
        <Typography variant="h5" sx={{ fontWeight: 600, mb: 2, lineHeight: 1.4 }}>
          Transforming Cloud Network Complexity Into Actionable Intelligence
        </Typography>
        <Typography variant="body1" sx={{ opacity: 0.8, mb: 5 }}>
          AI-Powered Multi-Cloud Network Architecture Visibility &amp; Exposure Analytics
        </Typography>
        <Stack spacing={2.5}>
          {FEATURES.map((feature) => (
            <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }} key={feature.text}>
              <Box
                sx={{
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  bgcolor: "rgba(255,255,255,0.12)",
                }}
              >
                {feature.icon}
              </Box>
              <Typography variant="body2" sx={{ opacity: 0.9 }}>
                {feature.text}
              </Typography>
            </Stack>
          ))}
        </Stack>
      </Box>

      <Box
        sx={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "background.default",
          px: 2,
        }}
      >
        <Box sx={{ width: "100%", maxWidth: 380 }}>
          <Box sx={{ display: { xs: "flex", md: "none" }, alignItems: "center", gap: 1, mb: 4 }}>
            <HubIcon color="primary" fontSize="large" />
            <Typography variant="h5" sx={{ fontWeight: 700, color: "primary.main" }}>
              NAVIXA AI
            </Typography>
          </Box>

          <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
            Welcome back
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Sign in to continue to your audit workspace.
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box
            component="form"
            onSubmit={handleSubmit}
            sx={{ display: "flex", flexDirection: "column", gap: 2 }}
          >
            <TextField
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              fullWidth
            />
            <TextField
              label="Password"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              fullWidth
              slotProps={{
                input: {
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        size="small"
                        onClick={() => setShowPassword((v) => !v)}
                        edge="end"
                        tabIndex={-1}
                      >
                        {showPassword ? (
                          <VisibilityOffIcon fontSize="small" />
                        ) : (
                          <VisibilityIcon fontSize="small" />
                        )}
                      </IconButton>
                    </InputAdornment>
                  ),
                },
              }}
            />
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={isSubmitting}
              fullWidth
              sx={{ mt: 1, py: 1.2 }}
            >
              {isSubmitting ? "Signing in..." : "Sign In"}
            </Button>
          </Box>

          <Divider sx={{ my: 3 }}>
            <Typography variant="caption" color="text.secondary">
              OR
            </Typography>
          </Divider>

          <Button
            variant="outlined"
            size="large"
            fullWidth
            sx={{ py: 1.2 }}
            onClick={() => {
              window.location.href = `${API_BASE_URL}/auth/sso/entra/login`;
            }}
          >
            Sign in with SSO
          </Button>
        </Box>
      </Box>
    </Box>
  );
}
