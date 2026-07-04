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

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("navixa_access_token");
      localStorage.removeItem("navixa_refresh_token");
      window.location.href = "/login";
    }
    // Both AWS and Azure delegated auth are device-code flows (see
    // app/api/v1/delegated_auth.py) - a 409 delegated_auth_required just
    // means the admin needs to complete sign-in on the Connections page;
    // there's no popup to retry transparently here.
    return Promise.reject(error);
  },
);
