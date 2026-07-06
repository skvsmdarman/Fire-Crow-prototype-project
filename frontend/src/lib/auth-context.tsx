"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  ReactNode,
} from "react";
import { useRouter, usePathname } from "next/navigation";
import { getSessionIdentity, clearSession, subscribeToSession, SessionIdentity } from "./auth-session";
import { request, ApiError } from "./request";
import { AuthUser, PolicyContext } from "./types";
import { SiteHeader, SiteFooter } from "../components/SiteChrome";
import { Card } from "../components/ui/Card";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthState {
  status: AuthStatus;
  identity: SessionIdentity;
  user: AuthUser | null;
  policyContext: PolicyContext | null;
  error: string | null;
}

export interface AuthActions {
  refresh: () => Promise<void>;
  logout: () => void;
  loadPolicyContext: () => Promise<PolicyContext | null>;
  setError: (msg: string | null) => void;
}

const DEFAULT_IDENTITY: SessionIdentity = {
  userId: null,
  username: null,
  workspace: null,
};

const AuthStateCtx = createContext<AuthState>({
  status: "loading",
  identity: DEFAULT_IDENTITY,
  user: null,
  policyContext: null,
  error: null,
});

const AuthActionsCtx = createContext<AuthActions>({
  refresh: async () => {},
  logout: () => {},
  loadPolicyContext: async () => null,
  setError: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [identity, setIdentity] = useState<SessionIdentity>(DEFAULT_IDENTITY);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [policyContext, setPolicyContext] = useState<PolicyContext | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fetchingRef = useRef(false);

  const syncIdentity = useCallback(() => {
    const id = getSessionIdentity();
    setIdentity(id);
    return id;
  }, []);

  const refresh = useCallback(async () => {
    if (fetchingRef.current) return;
    fetchingRef.current = true;
    const id = syncIdentity();
    if (!id.userId) {
      setStatus("unauthenticated");
      setUser(null);
      fetchingRef.current = false;
      return;
    }
    try {
      const me = await request<AuthUser>("/auth/me");
      setUser(me);
      setStatus("authenticated");
    } catch (err) {
      if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
        clearSession();
        setUser(null);
        setStatus("unauthenticated");
      } else {
        setStatus("unauthenticated");
      }
    } finally {
      fetchingRef.current = false;
    }
  }, [syncIdentity]);

  const logout = useCallback(() => {
    clearSession();
    setUser(null);
    setIdentity(DEFAULT_IDENTITY);
    setStatus("unauthenticated");
  }, []);

  const loadPolicyContext = useCallback(async () => {
    try {
      const ctx = await request<PolicyContext>("/auth/policy-context");
      setPolicyContext(ctx);
      return ctx;
    } catch {
      const fallback: PolicyContext = {
        privacy_policy_version: "2026-06-06",
        terms_version: "2026-06-06",
        providers: { github: false, google: false, password: false },
      };
      setPolicyContext(fallback);
      return fallback;
    }
  }, []);

  useEffect(() => {
    let live = true;

    async function checkSession() {
      if (fetchingRef.current) return;
      fetchingRef.current = true;
      try {
        const me = await request<AuthUser>("/auth/me");
        if (!live) return;
        setUser(me);
        setIdentity({
          userId: me.user_id,
          username: me.username,
          workspace: me.username,
        });
        setStatus("authenticated");
      } catch {
        if (!live) return;
        clearSession();
        setUser(null);
        setIdentity({
          userId: null,
          username: null,
          workspace: null,
        });
        setStatus("unauthenticated");
      } finally {
        fetchingRef.current = false;
      }
    }

    void checkSession();
    const unsub = subscribeToSession(() => { void checkSession(); });
    return () => { live = false; unsub(); };
  }, []);

  const state = useMemo<AuthState>(
    () => ({ status, identity, user, policyContext, error }),
    [status, identity, user, policyContext, error],
  );

  const actions = useMemo<AuthActions>(
    () => ({ refresh, logout, loadPolicyContext, setError }),
    [refresh, logout, loadPolicyContext],
  );

  return (
    <AuthStateCtx.Provider value={state}>
      <AuthActionsCtx.Provider value={actions}>
        {children}
      </AuthActionsCtx.Provider>
    </AuthStateCtx.Provider>
  );
}

