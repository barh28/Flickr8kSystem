// Persists the auth session (token + user) in localStorage. Plain module (no
// React) so both the API client and the AuthContext can use it.
import type { AuthResponse, AuthUser } from "../types";

const STORAGE_KEY = "flickr8k.auth";

export interface StoredAuth {
  token: string;
  user: AuthUser;
}

export function loadAuth(): StoredAuth | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredAuth;
  } catch {
    return null;
  }
}

export function saveAuth(auth: AuthResponse): StoredAuth {
  const stored: StoredAuth = {
    token: auth.token,
    user: { user_id: auth.user_id, username: auth.username },
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  return stored;
}

export function clearAuth(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export function getToken(): string | null {
  return loadAuth()?.token ?? null;
}
