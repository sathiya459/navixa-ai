import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./AuthContext";

/** Route-level guard mirroring the server-side require_role(ADMIN) checks -
 * a defense-in-depth UX nicety, not the actual security boundary (that's
 * enforced by the API itself). */
export function RequireAdmin() {
  const { user } = useAuth();

  if (!user?.roles.includes("admin")) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
