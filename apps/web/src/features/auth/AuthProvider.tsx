import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import type { UserResponse, LoginRequest, RegisterRequest } from "../../lib/api/types";
import { ApiClient, ApiError } from "../../lib/api/client";

interface AuthState {
  user: UserResponse | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
}

interface AuthContextValue extends AuthState {
  login: (account: string, password: string) => Promise<void>;
  register: (email: string, password: string, inviteCode: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function loadStoredToken(): string | null {
  try {
    return sessionStorage.getItem("vsl_token");
  } catch {
    return null;
  }
}

function storeToken(token: string | null) {
  try {
    if (token) {
      sessionStorage.setItem("vsl_token", token);
    } else {
      sessionStorage.removeItem("vsl_token");
    }
  } catch {
    // ignore
  }
}

export function AuthProvider({
  children,
  apiClient,
}: {
  children: ReactNode;
  apiClient: ApiClient;
}) {
  const [state, setState] = useState<AuthState>(() => {
    const token = loadStoredToken();
    return { user: null, token, isLoading: false, error: null };
  });

  const clearError = useCallback(() => {
    setState((s) => ({ ...s, error: null }));
  }, []);

  const login = useCallback(
    async (account: string, password: string) => {
      setState((s) => ({ ...s, isLoading: true, error: null }));
      try {
        const tokenRes = await apiClient.login({ email: account, password });
        const token = tokenRes.accessToken;
        storeToken(token);
        const user = await apiClient.getCurrentUser();
        setState({ user, token, isLoading: false, error: null });
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : "登录失败，请重试";
        setState((s) => ({ ...s, isLoading: false, error: message }));
      }
    },
    [apiClient],
  );

  const register = useCallback(
    async (email: string, password: string, inviteCode: string) => {
      setState((s) => ({ ...s, isLoading: true, error: null }));
      try {
        const tokenRes = await apiClient.register({ email, password, inviteCode });
        const token = tokenRes.accessToken;
        storeToken(token);
        const user = await apiClient.getCurrentUser();
        setState({ user, token, isLoading: false, error: null });
      } catch (err) {
        let message = "注册失败，请重试";
        if (err instanceof ApiError) {
          if (err.status === 400 || err.status === 422) {
            message = "邀请码无效或已使用，请检查后重试";
          } else {
            message = err.message;
          }
        }
        setState((s) => ({ ...s, isLoading: false, error: message }));
      }
    },
    [apiClient],
  );

  const logout = useCallback(() => {
    storeToken(null);
    setState({ user: null, token: null, isLoading: false, error: null });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout, clearError }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
