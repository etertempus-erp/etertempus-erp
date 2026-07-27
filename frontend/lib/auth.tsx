"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { apiGet, apiPost, AuthenticatedUser } from "@/lib/api";
import { friendlyErrorMessage } from "@/lib/messages";

type AuthContextValue = {
  user: AuthenticatedUser | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  canWrite: boolean;
  isAdmin: boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isLoginPage = pathname === "/login";

  async function refreshSession() {
    try {
      setError(null);
      const current = await apiGet<AuthenticatedUser>("/auth/me");
      setUser(current);
      if (isLoginPage) router.replace("/");
    } catch (err) {
      setUser(null);
      if (!isLoginPage) router.replace("/login");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshSession();
  }, [pathname]);

  async function login(email: string, password: string) {
    try {
      setError(null);
      const response = await apiPost<{ user: AuthenticatedUser }>("/auth/login", { email, password });
      setUser(response.user);
      router.replace("/");
    } catch (err) {
      setError(friendlyErrorMessage(err, "No se pudo iniciar sesion."));
      throw err;
    }
  }

  async function logout() {
    await apiPost("/auth/logout", {});
    setUser(null);
    router.replace("/login");
  }

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      error,
      login,
      logout,
      canWrite: user?.role === "admin" || user?.role === "operator",
      isAdmin: user?.role === "admin",
    }),
    [user, loading, error],
  );

  if (loading && !isLoginPage) {
    return <div className="auth-loading">Validando sesion...</div>;
  }

  if (!loading && !user && !isLoginPage) {
    return <div className="auth-loading">Redirigiendo al inicio de sesion...</div>;
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth debe usarse dentro de AuthProvider.");
  return context;
}
