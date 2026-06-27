// Auth endpoints (public — no token required).
import type { AuthResponse } from "../types";
import { api } from "./client";

export function register(username: string, password: string): Promise<AuthResponse> {
  return api<AuthResponse>("/api/users/create", {
    method: "POST",
    body: { username, password },
    auth: false,
  });
}

export function login(username: string, password: string): Promise<AuthResponse> {
  return api<AuthResponse>("/api/users/login", {
    method: "POST",
    body: { username, password },
    auth: false,
  });
}
