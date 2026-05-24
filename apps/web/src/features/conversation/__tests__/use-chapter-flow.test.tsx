// @vitest-environment jsdom

import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useChapterFlow } from "../useChapterFlow";
import type { ChapterContentResponse, ChapterLatestGenerationTaskResponse, ChapterListItem } from "../../../lib/api/types";
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
  latestGenerationTask: ChapterLatestGenerationTaskResponse | null = null,
  targetWords: string[] = [],
): ChapterListItem {
  return {
    id: `${storyProjectId}-chapter-${chapterNumber}`,
    storyProjectId,
    chapterNumber,
    status,
    targetWords: targetWords.map((word, position) => ({
      word,
      lemma: word,
      source: "manual",
      position,
    })),
    hasOutput: status === "completed",
    latestGenerationTask,
  };
}

function generationTask(
  chapterId: string,
  status: ChapterLatestGenerationTaskResponse["status"] = "running",
): ChapterLatestGenerationTaskResponse {
  return {
    id: `${chapterId}-task`,
    chapterId,
    status,
    retryCount: 1,
    createdAt: "2026-05-18T00:00:00Z",
    updatedAt: "2026-05-18T00:01:00Z",
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

  it("restores a history story draft chapter as pending instead of word selection", async () => {
    const chapters = [
      chapterListItem("story-history-pending", 1, "completed"),
      chapterListItem("story-history-pending", 2, "completed"),
      chapterListItem("story-history-pending", 3, "draft", null, ["past", "go", "test"]),
    ];
    const getChapter = vi.fn().mockRejectedValue(new Error("not found"));
    const listChapters = vi.fn().mockResolvedValue(chapters);
    const generateChapter = vi.fn();
    const client = { getChapter, listChapters, generateChapter } as unknown as ApiClient;

    const { result } = renderHook(() =>
      useChapterFlow(client, "story-history-pending", [], 3),
    );

    await waitFor(() => {
      expect(result.current.chapters).toHaveLength(3);
    });

    expect(result.current.chapterNumber).toBe(3);
    expect(result.current.output).toBeNull();
    expect(result.current.isPendingDraft).toBe(true);
    expect(result.current.isGenerating).toBe(false);
    expect(result.current.generationTaskId).toBeNull();
    expect(getChapter).not.toHaveBeenCalledWith("story-history-pending", 3);
    expect(generateChapter).not.toHaveBeenCalled();
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
      chapterListItem("story-nav", 2, "completed"),
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

  it("restores a running generation task from the chapter list when entering a story", async () => {
    const runningTask = generationTask("story-running-chapter-2");
    const chapters = [
      chapterListItem("story-running", 1, "completed"),
      chapterListItem("story-running", 2, "running", runningTask),
    ];
    const getChapter = vi.fn().mockRejectedValue(new Error("not found"));
    const listChapters = vi.fn().mockResolvedValue(chapters);
    const generateChapter = vi.fn();
    const client = { getChapter, listChapters, generateChapter } as unknown as ApiClient;

    const { result } = renderHook(() =>
      useChapterFlow(client, "story-running", [], 2),
    );

    await waitFor(() => {
      expect(result.current.generationTaskId).toBe(runningTask.id);
    });

    expect(result.current.isGenerating).toBe(true);
    expect(result.current.generationStatus).toBe("running");
    expect(result.current.retryCount).toBe(1);
    expect(getChapter).not.toHaveBeenCalled();
    expect(generateChapter).not.toHaveBeenCalled();
  });

  it("restores an existing running task when selecting a generating chapter", async () => {
    const runningTask = generationTask("story-select-chapter-2");
    const chapters = [
      chapterListItem("story-select", 1, "completed"),
      chapterListItem("story-select", 2, "running", runningTask),
    ];
    const getChapter = vi.fn()
      .mockResolvedValueOnce(chapterResponse("story-select", "Chapter one **word**.", ["word"], 1));
    const listChapters = vi.fn().mockResolvedValue(chapters);
    const generateChapter = vi.fn();
    const client = { getChapter, listChapters, generateChapter } as unknown as ApiClient;

    const { result } = renderHook(() => useChapterFlow(client, "story-select"));

    await waitFor(() => {
      expect(result.current.chapters).toHaveLength(2);
    });

    await act(async () => {
      await result.current.selectChapter(2);
    });

    expect(result.current.chapterNumber).toBe(2);
    expect(result.current.output).toBeNull();
    expect(result.current.isGenerating).toBe(true);
    expect(result.current.generationTaskId).toBe(runningTask.id);
    expect(getChapter).not.toHaveBeenCalledWith("story-select", 2);
    expect(generateChapter).not.toHaveBeenCalled();
  });

  it("marks a selected draft chapter as pending instead of returning to word selection", async () => {
    const chapters = [
      chapterListItem("story-pending", 1, "completed"),
      chapterListItem("story-pending", 2, "draft", null, ["past", "go", "test"]),
    ];
    const getChapter = vi.fn()
      .mockResolvedValueOnce(chapterResponse("story-pending", "Chapter one **word**.", ["word"], 1));
    const listChapters = vi.fn().mockResolvedValue(chapters);
    const generateChapter = vi.fn();
    const client = { getChapter, listChapters, generateChapter } as unknown as ApiClient;

    const { result } = renderHook(() => useChapterFlow(client, "story-pending"));

    await waitFor(() => {
      expect(result.current.chapters).toHaveLength(2);
    });

    await act(async () => {
      await result.current.selectChapter(2);
    });

    expect(result.current.chapterNumber).toBe(2);
    expect(result.current.output).toBeNull();
    expect(result.current.isPendingDraft).toBe(true);
    expect(result.current.isGenerating).toBe(false);
    expect(result.current.generationTaskId).toBeNull();
    expect(getChapter).not.toHaveBeenCalledWith("story-pending", 2);
    expect(generateChapter).not.toHaveBeenCalled();
  });

  it("loads a completed chapter after a restored running task finishes", async () => {
    const runningTask = generationTask("story-finish-chapter-2");
    const chapters = [
      chapterListItem("story-finish", 1, "completed"),
      chapterListItem("story-finish", 2, "running", runningTask),
    ];
    const completedChapters = [
      chapterListItem("story-finish", 1, "completed"),
      chapterListItem("story-finish", 2, "completed"),
    ];
    const getChapter = vi.fn()
      .mockResolvedValueOnce(chapterResponse("story-finish", "Chapter two **beta**.", ["beta"], 2));
    const listChapters = vi.fn()
      .mockResolvedValueOnce(chapters)
      .mockResolvedValueOnce(completedChapters);
    const client = { getChapter, listChapters } as unknown as ApiClient;

    const { result } = renderHook(() =>
      useChapterFlow(client, "story-finish", [], 2),
    );

    await waitFor(() => {
      expect(result.current.generationTaskId).toBe(runningTask.id);
    });

    await act(async () => {
      await result.current.loadCompletedChapter();
    });

    expect(getChapter).toHaveBeenCalledWith("story-finish", 2);
    expect(result.current.output?.englishContent).toBe("Chapter two **beta**.");
    expect(result.current.isGenerating).toBe(false);
  });

  it("does not reset output when clicking the already-active completed chapter", async () => {
    const chapters = [
      chapterListItem("story-click-same", 1, "completed"),
      chapterListItem("story-click-same", 2, "draft"),
    ];
    const getChapter = vi.fn()
      .mockResolvedValueOnce(chapterResponse("story-click-same", "Chapter one **word**.", ["word"], 1))
      .mockResolvedValueOnce(chapterResponse("story-click-same", "Chapter two **beta**.", ["beta"], 2));
    const listChapters = vi.fn().mockResolvedValue(chapters);
    const client = { getChapter, listChapters } as unknown as ApiClient;

    const { result } = renderHook(() => useChapterFlow(client, "story-click-same"));

    await waitFor(() => {
      expect(result.current.output?.englishContent).toBe("Chapter one **word**.");
    });

    getChapter.mockClear();

    await act(async () => {
      await result.current.selectChapter(1);
    });

    expect(result.current.output?.englishContent).toBe("Chapter one **word**.");
    expect(getChapter).not.toHaveBeenCalled();
  });

  it("does not reset generationTaskId when clicking the already-active generating chapter", async () => {
    const runningTask = generationTask("story-click-gen-chapter-2");
    const chapters = [
      chapterListItem("story-click-gen", 1, "completed"),
      chapterListItem("story-click-gen", 2, "running", runningTask),
    ];
    const getChapter = vi.fn()
      .mockResolvedValueOnce(chapterResponse("story-click-gen", "Chapter one **word**.", ["word"], 1));
    const listChapters = vi.fn().mockResolvedValue(chapters);
    const client = { getChapter, listChapters } as unknown as ApiClient;

    const { result } = renderHook(() => useChapterFlow(client, "story-click-gen"));

    await waitFor(() => {
      expect(result.current.chapters).toHaveLength(2);
    });

    await act(async () => {
      await result.current.selectChapter(2);
    });

    expect(result.current.generationTaskId).toBe(runningTask.id);
    expect(result.current.isGenerating).toBe(true);

    getChapter.mockClear();

    await act(async () => {
      await result.current.selectChapter(2);
    });

    expect(result.current.generationTaskId).toBe(runningTask.id);
    expect(result.current.isGenerating).toBe(true);
    expect(getChapter).not.toHaveBeenCalled();
  });

  it("retryGeneration calls generateChapter and updates task state", async () => {
    const getChapter = vi.fn()
      .mockResolvedValueOnce(chapterResponse("story-retry", "First **alpha**.", ["alpha"], 1));
    const listChapters = vi.fn().mockResolvedValue([]);
    const generateChapter = vi.fn().mockResolvedValue({
      id: "retry-task-1",
      chapterId: "chapter-1",
      status: "queued",
      retryCount: 0,
      createdAt: "2026-05-19T00:00:00Z",
      updatedAt: "2026-05-19T00:00:00Z",
    });
    const client = {
      getChapter,
      listChapters,
      generateChapter,
    } as unknown as ApiClient;

    const { result } = renderHook(() => useChapterFlow(client, "story-retry"));

    await waitFor(() => {
      expect(result.current.output?.englishContent).toBe("First **alpha**.");
    });

    await act(async () => {
      await result.current.retryGeneration();
    });

    expect(generateChapter).toHaveBeenCalledWith("story-retry", 1);
    expect(result.current.generationTaskId).toBe("retry-task-1");
    expect(result.current.generationStatus).toBe("queued");
    expect(result.current.isGenerating).toBe(true);
    expect(result.current.output?.englishContent).toBe("First **alpha**.");
  });
});
