import api from "./api";

function storeTokens(data) {
  localStorage.setItem("token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  return data;
}

export async function register(payload) {
  const { data } = await api.post("/auth/register", payload);
  return storeTokens(data);
}

export async function login(payload) {
  const { data } = await api.post("/auth/login", payload);
  return storeTokens(data);
}

export async function fetchCurrentUser() {
  const { data } = await api.get("/auth/me");
  return data;
}

export async function logout() {
  const refreshToken = getRefreshToken();
  if (refreshToken) {
    try {
      await api.post("/auth/logout", { refresh_token: refreshToken });
    } catch {
      // Best-effort — if the network is down, still clear local state below
      // so the user is logged out client-side regardless.
    }
  }
  localStorage.removeItem("token");
  localStorage.removeItem("refresh_token");
}

export function getToken() {
  return localStorage.getItem("token");
}

export function getRefreshToken() {
  return localStorage.getItem("refresh_token");
}

export function setAccessToken(token) {
  localStorage.setItem("token", token);
}
