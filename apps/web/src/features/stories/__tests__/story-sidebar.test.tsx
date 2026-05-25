import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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

  it("opens the row operation menu and enters rename mode", () => {
    render(
      <StorySidebar
        stories={mockStories}
        selectedStoryId={null}
        onSelectStory={vi.fn()}
        onNewStory={vi.fn()}
        onRenameStory={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "打开故事操作菜单：My First Story" }));
    expect(screen.getByRole("menu")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("menuitem", { name: "重命名" }));

    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(screen.getByLabelText("重命名故事名称")).toHaveValue("My First Story");
  });

  it("confirms a valid inline rename", async () => {
    const onRenameStory = vi.fn().mockResolvedValue(undefined);
    render(
      <StorySidebar
        stories={mockStories}
        selectedStoryId={null}
        onSelectStory={vi.fn()}
        onNewStory={vi.fn()}
        onRenameStory={onRenameStory}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "打开故事操作菜单：My First Story" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "重命名" }));
    fireEvent.change(screen.getByLabelText("重命名故事名称"), {
      target: { value: "Renamed Story" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存" }));

    await waitFor(() => {
      expect(onRenameStory).toHaveBeenCalledWith("1", "Renamed Story");
    });
    await waitFor(() => {
      expect(screen.queryByLabelText("重命名故事名称")).not.toBeInTheDocument();
    });
  });

  it("disables rename controls while saving", async () => {
    let resolveRename!: () => void;
    const onRenameStory = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveRename = resolve;
        }),
    );
    render(
      <StorySidebar
        stories={mockStories}
        selectedStoryId={null}
        onSelectStory={vi.fn()}
        onNewStory={vi.fn()}
        onRenameStory={onRenameStory}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "打开故事操作菜单：My First Story" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "重命名" }));
    fireEvent.change(screen.getByLabelText("重命名故事名称"), {
      target: { value: "Renamed Story" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "保存中" })).toBeDisabled();
    });
    expect(screen.getByLabelText("重命名故事名称")).toBeDisabled();
    expect(screen.getByRole("button", { name: "取消" })).toBeDisabled();

    resolveRename();
    await waitFor(() => {
      expect(screen.queryByLabelText("重命名故事名称")).not.toBeInTheDocument();
    });
  });

  it("keeps editing open and shows a recoverable error when rename fails", async () => {
    const onRenameStory = vi.fn().mockRejectedValue(new Error("network"));
    render(
      <StorySidebar
        stories={mockStories}
        selectedStoryId={null}
        onSelectStory={vi.fn()}
        onNewStory={vi.fn()}
        onRenameStory={onRenameStory}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "打开故事操作菜单：My First Story" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "重命名" }));
    fireEvent.change(screen.getByLabelText("重命名故事名称"), {
      target: { value: "Renamed Story" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("重命名失败，请重试");
    });
    expect(screen.getByLabelText("重命名故事名称")).toHaveValue("Renamed Story");
    expect(onRenameStory).toHaveBeenCalledWith("1", "Renamed Story");
  });

  it("cancels inline rename without changing the story", () => {
    const onRenameStory = vi.fn();
    render(
      <StorySidebar
        stories={mockStories}
        selectedStoryId={null}
        onSelectStory={vi.fn()}
        onNewStory={vi.fn()}
        onRenameStory={onRenameStory}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "打开故事操作菜单：My First Story" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "重命名" }));
    fireEvent.change(screen.getByLabelText("重命名故事名称"), {
      target: { value: "Draft Title" },
    });
    fireEvent.click(screen.getByRole("button", { name: "取消" }));

    expect(screen.queryByLabelText("重命名故事名称")).not.toBeInTheDocument();
    expect(screen.getByText("My First Story")).toBeInTheDocument();
    expect(onRenameStory).not.toHaveBeenCalled();
  });

  it("shows an inline error for a blank rename and does not call the API", () => {
    const onRenameStory = vi.fn();
    render(
      <StorySidebar
        stories={mockStories}
        selectedStoryId={null}
        onSelectStory={vi.fn()}
        onNewStory={vi.fn()}
        onRenameStory={onRenameStory}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "打开故事操作菜单：My First Story" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "重命名" }));
    fireEvent.change(screen.getByLabelText("重命名故事名称"), {
      target: { value: "   " },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存" }));

    expect(screen.getByRole("alert")).toHaveTextContent("名称不能为空");
    expect(screen.getByLabelText("重命名故事名称")).toHaveAttribute(
      "aria-describedby",
      "rename-story-error-1",
    );
    expect(onRenameStory).not.toHaveBeenCalled();
  });

  it("cancels inline rename with Escape", () => {
    const onRenameStory = vi.fn();
    render(
      <StorySidebar
        stories={mockStories}
        selectedStoryId={null}
        onSelectStory={vi.fn()}
        onNewStory={vi.fn()}
        onRenameStory={onRenameStory}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "打开故事操作菜单：My First Story" }));
    fireEvent.click(screen.getByRole("menuitem", { name: "重命名" }));
    fireEvent.keyDown(screen.getByLabelText("重命名故事名称"), { key: "Escape" });

    expect(screen.queryByLabelText("重命名故事名称")).not.toBeInTheDocument();
    expect(onRenameStory).not.toHaveBeenCalled();
  });

  it("keeps the operation trigger reachable by keyboard focus", () => {
    render(
      <StorySidebar
        stories={mockStories}
        selectedStoryId={null}
        onSelectStory={vi.fn()}
        onNewStory={vi.fn()}
        onRenameStory={vi.fn()}
      />,
    );

    const menuButton = screen.getByRole("button", { name: "打开故事操作菜单：My First Story" });
    menuButton.focus();

    expect(menuButton).toHaveFocus();
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
