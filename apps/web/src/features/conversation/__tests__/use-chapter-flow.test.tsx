// @vitest-environment jsdom

import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useChapterFlow } from "../useChapterFlow";
import type { ChapterContentResponse } from "../../../lib/api/types";
import type { ApiClient } from "../../../lib/api/client";

function chapterResponse(
  storyProjectId: string,
  englishContent: string,
  highlightedTargetWords: string[],
): ChapterContentResponse {
  return {
    id: `${storyProjectId}-chapter-1`,
    storyProjectId,
    chapterNumber: 1,
    status: "completed",
    output: {
      englishContent,
      highlightedTargetWords,
      chineseTranslation: `${englishContent} 中文`,
    },
  };
}

describe("useChapterFlow", () => {
  it("loads the selected story chapter instead of reusing the previous output", async () => {
    const getChapter = vi.fn()
      .mockResolvedValueOnce(chapterResponse("story-1", "First story **alpha**.", ["alpha"]))
      .mockResolvedValueOnce(chapterResponse("story-2", "Second story **beta**.", ["beta"]));
    const client = { getChapter } as unknown as ApiClient;

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
    const client = { getChapter } as unknown as ApiClient;

    const { result } = renderHook(() =>
      useChapterFlow(client, "story-draft", ["pass", "exit", "kill"]),
    );

    await waitFor(() => {
      expect(getChapter).toHaveBeenCalledWith("story-draft", 1);
    });
    expect(result.current.output).toBeNull();
    expect(result.current.targetWords).toEqual(["pass", "exit", "kill"]);
  });
});
