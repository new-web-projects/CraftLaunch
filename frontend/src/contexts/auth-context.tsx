"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { apiClient, getAccessToken, setAccessToken } from "@/lib/api-client";
import { ApiError, type AuthUser } from "@/types/auth";

interface LoginPayload {
  identifier: string;
  password: string;
  remember_me?: boolean;
}

interface RegisterPayload {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  role: "CUSTOMER" | "DEVELOPER";
  first_name?: string;
  last_name?: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<AuthUser>;
  register: (payload: RegisterPayload) => Promise<{ detail: string }>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
  refreshUser: () => Promise<AuthUser | null>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const SESSION_HINT_COOKIE = "craftlaunch_session";

function hasSessionHint(): boolean {
  if (typeof document === "undefined") return false;
  return document.cookie.split("; ").some((c) => c.startsWith(`${SESSION_HINT_COOKIE}=`));
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async (): Promise<AuthUser | null> => {
    try {
      const me = await apiClient.get<AuthUser>("/api/auth/me/");
      setUser(me);
      return me;
    } catch {
      setUser(null);
      setAccessToken(null);
      return null;
    }
  }, []);

  useEffect(() => {
    // Access tokens live in memory only, so a full page reload always
    // starts with none — the non-httpOnly hint cookie tells us whether
    // it's even worth attempting a silent refresh against the real
    // (httpOnly, invisible to this code) refresh cookie.
    async function restoreSession() {
      if (!hasSessionHint()) {
        setIsLoading(false);
        return;
      }
      await refreshUser();
      setIsLoading(false);
    }
    restoreSession();
  }, [refreshUser]);

  const login = useCallback(async (payload: LoginPayload) => {
    const data = await apiClient.post<{ access: string; user: AuthUser }>(
      "/api/auth/login/",
      payload,
      { skipAuthRetry: true }
    );
    setAccessToken(data.access);
    setUser(data.user);
    return data.user;
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    return apiClient.post<{ detail: string }>("/api/auth/register/", payload, {
      skipAuthRetry: true,
    });
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiClient.post("/api/auth/logout/");
    } catch {
      // Clearing local state below is what actually matters for the
      // user's browser; a failed network call shouldn't block that.
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  }, []);

  const logoutAll = useCallback(async () => {
    try {
      await apiClient.post("/api/auth/logout-all/");
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      isAuthenticated: !!user,
      login,
      register,
      logout,
      logoutAll,
      refreshUser,
    }),
    [user, isLoading, login, register, logout, logoutAll, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

export { ApiError };
export { getAccessToken };