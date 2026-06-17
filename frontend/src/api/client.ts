import { API } from "../config";

export const API_KEY_STORAGE_KEY = "graphify_cockpit_api_key";
export const API_AUTH_ERROR_MESSAGE = "API key required or invalid.";

export function getStoredApiKey(): string {
  try {
    return localStorage.getItem(API_KEY_STORAGE_KEY)?.trim() ?? "";
  } catch {
    return "";
  }
}

export function setStoredApiKey(value: string): void {
  const key = value.trim();
  if (!key) {
    clearStoredApiKey();
    return;
  }
  try {
    localStorage.setItem(API_KEY_STORAGE_KEY, key);
  } catch {
    // Restricted browser storage should not break the rest of the UI.
  }
}

export function clearStoredApiKey(): void {
  try {
    localStorage.removeItem(API_KEY_STORAGE_KEY);
  } catch {
    // Restricted browser storage should not break the rest of the UI.
  }
}

function endpoint(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  return `${API}${path.startsWith("/") ? path : `/${path}`}`;
}

function withApiKey(headers?: HeadersInit): Headers {
  const next = new Headers(headers);
  const key = getStoredApiKey();
  if (key && !next.has("X-API-Key") && !next.has("Authorization")) {
    next.set("X-API-Key", key);
  }
  return next;
}

export function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  return fetch(endpoint(path), {
    ...options,
    headers: withApiKey(options.headers),
  });
}

function detailMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    const body = detail as { code?: unknown; message?: unknown };
    const message = typeof body.message === "string" ? body.message : fallback;
    return typeof body.code === "string" ? `${body.code}: ${message}` : message;
  }
  return fallback;
}

export async function apiErrorMessage(response: Response, fallback?: string): Promise<string> {
  if (response.status === 401 || response.status === 403) {
    return API_AUTH_ERROR_MESSAGE;
  }

  const base = fallback ?? (response.statusText || `HTTP ${response.status}`);
  try {
    const body = await response.clone().json() as { detail?: unknown };
    return detailMessage(body.detail, base);
  } catch {
    return base;
  }
}
