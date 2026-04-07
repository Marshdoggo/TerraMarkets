function resolveApiBaseUrl() {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }

  if (typeof window !== "undefined") {
    const protocol = window.location.protocol || "http:";
    const hostname = window.location.hostname || "localhost";
    return `${protocol}//${hostname}:8000`;
  }

  return "http://localhost:8000";
}

export function getApiBaseUrl() {
  return resolveApiBaseUrl();
}

export function getAccessToken() {
  if (typeof window === "undefined") {
    return null;
  }
  return localStorage.getItem("accessToken");
}

export function getRefreshToken() {
  if (typeof window === "undefined") {
    return null;
  }
  return localStorage.getItem("refreshToken");
}

export function setTokens({ access_token, refresh_token }) {
  localStorage.setItem("accessToken", access_token);
  localStorage.setItem("refreshToken", refresh_token);
}

export function clearTokens() {
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
}

export async function logoutSession() {
  try {
    await request("/auth/logout", { method: "POST" }, false);
  } catch {
    // Local logout should still succeed even if the server session is already stale.
  } finally {
    clearTokens();
  }
}

let refreshPromise = null;

async function refreshAccessToken() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error("No refresh token available");
  }
  if (!refreshPromise) {
    refreshPromise = fetch(
      `${resolveApiBaseUrl()}/auth/refresh?refresh_token=${encodeURIComponent(refreshToken)}`,
      { method: "POST" }
    )
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("Session refresh failed");
        }
        return response.json();
      })
      .then((tokens) => {
        setTokens(tokens);
        return tokens.access_token;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

async function request(path, options = {}, retry = true) {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const token = getAccessToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${resolveApiBaseUrl()}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && retry && getRefreshToken()) {
    try {
      const nextToken = await refreshAccessToken();
      headers.set("Authorization", `Bearer ${nextToken}`);
      return request(path, { ...options, headers }, false);
    } catch {
      clearTokens();
      throw new Error("Your session expired. Please log in again.");
    }
  }

  if (!response.ok) {
    let message = "Request failed";
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export function apiGet(path) {
  return request(path);
}

export function apiPost(path, body, options = {}) {
  return request(path, {
    method: "POST",
    body: typeof body === "string" ? body : JSON.stringify(body),
    ...options,
  });
}
