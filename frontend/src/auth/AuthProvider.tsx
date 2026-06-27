import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import * as authApi from "../api/auth";
import { UNAUTHORIZED_EVENT } from "../api/client";
import type { AuthUser } from "../types";
import { AuthContext } from "./context";
import type { AuthContextValue } from "./context";
import { clearAuth, loadAuth, saveAuth } from "./storage";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => loadAuth()?.user ?? null);

  // If any request gets a 401, the client clears storage and fires this event.
  useEffect(() => {
    const handle = () => setUser(null);
    window.addEventListener(UNAUTHORIZED_EVENT, handle);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handle);
  }, []);

  const value = useMemo<AuthContextValue>(() => {
    async function login(username: string, password: string) {
      const res = await authApi.login(username, password);
      saveAuth(res);
      setUser({ user_id: res.user_id, username: res.username });
    }
    async function register(username: string, password: string) {
      const res = await authApi.register(username, password);
      saveAuth(res);
      setUser({ user_id: res.user_id, username: res.username });
    }
    function logout() {
      clearAuth();
      setUser(null);
    }
    return { user, isAuthenticated: user !== null, login, register, logout };
  }, [user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
