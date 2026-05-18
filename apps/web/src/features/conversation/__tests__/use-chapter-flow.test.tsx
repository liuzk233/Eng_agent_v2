// @vitest-environment jsdom

import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useChapterFlow } from "../useChapterFlow";
import type { ChapterContentResponse, ChapterListItem } from "../../../lib/api/types";
import type { ApiClient } from "../../../lib/api/client";

function chapterResponse(
  storyProjectId: string,
  englishContent: string,
  highlightedTargetWords: string[],
  chapterNumber = 1,
): ChapterContentResponse {
  return {
    id: `${storyProjectId}-chapter-${chapterNumber}`,
    storyProjectId,
    chapterNumber,
    status: "completed",
    output: {
      englishContent,
      highlightedTargetWords,
      chineseTranslation: `${englishContent} 中文`,
    },
  };
}

function chapterListItem(
  storyProjectId: string,
  chapterNumber: number,
  status: string,
): ChapterListItem {
  return {
    id: `${storyProjectId}-chapter-${chapterNumber}`,
    storyProjectId,
    chapterNumber,
    status,
    targetWords: [],
    hasOutput: status === "completed",
    latestGenerationTask: null,
  };
}

describe("useChapterFlow", () => {
  it("loads the selected story chapter instead of reusing the previous output", async () => {
    const getChapter = vi.fn()
      .mockResolvedValueOnce(chapterResponse("story-1", "First story **alpha**.", ["alpha"]))
      .mockResolvedValueOnce(chapterResponse("story-2", "Second story **beta**.", ["beta"]));
    const listChapters = vi.fn().mockResolvedValue([]);
    const client = { getChapter, listChapters } as unknown as ApiClient;

    const { result, rerender } = renderHook(
      ({ storyId }) => useChapterFlow(client, storyId),
      { initialProps: { storyId: "story-1" as string | null } },
    );

    await waitFor(() => {
      expect(result.current.output?.englishContent).toBe("First story **alpha**.");
    });

    rerender({ storyId: "story-2" });
    expect(result.current.output).toBeNull();

    await waitFor(() => {
      expect(result.current.output?.englishContent).toBe("Second story **beta**.");
    });
    expect(result.current.targetWords).toEqual(["beta"]);
    expect(getChapter).toHaveBeenCalledWith("story-2", 1);
  });

  it("keeps seeded target words when a draft story has no completed chapter", async () => {
    const getChapter = vi.fn().mockRejectedValue(new Error("not found"));
    const listChapters = vi.fn().mockResolvedValue([]);
    const client = { getChapter, listChapters } as unknown as ApiClient;

    const { result } = renderHook(() =>
      useChapterFlow(client, "story-draft", ["pass", "exit", "kill"]),
    );

    await waitFor(() => {
      expect(getChapter).toHaveBeenCalledWith("story-draft", 1);
    });
    expect(result.current.output).toBeNull();
    expect(result.current.targetWords).toEqual(["pass", "exit", "kill"]);
  });

  it("moves to the next chapter and generates against that chapter number", async () => {
    const getChapter = vi.fn()
      .mockResolvedValueOnce(chapterResponse("story-serial", "First **alpha**.", ["alpha"], 1));
    const listChapters = vi.fn().mockResolvedValue([]);
    const submitChapterTargetWords = vi.fn().mockResolvedValue({ words: [] });
    const generateChapter = vi.fn().mockResolvedValue({
      id: "task-2",
      chapterId: "chapter-2",
      status: "queued",
      retryCount: 0,
      createdAt: "2026-05-18T00:00:00Z",
      updatedAt: "2026-05-18T00:00:00Z",
    });
    const client = {
      getChapter,
      listChapters,
      submitChapterTargetWords,
      generateChapter,
    } as unknown as ApiClient;

    const { result } = renderHook(() => useChapterFlow(client, "story-serial"));

    await waitFor(() => {
      expect(result.current.output?.englishContent).toBe("First **alpha**.");
    });

    act(() => {
      result.current.startNextChapter();
      result.current.setTargetWords(["beta"]);
    });

    await act(async () => {
      await result.current.submitWords();
      await result.current.startGeneration();
    });

    expect(result.current.chapterNumber).toBe(2);
    expect(submitChapterTargetWords).toHaveBeenCalledWith("story-serial", 2, {
      words: [{ word: "beta", source: "manual" }],
    });
    expect(generateChapter).toHaveBeenCalledWith("story-serial", 2);
  });

  it("loads chapter list and allows selecting a chapter", async () => {
    const chapters = [
      chapterListItem("story-nav", 1, "completed"),
      chapterListItem("story-nav", 2, "draft"),
    ];
    const getChapter = vi.fn()
      .mockResolvedValueOnce(chapterResponse("story-nav", "Chapter one **word**.", ["word"], 1))
      .mockResolvedValueOnce(chapterResponse("story-nav", "Chapter two **beta**.", ["beta"], 2));
    const listChapters = vi.fn().mockResolvedValue(chapters);
    const client = { getChapter, listChapters } as unknown as ApiClient;

    const { result } = renderHook(() => useChapterFlow(client, "story-nav"));

    await waitFor(() => {
      expect(result.current.chapters).toHaveLength(2);
    });

    await act(async () => {
      await result.current.selectChapter(2);
    });

    expect(result.current.chapterNumber).toBe(2);
    expect(result.current.output?.englishContent).toBe("Chapter two **beta**.");
    expect(getChapter).toHaveBeenCalledWith("story-nav", 2);
  });
});
