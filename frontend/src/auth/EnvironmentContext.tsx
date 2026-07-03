import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import type { Environment } from "../api/types";
import { useAuth } from "./AuthContext";

interface EnvironmentContextValue {
  environment: Environment;
  setEnvironment: (env: Environment) => void;
}

const EnvironmentContext = createContext<EnvironmentContextValue | undefined>(undefined);

const STORAGE_KEY = "navixa_environment";

export function EnvironmentProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const isAdmin = Boolean(user?.roles.includes("admin"));
  const [environment, setEnvironmentState] = useState<Environment>("dev");

  useEffect(() => {
    if (!isAdmin) {
      setEnvironmentState("dev");
      return;
    }
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "dev" || stored === "prod") {
      setEnvironmentState(stored);
    }
  }, [isAdmin]);

  function setEnvironment(env: Environment) {
    // Readers never get to switch - the selector UI is admin-only, but this
    // is a defense-in-depth check too (the real enforcement is server-side).
    if (!isAdmin) return;
    setEnvironmentState(env);
    localStorage.setItem(STORAGE_KEY, env);
  }

  return (
    <EnvironmentContext.Provider value={{ environment, setEnvironment }}>
      {children}
    </EnvironmentContext.Provider>
  );
}

export function useEnvironment(): EnvironmentContextValue {
  const context = useContext(EnvironmentContext);
  if (!context) {
    throw new Error("useEnvironment must be used within an EnvironmentProvider");
  }
  return context;
}
