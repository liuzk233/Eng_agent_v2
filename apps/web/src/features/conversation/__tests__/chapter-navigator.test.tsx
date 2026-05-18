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
    expect(screen.getByText("生成中")).toBeDefined();
    expect(screen.getByText("待生成")).toBeDefined();
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
        chapters={makeChapters()}
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

    fireEvent.click(screen.getByText("第 3 章"));
    expect(onSelectChapter).toHaveBeenCalledWith(3);
  });
});
