/**
 * Authentication context — dev mode uses simple token auth (no Keycloak needed).
 * Production mode uses Keycloak OIDC.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  role: "admin" | "owner" | "viewer";
  is_active: boolean;
}

interface AuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
  user: UserProfile | null;
  token: string | null;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

const API_BASE = "/api/v1";
const DEV_USERS = ["alice", "bob", "carol", "admin"] as const;
type DevUser = typeof DEV_USERS[number];

// Store token in memory only — never localStorage
let _memoryToken: string | null = null;

export function getMemoryToken(): string | null {
  return _memoryToken;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  // Which dev user is selected — stored in sessionStorage (cleared on tab close)
  const [devUser, setDevUser] = useState<DevUser | null>(
    () => (sessionStorage.getItem("dev_user") as DevUser | null)
  );

  const logout = useCallback(() => {
    queryClient.clear();
    _memoryToken = null;
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
    sessionStorage.removeItem("dev_user");
    setDevUser(null);
  }, [queryClient]);

  async function loginAs(username: DevUser) {
    setIsLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/auth/dev/token/${username}`);
      const data = await resp.json();
      const t = data.access_token;
      _memoryToken = t;
      setToken(t);

      // Provision and get profile
      await fetch(`${API_BASE}/auth/provision`, {
        method: "POST",
        headers: { Authorization: `Bearer ${t}` },
      });
      const profileResp = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      const profile = await profileResp.json();
      setUser(profile);
      setIsAuthenticated(true);
      sessionStorage.setItem("dev_user", username);
      setDevUser(username);
    } catch (err) {
      console.error("Login failed", err);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (devUser) {
      loginAs(devUser);
    } else {
      setIsLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Show login picker if not authenticated
  if (!isLoading && !isAuthenticated) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-6 bg-background">
        <div className="flex items-center gap-3">
          <svg className="h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
          <span className="text-2xl font-bold">TrustVault</span>
        </div>
        <div className="rounded-lg border bg-card p-8 shadow-sm w-80">
          <h2 className="text-lg font-semibold mb-1">Development Login</h2>
          <p className="text-sm text-muted-foreground mb-6">Select a demo account to sign in</p>
          <div className="space-y-2">
            {[
              { u: "admin" as DevUser,  label: "Admin",        desc: "See audit log, manage users",     color: "text-red-600" },
              { u: "alice" as DevUser,  label: "Alice (Owner)", desc: "Upload and manage documents",    color: "text-blue-600" },
              { u: "bob" as DevUser,    label: "Bob (Viewer)",  desc: "Has access to shared docs",      color: "text-green-600" },
              { u: "carol" as DevUser,  label: "Carol (Viewer)", desc: "No document access",           color: "text-gray-600" },
            ].map(({ u, label, desc, color }) => (
              <button
                key={u}
                onClick={() => loginAs(u)}
                className="w-full rounded-md border p-3 text-left hover:bg-accent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <div className={`text-sm font-medium ${color}`}>{label}</div>
                <div className="text-xs text-muted-foreground">{desc}</div>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ isLoading, isAuthenticated, user, token, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
