import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "../App";

describe("App shell", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("renders login page when not authenticated", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "登录 WordFlow" })).toBeInTheDocument();
  });

  it("renders the main app when a stored token exists", async () => {
    sessionStorage.setItem("vsl_token", "stored-token");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    render(<App />);

    expect(await screen.findByText("选择一个故事，或新建故事开始按章节记忆单词。")).toBeInTheDocument();
  });
});
