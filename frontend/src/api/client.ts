import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("navixa_access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Waits for the delegated-auth popup (app/api/v1/delegated_auth.py) to
 * finish and postMessage back { type: "navixa-sso-complete", success }.
 * Resolves true/false; never rejects (a closed-without-completing popup
 * resolves false so the caller can show a normal error instead of hanging).
 */
function waitForPopupCompletion(popup: Window): Promise<boolean> {
  return new Promise((resolve) => {
    function cleanup() {
      window.removeEventListener("message", onMessage);
      clearInterval(closedCheck);
    }
    function onMessage(event: MessageEvent) {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type !== "navixa-sso-complete") return;
      cleanup();
      resolve(Boolean(event.data.success));
    }
    const closedCheck = setInterval(() => {
      if (popup.closed) {
        cleanup();
        resolve(false);
      }
    }, 500);
    window.addEventListener("message", onMessage);
  });
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("navixa_access_token");
      localStorage.removeItem("navixa_refresh_token");
      window.location.href = "/login";
      return Promise.reject(error);
    }

    const detail = error.response?.data?.detail;
    const config = error.config as (typeof error.config & { _delegatedAuthRetried?: boolean }) | undefined;
    if (
      error.response?.status === 409 &&
      detail?.code === "delegated_auth_required" &&
      config &&
      !config._delegatedAuthRetried
    ) {
      const popup = window.open(
        `${API_BASE_URL}${detail.start_url}`,
        "navixa-sso",
        "width=520,height=680",
      );
      if (popup) {
        const success = await waitForPopupCompletion(popup);
        if (success) {
          config._delegatedAuthRetried = true;
          return apiClient.request(config);
        }
      }
    }

    return Promise.reject(error);
  },
);
