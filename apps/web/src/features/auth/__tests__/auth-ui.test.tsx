import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AuthProvider } from "../AuthProvider";
import { LoginPage } from "../LoginPage";
import { RegisterPage } from "../RegisterPage";
import { ProtectedRoute } from "../ProtectedRoute";
import { ApiClient, ApiError } from "../../../lib/api/client";

function createMockClient(): ApiClient {
  return {
    login: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
  } as unknown as ApiClient;
}

function renderWithAuth(ui: React.ReactElement, client: ApiClient) {
  return render(<AuthProvider apiClient={client}>{ui}</AuthProvider>);
}

describe("LoginPage", () => {
  let mockClient: ApiClient;
  beforeEach(() => { mockClient = createMockClient(); });

  it("renders account and password inputs with visible labels", () => {
    renderWithAuth(<LoginPage />, mockClient);
    expect(screen.getByLabelText("账号/邮箱")).toBeInTheDocument();
    expect(screen.getByLabelText("密码")).toBeInTheDocument();
  });

  it("renders login button", () => {
    renderWithAuth(<LoginPage />, mockClient);
    expect(screen.getByRole("button", { name: /登录/ })).toBeInTheDocument();
  });

  it("has link to register page", () => {
    renderWithAuth(<LoginPage />, mockClient);
    expect(screen.getByText("注册").closest("a")).toHaveAttribute("href", "/register");
  });

  it("shows error on failed login", async () => {
    (mockClient.login as ReturnType<typeof vi.fn>).mockRejectedValue(
      new ApiError(401, null, "Invalid credentials"),
    );
    renderWithAuth(<LoginPage />, mockClient);
    fireEvent.change(screen.getByLabelText("账号/邮箱"), { target: { value: "test@test.com" } });
    fireEvent.change(screen.getByLabelText("密码"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: /登录/ }));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });
});

describe("RegisterPage", () => {
  let mockClient: ApiClient;
  beforeEach(() => { mockClient = createMockClient(); });

  it("renders email, password and invite code inputs with visible labels", () => {
    renderWithAuth(<RegisterPage />, mockClient);
    expect(screen.getByLabelText("邮箱")).toBeInTheDocument();
    expect(screen.getByLabelText("密码")).toBeInTheDocument();
    expect(screen.getByLabelText("邀请码")).toBeInTheDocument();
  });

  it("renders register button", () => {
    renderWithAuth(<RegisterPage />, mockClient);
    expect(screen.getByRole("button", { name: /注册/ })).toBeInTheDocument();
  });

  it("shows clear error for invalid invite code", async () => {
    (mockClient.register as ReturnType<typeof vi.fn>).mockRejectedValue(
      new ApiError(400, null, "Invalid invite code"),
    );
    renderWithAuth(<RegisterPage />, mockClient);
    fireEvent.change(screen.getByLabelText("邮箱"), { target: { value: "test@test.com" } });
    fireEvent.change(screen.getByLabelText("密码"), { target: { value: "password123" } });
    fireEvent.change(screen.getByLabelText("邀请码"), { target: { value: "BAD" } });
    fireEvent.click(screen.getByRole("button", { name: /注册/ }));
    await waitFor(() => {
      const alert = screen.getByRole("alert");
      expect(alert.textContent).toContain("邀请码无效");
    });
  });

  it("has link to login page", () => {
    renderWithAuth(<RegisterPage />, mockClient);
    expect(screen.getByText("登录").closest("a")).toHaveAttribute("href", "/login");
  });
});

describe("ProtectedRoute", () => {
  it("redirects to login when not authenticated", () => {
    const mockClient = createMockClient();
    renderWithAuth(
      <ProtectedRoute><div>Protected content</div></ProtectedRoute>,
      mockClient,
    );
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
    expect(screen.getByText("请先登录后继续")).toBeInTheDocument();
    expect(screen.getByText("前往登录")).toBeInTheDocument();
  });
});
