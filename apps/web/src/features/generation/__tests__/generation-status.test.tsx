import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { GenerationStatusIndicator } from "../GenerationStatusIndicator";

describe("GenerationStatusIndicator", () => {
  it("shows queued status", () => {
    render(<GenerationStatusIndicator status="queued" />);
    expect(screen.getByText("排队中")).toBeInTheDocument();
  });

  it("shows running status", () => {
    render(<GenerationStatusIndicator status="running" />);
    expect(screen.getByText("生成中")).toBeInTheDocument();
  });

  it("shows reviewing status", () => {
    render(<GenerationStatusIndicator status="reviewing" />);
    expect(screen.getByText("质检中")).toBeInTheDocument();
  });

  it("shows retrying status", () => {
    render(<GenerationStatusIndicator status="retrying" />);
    expect(screen.getByText("重新生成中")).toBeInTheDocument();
  });

  it("shows completed status", () => {
    render(<GenerationStatusIndicator status="completed" />);
    expect(screen.getByText("生成通过")).toBeInTheDocument();
  });

  it("shows fallback_completed with correct message", () => {
    render(<GenerationStatusIndicator status="fallback_completed" />);
    expect(screen.getByText("已标注少量超纲词")).toBeInTheDocument();
  });

  it("does not show '失败' for fallback_completed", () => {
    render(<GenerationStatusIndicator status="fallback_completed" />);
    const el = screen.getByText("已标注少量超纲词");
    expect(el.textContent).not.toContain("失败");
  });

  it("shows retry count when retrying", () => {
    render(<GenerationStatusIndicator status="retrying" retryCount={2} />);
    expect(screen.getByText(/第 2 次重试/)).toBeInTheDocument();
  });

  it("does not show retry count when not retrying", () => {
    render(<GenerationStatusIndicator status="running" retryCount={1} />);
    expect(screen.queryByText(/重试/)).not.toBeInTheDocument();
  });

  it("has aria-live for accessibility", () => {
    render(<GenerationStatusIndicator status="running" />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
