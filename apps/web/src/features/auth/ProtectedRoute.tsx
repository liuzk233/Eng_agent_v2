import type { ReactNode } from "react";
import { useAuth } from "./AuthProvider";
import "./auth.css";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { token } = useAuth();

  if (!token) {
    return (
      <div className="auth-redirect">
        <p>请先登录后继续</p>
        <a href="/login" className="auth-redirect-link">前往登录</a>
      </div>
    );
  }

  return <>{children}</>;
}
