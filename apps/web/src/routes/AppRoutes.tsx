import { AuthProvider, useAuth } from "../features/auth/AuthProvider";
import { LoginPage } from "../features/auth/LoginPage";
import { RegisterPage } from "../features/auth/RegisterPage";
import { ProtectedRoute } from "../features/auth/ProtectedRoute";
import { apiClient } from "../lib/api/client";

function MainApp() {
  return (
    <ProtectedRoute>
      <div className="app-main-content">
        <p className="text-body">选择一个故事，或新建故事开始按章节记忆单词。</p>
      </div>
    </ProtectedRoute>
  );
}

export function AppRoutes({ currentPath }: { currentPath?: string }) {
  const path = currentPath ?? (typeof window !== "undefined" ? window.location.pathname : "/");

  return (
    <AuthProvider apiClient={apiClient}>
      {path === "/register" ? <RegisterPage /> : path === "/login" ? <LoginPage /> : <MainApp />}
    </AuthProvider>
  );
}
