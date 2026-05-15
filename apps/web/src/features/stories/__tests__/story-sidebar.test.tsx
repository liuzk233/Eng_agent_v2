import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StorySidebar } from "../StorySidebar";
import { NewStoryDialog } from "../NewStoryDialog";
import type { StoryProject } from "../storyTypes";

const mockStories: StoryProject[] = [
  {
    id: "1",
    title: "My First Story",
    style: "web_novel",
    targetChapterCount: 5,
    currentChapterNumber: 1,
    createdAt: "2026-05-11",
    updatedAt: "2026-05-11",
  },
  {
    id: "2",
    title: "Sci-Fi Adventure",
    style: "science_fiction",
    targetChapterCount: 10,
    currentChapterNumber: 3,
    createdAt: "2026-05-10",
    updatedAt: "2026-05-11",
  },
];

describe("StorySidebar", () => {
  it("renders empty state when no stories", () => {
    render(
      <StorySidebar
        stories={[]}
        selectedStoryId={null}
        onSelectStory={vi.fn()}
        onNewStory={vi.fn()}
      />,
    );
    expect(screen.getByText(/还没有故事/)).toBeInTheDocument();
  });

  it("renders story list", () => {
    render(
      <StorySidebar
        stories={mockStories}
        selectedStoryId={null}
        onSelectStory={vi.fn()}
        onNewStory={vi.fn()}
      />,
    );
    expect(screen.getByText("My First Story")).toBeInTheDocument();
    expect(screen.getByText("Sci-Fi Adventure")).toBeInTheDocument();
  });

  it("shows selected state", () => {
    render(
      <StorySidebar
        stories={mockStories}
        selectedStoryId="1"
        onSelectStory={vi.fn()}
        onNewStory={vi.fn()}
      />,
    );
    const selected = screen.getByText("My First Story").closest("button");
    expect(selected?.classList.contains("story-sidebar-item--selected")).toBe(true);
  });

  it("calls onSelectStory when story clicked", () => {
    const onSelect = vi.fn();
    render(
      <StorySidebar
        stories={mockStories}
        selectedStoryId={null}
        onSelectStory={onSelect}
        onNewStory={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText("Sci-Fi Adventure"));
    expect(onSelect).toHaveBeenCalledWith("2");
  });

  it("calls onNewStory when new story button clicked", () => {
    const onNew = vi.fn();
    render(
      <StorySidebar
        stories={[]}
        selectedStoryId={null}
        onSelectStory={vi.fn()}
        onNewStory={onNew}
      />,
    );
    fireEvent.click(screen.getByText("新建故事"));
    expect(onNew).toHaveBeenCalled();
  });
});

describe("NewStoryDialog", () => {
  it("renders when open", () => {
    render(
      <NewStoryDialog open={true} onClose={vi.fn()} onSubmit={vi.fn()} />,
    );
    expect(screen.getByText("新建故事")).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    render(
      <NewStoryDialog open={false} onClose={vi.fn()} onSubmit={vi.fn()} />,
    );
    expect(screen.queryByText("新建故事")).not.toBeInTheDocument();
  });

  it("allows style selection", () => {
    render(
      <NewStoryDialog open={true} onClose={vi.fn()} onSubmit={vi.fn()} />,
    );
    const sciFiRadio = screen.getByLabelText("科幻小说");
    expect(sciFiRadio).toBeInTheDocument();
    fireEvent.click(sciFiRadio);
    expect(sciFiRadio).toBeChecked();
  });

  it("forces chapter count to 1 for exam_reading", () => {
    render(
      <NewStoryDialog open={true} onClose={vi.fn()} onSubmit={vi.fn()} />,
    );
    fireEvent.click(screen.getByLabelText("应试阅读文章"));
    const chapterInput = screen.getByLabelText("章节数") as HTMLInputElement;
    expect(chapterInput.value).toBe("1");
    expect(chapterInput.disabled).toBe(true);
    expect(screen.getByText("应试阅读固定为 1 章")).toBeInTheDocument();
  });

  it("submits with correct data", () => {
    const onSubmit = vi.fn();
    render(
      <NewStoryDialog open={true} onClose={vi.fn()} onSubmit={onSubmit} />,
    );
    fireEvent.change(screen.getByLabelText("目标单词"), {
      target: { value: "courage, adventure courage" },
    });
    fireEvent.click(screen.getByRole("button", { name: "创建故事" }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ targetWords: ["courage", "adventure"], style: "web_novel" }),
    );
  });
});
