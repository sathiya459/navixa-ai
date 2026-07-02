import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Box, CircularProgress, Typography } from "@mui/material";
import { getCurrentUser } from "../api/auth";
import { useAuth } from "../auth/AuthContext";

/**
 * Lands here after the backend's /auth/sso/entra/callback redirects with
 * tokens in the URL fragment (never a query string, so they aren't
 * captured in server access logs along the way). Stores them the same
 * way local login does, then hands off to the dashboard.
 */
export function SsoCallbackPage() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();

  useEffect(() => {
    const params = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const error = params.get("error");
    if (error) {
      navigate(`/login?error=${encodeURIComponent(error)}`, { replace: true });
      return;
    }

    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");
    if (!accessToken || !refreshToken) {
      navigate("/login?error=sso_failed", { replace: true });
      return;
    }

    localStorage.setItem("navixa_access_token", accessToken);
    localStorage.setItem("navixa_refresh_token", refreshToken);

    getCurrentUser()
      .then(() => {
        refreshUser();
        navigate("/dashboard", { replace: true });
      })
      .catch(() => navigate("/login?error=sso_failed", { replace: true }));
  }, [navigate, refreshUser]);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        gap: 2,
      }}
    >
      <CircularProgress />
      <Typography color="text.secondary">Completing sign-in...</Typography>
    </Box>
  );
}
