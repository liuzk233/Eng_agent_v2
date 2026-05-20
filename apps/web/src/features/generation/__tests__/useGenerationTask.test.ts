// @vitest-environment jsdom

import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";
import { useGenerationTask } from "../useGenerationTask";
import type { ApiClient } from "../../../lib/api/client";
import type { GenerationTaskResponse } from "../../../lib/api/types";

function makeTask(overrides: Partial<GenerationTaskResponse> = {}): GenerationTaskResponse {
  return {
    id: "task-1",
    chapterId: "chapter-1",
    status: "running",
    retryCount: 0,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}

function makeClient(task: GenerationTaskResponse | null) {
  return {
    getGenerationTask: vi.fn().mockResolvedValue(task),
  } as unknown as ApiClient;
}

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("useGenerationTask", () => {
  it("returns task data when taskId is provided", async () => {
    const task = makeTask();
    const client = makeClient(task);

    const { result } = renderHook(() => useGenerationTask(client, "task-1"), { wrapper });

    await waitFor(() => {
      expect(result.current.task).not.toBeNull();
    });

    expect(result.current.task!.id).toBe("task-1");
    expect(result.current.task!.status).toBe("running");
  });

  it("returns null task when taskId is null", () => {
    const client = makeClient(null);

    const { result } = renderHook(() => useGenerationTask(client, null), { wrapper });

    expect(result.current.task).toBeNull();
  });

  it("isPolling is true for queued status", async () => {
    const task = makeTask({ status: "queued" });
    const client = makeClient(task);

    const { result } = renderHook(() => useGenerationTask(client, "task-1"), { wrapper });

    await waitFor(() => {
      expect(result.current.isPolling).toBe(true);
    });
  });

  it("isPolling is true for running status", async () => {
    const task = makeTask({ status: "running" });
    const client = makeClient(task);

    const { result } = renderHook(() => useGenerationTask(client, "task-1"), { wrapper });

    await waitFor(() => {
      expect(result.current.isPolling).toBe(true);
    });
  });

  it("isPolling is false for completed status", async () => {
    const task = makeTask({ status: "completed" });
    const client = makeClient(task);

    const { result } = renderHook(() => useGenerationTask(client, "task-1"), { wrapper });

    await waitFor(() => {
      expect(result.current.isPolling).toBe(false);
    });
  });

  it("isTerminal is true for completed status", async () => {
    const task = makeTask({ status: "completed" });
    const client = makeClient(task);

    const { result } = renderHook(() => useGenerationTask(client, "task-1"), { wrapper });

    await waitFor(() => {
      expect(result.current.isTerminal).toBe(true);
    });
  });

  it("isTerminal is true for failed_internal status", async () => {
    const task = makeTask({ status: "failed_internal" });
    const client = makeClient(task);

    const { result } = renderHook(() => useGenerationTask(client, "task-1"), { wrapper });

    await waitFor(() => {
      expect(result.current.isTerminal).toBe(true);
    });
  });

  it("isStale is true when task is polling and createdAt exceeds threshold", async () => {
    const oldTime = new Date(Date.now() - 600_000).toISOString(); // 10 minutes ago
    const task = makeTask({ status: "running", createdAt: oldTime });
    const client = makeClient(task);

    const { result } = renderHook(() => useGenerationTask(client, "task-1"), { wrapper });

    await waitFor(() => {
      expect(result.current.isStale).toBe(true);
    });
  });

  it("isStale is false when task is polling and createdAt is within threshold", async () => {
    const recentTime = new Date(Date.now() - 60_000).toISOString(); // 1 minute ago
    const task = makeTask({ status: "running", createdAt: recentTime });
    const client = makeClient(task);

    const { result } = renderHook(() => useGenerationTask(client, "task-1"), { wrapper });

    await waitFor(() => {
      expect(result.current.task).not.toBeNull();
    });

    expect(result.current.isStale).toBe(false);
  });

  it("isStale is false when task is in terminal status even if old", async () => {
    const oldTime = new Date(Date.now() - 600_000).toISOString(); // 10 minutes ago
    const task = makeTask({ status: "completed", createdAt: oldTime });
    const client = makeClient(task);

    const { result } = renderHook(() => useGenerationTask(client, "task-1"), { wrapper });

    await waitFor(() => {
      expect(result.current.task).not.toBeNull();
    });

    expect(result.current.isStale).toBe(false);
  });
});
