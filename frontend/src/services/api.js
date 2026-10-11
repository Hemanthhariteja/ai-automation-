import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

const api = axios.create({ baseURL, timeout: 15000 });

// Access tokens are short-lived (30 min) by design — this is what makes
// that safe without logging the user out constantly: a 401 triggers one
// silent refresh-and-retry before falling back to a real logout.
let refreshPromise = null;

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) return null;

  if (!refreshPromise) {
    // Share one in-flight refresh across concurrent 401s instead of firing
    // a separate refresh call per failed request.
    refreshPromise = axios
      .post(`${baseURL}/auth/refresh`, { refresh_token: refreshToken })
      .then((res) => res.data.access_token)
      .catch(() => null)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

function forceLogout() {
  localStorage.removeItem("token");
  localStorage.removeItem("refresh_token");
  if (!window.location.pathname.startsWith("/login")) {
    window.location.href = "/login";
  }
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;
    const isAuthEndpoint = config?.url?.startsWith("/auth/");

    if (response?.status === 401 && !isAuthEndpoint && !config._retried) {
      const newAccessToken = await refreshAccessToken();
      if (newAccessToken) {
        localStorage.setItem("token", newAccessToken);
        config._retried = true;
        config.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(config);
      }
      forceLogout();
    }

    return Promise.reject(error);
  }
);

export default api;
