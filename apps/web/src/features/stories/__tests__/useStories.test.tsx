// @vitest-environment jsdom

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { createElement } from "react";
import { describe, expect, it, vi } from "vitest";
import type { ApiClient } from "../../../lib/api/client";
import type { StoryProjectResponse } from "../../../lib/api/types";
import { useStories } from "../useStories";

function makeStory(overrides: Partial<StoryProjectResponse> = {}): StoryProjectResponse {
  return {
    id: "story-1",
    title: "Original title",
    style: "web_novel",
    targetChapterCount: 3,
    currentChapterNumber: 1,
    createdAt: "2026-05-20T00:00:00.000Z",
    updatedAt: "2026-05-20T00:00:00.000Z",
    ...overrides,
  };
}

function makeClient(
  stories: StoryProjectResponse[],
  renamedStory: StoryProjectResponse,
  deleteStoryProject = vi.fn().mockResolvedValue(undefined),
) {
  return {
    listStoryProjects: vi.fn().mockResolvedValue(stories),
    renameStoryProject: vi.fn().mockResolvedValue(renamedStory),
    deleteStoryProject,
  } as unknown as ApiClient;
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  function wrapper({ children }: { children: React.ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  }

  return { queryClient, wrapper };
}

describe("useStories", () => {
  it("renames a story through the API client and synchronizes the storyProjects cache", async () => {
    const originalStory = makeStory();
    const otherStory = makeStory({ id: "story-2", title: "Other title" });
    const renamedStory = makeStory({
      title: "Renamed title",
      updatedAt: "2026-05-25T04:30:00.000Z",
    });
    const client = makeClient([originalStory, otherStory], renamedStory);
    const { queryClient, wrapper } = createWrapper();

    const { result } = renderHook(() => useStories(client), { wrapper });

    await waitFor(() => {
      expect(result.current.stories).toHaveLength(2);
    });

    await act(async () => {
      await result.current.renameStory("story-1", "Renamed title");
    });

    expect(client.renameStoryProject).toHaveBeenCalledWith("story-1", {
      title: "Renamed title",
    });
    expect(queryClient.getQueryData<StoryProjectResponse[]>(["storyProjects"])).toEqual([
      renamedStory,
      otherStory,
    ]);
    await waitFor(() => {
      expect(result.current.stories[0]).toMatchObject({
        id: "story-1",
        title: "Renamed title",
        updatedAt: "2026-05-25T04:30:00.000Z",
      });
    });
  });

  it("deletes a story through the API client and removes it from the storyProjects cache", async () => {
    const deletedStory = makeStory();
    const remainingStory = makeStory({ id: "story-2", title: "Keep title" });
    const deleteStoryProject = vi.fn().mockResolvedValue(undefined);
    const client = {
      listStoryProjects: vi
        .fn()
        .mockResolvedValueOnce([deletedStory, remainingStory])
        .mockResolvedValue([remainingStory]),
      renameStoryProject: vi.fn().mockResolvedValue(deletedStory),
      deleteStoryProject,
    } as unknown as ApiClient;
    const { queryClient, wrapper } = createWrapper();

    const { result } = renderHook(() => useStories(client), { wrapper });

    await waitFor(() => {
      expect(result.current.stories).toHaveLength(2);
    });

    await act(async () => {
      await result.current.deleteStory("story-1");
    });

    expect(deleteStoryProject).toHaveBeenCalledWith("story-1");
    expect(queryClient.getQueryData<StoryProjectResponse[]>(["storyProjects"])).toEqual([
      remainingStory,
    ]);
    await waitFor(() => {
      expect(result.current.stories).toEqual([remainingStory]);
    });
  });

  it("keeps the storyProjects cache unchanged when deleting a story fails", async () => {
    const originalStory = makeStory();
    const otherStory = makeStory({ id: "story-2", title: "Other title" });
    const deleteStoryProject = vi.fn().mockRejectedValue(new Error("delete failed"));
    const client = makeClient([originalStory, otherStory], originalStory, deleteStoryProject);
    const { queryClient, wrapper } = createWrapper();

    const { result } = renderHook(() => useStories(client), { wrapper });

    await waitFor(() => {
      expect(result.current.stories).toHaveLength(2);
    });

    await expect(
      act(async () => {
        await result.current.deleteStory("story-1");
      }),
    ).rejects.toThrow("delete failed");

    expect(queryClient.getQueryData<StoryProjectResponse[]>(["storyProjects"])).toEqual([
      originalStory,
      otherStory,
    ]);
  });
});
