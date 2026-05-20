import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
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

  it("shows '生成异常' and retry button for failed_internal status", () => {
    const onRetry = vi.fn();
    render(<GenerationStatusIndicator status="failed_internal" onRetry={onRetry} />);
    expect(screen.getByText("生成异常")).toBeInTheDocument();
    expect(screen.getByText("重试")).toBeInTheDocument();
  });

  it("shows '生成超时，请重试' when isStale and polling status", () => {
    const onRetry = vi.fn();
    render(<GenerationStatusIndicator status="running" isStale onRetry={onRetry} />);
    expect(screen.getByText("生成超时，请重试")).toBeInTheDocument();
    expect(screen.getByText("重试")).toBeInTheDocument();
  });

  it("does not show stale message when isStale but status is not polling", () => {
    render(<GenerationStatusIndicator status="completed" isStale />);
    expect(screen.queryByText("生成超时，请重试")).not.toBeInTheDocument();
    expect(screen.getByText("生成通过")).toBeInTheDocument();
  });

  it("calls onRetry when retry button is clicked", async () => {
    const onRetry = vi.fn();
    render(<GenerationStatusIndicator status="failed_internal" onRetry={onRetry} />);
    fireEvent.click(screen.getByText("重试"));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("does not show retry button for failed_internal without onRetry", () => {
    render(<GenerationStatusIndicator status="failed_internal" />);
    expect(screen.queryByText("重试")).not.toBeInTheDocument();
  });
});
