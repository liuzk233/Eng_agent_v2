import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChapterNavigator } from "../ChapterNavigator";
import type { ChapterListItem } from "../../../lib/api/types";

function makeChapters(): ChapterListItem[] {
  return [
    {
      id: "ch-1",
      storyProjectId: "story-1",
      chapterNumber: 1,
      status: "completed",
      targetWords: [],
      hasOutput: true,
      latestGenerationTask: null,
    },
    {
      id: "ch-2",
      storyProjectId: "story-1",
      chapterNumber: 2,
      status: "draft",
      targetWords: [],
      hasOutput: false,
      latestGenerationTask: null,
    },
    {
      id: "ch-3",
      storyProjectId: "story-1",
      chapterNumber: 3,
      status: "draft",
      targetWords: [],
      hasOutput: false,
      latestGenerationTask: null,
    },
  ];
}

function makeGeneratingChapters(): ChapterListItem[] {
  return [
    makeChapters()[0],
    {
      id: "ch-2",
      storyProjectId: "story-1",
      chapterNumber: 2,
      status: "running",
      targetWords: [],
      hasOutput: false,
      latestGenerationTask: {
        id: "task-2",
        chapterId: "ch-2",
        status: "running",
        retryCount: 0,
        createdAt: "2026-05-18T00:00:00Z",
        updatedAt: "2026-05-18T00:00:00Z",
      },
    },
    makeChapters()[2],
  ];
}

describe("ChapterNavigator", () => {
  it("renders a button for each chapter", () => {
    render(
      <ChapterNavigator
        chapters={makeChapters()}
        currentChapterNumber={1}
        onSelectChapter={() => {}}
      />,
    );

    expect(screen.getByText("第 1 章")).toBeDefined();
    expect(screen.getByText("第 2 章")).toBeDefined();
    expect(screen.getByText("第 3 章")).toBeDefined();
  });

  it("marks the current chapter as active", () => {
    render(
      <ChapterNavigator
        chapters={makeChapters()}
        currentChapterNumber={2}
        onSelectChapter={() => {}}
      />,
    );

    const activeItem = screen.getByText("第 2 章").closest("button");
    expect(activeItem?.className).toContain("chapter-nav-item--active");
    expect(activeItem?.getAttribute("aria-current")).toBe("page");
  });

  it("shows correct status labels", () => {
    render(
      <ChapterNavigator
        chapters={makeChapters()}
        currentChapterNumber={1}
        onSelectChapter={() => {}}
      />,
    );

    expect(screen.getByText("已完成")).toBeDefined();
    expect(screen.getByText("待生成")).toBeDefined();
    expect(screen.getByText("待解锁")).toBeDefined();
  });

  it("shows only the first draft chapter as ready to generate", () => {
    render(
      <ChapterNavigator
        chapters={makeChapters()}
        currentChapterNumber={1}
        onSelectChapter={() => {}}
      />,
    );

    const readyDraft = screen.getByText("第 2 章").closest("button");
    const lockedDraft = screen.getByText("第 3 章").closest("button");

    expect(readyDraft).not.toBeDisabled();
    expect(readyDraft?.textContent).toContain("待生成");
    expect(lockedDraft).toBeDisabled();
    expect(lockedDraft?.textContent).toContain("待解锁");
  });

  it("applies completed class to completed chapters", () => {
    render(
      <ChapterNavigator
        chapters={makeChapters()}
        currentChapterNumber={1}
        onSelectChapter={() => {}}
      />,
    );

    const completedItem = screen.getByText("第 1 章").closest("button");
    expect(completedItem?.className).toContain("chapter-nav-item--completed");
  });

  it("applies generating class to generating chapters", () => {
    render(
      <ChapterNavigator
        chapters={makeGeneratingChapters()}
        currentChapterNumber={1}
        onSelectChapter={() => {}}
      />,
    );

    const generatingItem = screen.getByText("第 2 章").closest("button");
    expect(generatingItem?.className).toContain("chapter-nav-item--generating");
  });

  it("calls onSelectChapter with the chapter number when clicked", () => {
    const onSelectChapter = vi.fn();
    render(
      <ChapterNavigator
        chapters={makeChapters()}
        currentChapterNumber={1}
        onSelectChapter={onSelectChapter}
      />,
    );

    fireEvent.click(screen.getByText("第 2 章"));
    expect(onSelectChapter).toHaveBeenCalledWith(2);
  });

  it("does not call onSelectChapter when a locked draft is clicked", () => {
    const onSelectChapter = vi.fn();
    render(
      <ChapterNavigator
        chapters={makeChapters()}
        currentChapterNumber={1}
        onSelectChapter={onSelectChapter}
      />,
    );

    fireEvent.click(screen.getByText("第 3 章"));
    expect(onSelectChapter).not.toHaveBeenCalled();
  });

  it("keeps later drafts locked when the previous chapter is generating", () => {
    render(
      <ChapterNavigator
        chapters={makeGeneratingChapters()}
        currentChapterNumber={1}
        onSelectChapter={() => {}}
      />,
    );

    const generatingCh2 = screen.getByText("第 2 章").closest("button");
    const lockedCh3 = screen.getByText("第 3 章").closest("button");

    expect(generatingCh2).not.toBeDisabled();
    expect(generatingCh2?.textContent).toContain("生成中");
    expect(lockedCh3).toBeDisabled();
    expect(lockedCh3?.textContent).toContain("待解锁");
  });

  it("unlocks the next draft only after the previous chapter is completed", () => {
    const chapters: ChapterListItem[] = [
      {
        id: "ch-1",
        storyProjectId: "story-unlock",
        chapterNumber: 1,
        status: "completed",
        targetWords: [],
        hasOutput: true,
        latestGenerationTask: null,
      },
      {
        id: "ch-2",
        storyProjectId: "story-unlock",
        chapterNumber: 2,
        status: "completed",
        targetWords: [],
        hasOutput: true,
        latestGenerationTask: null,
      },
      {
        id: "ch-3",
        storyProjectId: "story-unlock",
        chapterNumber: 3,
        status: "draft",
        targetWords: [],
        hasOutput: false,
        latestGenerationTask: null,
      },
    ];

    render(
      <ChapterNavigator
        chapters={chapters}
        currentChapterNumber={2}
        onSelectChapter={() => {}}
      />,
    );

    const unlockedCh3 = screen.getByText("第 3 章").closest("button");
    expect(unlockedCh3).not.toBeDisabled();
    expect(unlockedCh3?.textContent).toContain("待生成");
  });
});
