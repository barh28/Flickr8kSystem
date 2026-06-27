// Thin fetch wrapper around the gateway: builds the URL, attaches the bearer
// token, normalizes errors, and signals global 401s so the app can log out.
import { clearAuth, getToken } from "../auth/storage";
import { API_BASE_URL } from "../config";

export const UNAUTHORIZED_EVENT = "auth:unauthorized";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// Best-effort human-readable message from any thrown error (ApiError, network
// failure, etc.), used by the global toast handlers.
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message || "Something went wrong.";
  return "Something went wrong.";
}

export type QueryValue = string | number | boolean | undefined | null | string[];

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  params?: Record<string, QueryValue>;
  auth?: boolean; // attach the bearer token (default true)
}

function buildUrl(path: string, params?: Record<string, QueryValue>): string {
  const url = new URL(path, API_BASE_URL);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null) continue;
      if (Array.isArray(value)) {
        for (const item of value) url.searchParams.append(key, item);
      } else {
        url.searchParams.append(key, String(value));
      }
    }
  }
  return url.toString();
}

async function extractMessage(response: Response): Promise<string> {
  try {
    const data = await response.json();
    const message = data?.error?.message;
    if (typeof message === "string") return message;
    if (message) return JSON.stringify(message);
  } catch {
    // not JSON; fall through
  }
  return response.statusText || "Request failed";
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, params, auth = true } = options;

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(buildUrl(path, params), {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401) {
    clearAuth();
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }

  if (!response.ok) {
    throw new ApiError(response.status, await extractMessage(response));
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