export function useAuthState(): AuthState {
  return useContext(AuthStateCtx);
}

export function useAuthActions(): AuthActions {
  return useContext(AuthActionsCtx);
}

export function AuthGuard({ children }: { children: ReactNode }) {
  const { status } = useAuthState();
  const router = useRouter();
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted && status === "unauthenticated") {
      router.replace(`/signin?redirect=${encodeURIComponent(pathname)}`);
    }
  }, [mounted, status, router, pathname]);

  if (!mounted || status === "loading" || status === "unauthenticated") {
    return (
      <div className="fc-page" style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
        <SiteHeader ctaHref="/" ctaLabel="Landing Page" />
        <main style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "40px 20px" }}>
          <Card className="fc-panel" style={{ maxWidth: 580, width: "100%", textAlign: "center", padding: 40 }}>
            <div className="fc-brand-mark" style={{ margin: "0 auto 24px auto", fontSize: "1.5rem", fontWeight: "bold", background: "linear-gradient(135deg, var(--red), rgba(255, 95, 109, 0.2))" }}>FC</div>
            <h1 style={{ fontSize: "2rem", marginBottom: 12, background: "linear-gradient(135deg, var(--red), var(--fire))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Initializing Session
            </h1>
            <p className="fc-copy" style={{ color: "var(--text-dim)", marginBottom: 20 }}>
              Connecting to secure auth gateway and synchronizing workspace state...
            </p>
            <div style={{ display: "flex", justifyContent: "center", marginTop: 20 }}>
              <span style={{ border: "3px solid rgba(255,255,255,0.1)", borderTop: "3px solid var(--fire)", borderRadius: "50%", width: "24px", height: "24px", display: "inline-block", animation: "spin 1s linear infinite" }} />
            </div>
          </Card>
        </main>
        <SiteFooter />
      </div>
    );
  }

  return <>{children}</>;
}

export function GuestGuard({ children }: { children: ReactNode }) {
  const { status } = useAuthState();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  useEffect(() => {
    if (mounted && status === "authenticated") {
      router.replace("/dashboard");
    }
  }, [mounted, status, router]);

  if (!mounted || status === "loading" || status === "authenticated") {
    return (
      <div className="fc-page" style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
        <SiteHeader ctaHref="/" ctaLabel="Landing Page" />
        <main style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", padding: "40px 20px" }}>
          <Card className="fc-panel" style={{ maxWidth: 580, width: "100%", textAlign: "center", padding: 40 }}>
            <div className="fc-brand-mark" style={{ margin: "0 auto 24px auto", fontSize: "1.5rem", fontWeight: "bold", background: "linear-gradient(135deg, var(--red), rgba(255, 95, 109, 0.2))" }}>FC</div>
            <h1 style={{ fontSize: "2rem", marginBottom: 12, background: "linear-gradient(135deg, var(--red), var(--fire))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Initializing Session
            </h1>
            <p className="fc-copy" style={{ color: "var(--text-dim)", marginBottom: 20 }}>
              Connecting to secure auth gateway and synchronizing workspace state...
            </p>
            <div style={{ display: "flex", justifyContent: "center", marginTop: 20 }}>
              <span style={{ border: "3px solid rgba(255,255,255,0.1)", borderTop: "3px solid var(--fire)", borderRadius: "50%", width: "24px", height: "24px", display: "inline-block", animation: "spin 1s linear infinite" }} />
            </div>
          </Card>
        </main>
        <SiteFooter />
      </div>
    );
  }

  return <>{children}</>;
}
