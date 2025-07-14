import axios from "axios";
import { getBackendBaseUrl } from "@/utils";

// Token duration in milliseconds (e.g., 24 hours)
export const TOKEN_DURATION = 24 * 60 * 60 * 1000;

const baseUrl = await getBackendBaseUrl();
const api = axios.create({
  baseURL: baseUrl,
  timeout: 30000,
  headers: {},
});

// Helper to check if token is expired
const isTokenExpired = () => {
  const expiration = localStorage.getItem("tokenExpiration");
  if (!expiration) return true;
  return new Date().getTime() > parseInt(expiration, 10); // Parse string back to number
};

// Add interceptor to add token to requests
api.interceptors.request.use((config) => {
  // Do not require the Authorization token for login. In addition, login requires a
  // specific content type
  if (config.url === "/api/v1/token") {
    config.headers["Content-Type"] = "application/x-www-form-urlencoded";
    return config;
  }

  // For sign-up, do not require the Authorization token
  else if (config.url == "/api/v1/signup" && config.method == "post") {
    return config;
  }

  // If the token is expired, throw an error. We handle this error in the components
  // that call the API.
  else if (isTokenExpired()) {
    localStorage.removeItem("authToken");
    localStorage.removeItem("tokenType");
    localStorage.removeItem("tokenExpiration");
    throw new Error("Token expired");
  }
  const tokenType = localStorage.getItem("tokenType");
  const authToken = localStorage.getItem("authToken");
  if (tokenType && authToken) {
    config.headers.Authorization = `${tokenType[0].toUpperCase() + tokenType.substring(1, tokenType.length)} ${authToken}`;
  }
  return config;
});

export default api;
