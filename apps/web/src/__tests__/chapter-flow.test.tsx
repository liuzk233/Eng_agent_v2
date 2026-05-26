import { describe, it, expect, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { App } from "../App";
import { AuthProvider } from "../features/auth/AuthProvider";
import { StorySidebar } from "../features/stories/StorySidebar";
import { NewStoryDialog } from "../features/stories/NewStoryDialog";
import { AppShell } from "../features/conversation/AppShell";
import { ConversationView } from "../features/conversation/ConversationView";
import { SetupCard } from "../features/conversation/cards/SetupCard";
import { TargetWordsInputDock } from "../features/conversation/TargetWordsInputDock";
import { GenerationStatusIndicator } from "../features/generation/GenerationStatusIndicator";
import { ChapterCard } from "../features/conversation/cards/ChapterCard";
import { ReviewCard } from "../features/conversation/cards/ReviewCard";
import { ProtectedRoute } from "../features/auth/ProtectedRoute";
import { ApiClient, apiClient } from "../lib/api/client";
import { queryClient } from "../lib/query/queryClient";
import type { ChapterListItem, StoryProjectResponse } from "../lib/api/types";

function createMockClient(): ApiClient {
  return {
    login: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
    listStoryProjects: vi.fn().mockResolvedValue([]),
    createStoryProject: vi.fn(),
  } as unknown as ApiClient;
}

const story: StoryProjectResponse = {
  id: "story-1",
  title: "Serial Story",
  style: "web_novel",
  targetChapterCount: 3,
  currentChapterNumber: 1,
  createdAt: "2026-05-20T00:00:00Z",
  updatedAt: "2026-05-20T00:00:00Z",
};

const otherStory: StoryProjectResponse = {
  id: "story-2",
  title: "Side Quest",
  style: "science_fiction",
  targetChapterCount: 2,
  currentChapterNumber: 1,
  createdAt: "2026-05-21T00:00:00Z",
  updatedAt: "2026-05-21T00:00:00Z",
};

const STYLE_LABELS: Record<StoryProjectResponse["style"], string> = {
  web_novel: "网络爽文",
  science_fiction: "科幻小说",
  exam_reading: "应试阅读",
};

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function storySelectionName(currentStory: StoryProjectResponse): RegExp {
  return new RegExp(
    `^${escapeRegExp(currentStory.title)}\\s*${STYLE_LABELS[currentStory.style]}\\s*·\\s*${currentStory.targetChapterCount}\\s*章$`,
  );
}

async function findStorySelectionButton(currentStory: StoryProjectResponse = story) {
  return screen.findByRole("button", { name: storySelectionName(currentStory) });
}

async function openStoryMenu(currentStory: StoryProjectResponse) {
  const menuButton = await screen.findByRole("button", {
    name: `打开故事操作菜单：${currentStory.title}`,
  });
  fireEvent.click(menuButton);
  return screen.getByRole("menu");
}

function storyWithCurrentChapter(currentChapterNumber: number): StoryProjectResponse {
  return {
    ...story,
    currentChapterNumber,
  };
}

function chapterListItem(chapterNumber: number, status = "completed"): ChapterListItem {
  return {
    id: `chapter-${chapterNumber}`,
    storyProjectId: story.id,
    chapterNumber,
    status,
    targetWords: [],
    hasOutput: status === "completed",
    latestGenerationTask: null,
  };
}

function draftChapterListItem(chapterNumber: number, targetWords: string[]): ChapterListItem {
  return {
    ...chapterListItem(chapterNumber, "draft"),
    targetWords: targetWords.map((word, position) => ({
      word,
      lemma: word,
      source: "manual",
      position,
    })),
  };
}

function mockStoryApp(chapters: ChapterListItem[]) {
  sessionStorage.setItem("vsl_token", "test-token");
  vi.spyOn(apiClient, "listStoryProjects").mockResolvedValue([story]);
  vi.spyOn(apiClient, "listChapters").mockResolvedValue(chapters);
  vi.spyOn(apiClient, "getChapter").mockResolvedValue({
    id: "chapter-1",
    storyProjectId: story.id,
    chapterNumber: 1,
    status: "completed",
    output: {
      englishContent: "She showed great **courage**.",
      highlightedTargetWords: ["courage"],
      chineseTranslation: "她展现了勇气。",
    },
  });
}

function mockStoryAppWithStory(currentStory: StoryProjectResponse, chapters: ChapterListItem[]) {
  sessionStorage.setItem("vsl_token", "test-token");
  vi.spyOn(apiClient, "listStoryProjects").mockResolvedValue([currentStory]);
  vi.spyOn(apiClient, "listChapters").mockResolvedValue(chapters);
  vi.spyOn(apiClient, "getChapter").mockResolvedValue({
    id: "chapter-1",
    storyProjectId: currentStory.id,
    chapterNumber: 1,
    status: "completed",
    output: {
      englishContent: "She showed great **courage**.",
      highlightedTargetWords: ["courage"],
      chineseTranslation: "她展现了勇气。",
    },
  });
}

describe("Chapter Flow Integration", () => {
  afterEach(() => {
    cleanup();
    queryClient.clear();
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  it("renders AppShell with sidebar and main content", () => {
    render(
      <AppShell
        sidebar={<div data-testid="sidebar">Stories</div>}
        main={<div data-testid="main">Content</div>}
      />,
    );
    expect(screen.getByTestId("sidebar")).toBeInTheDocument();
    expect(screen.getByTestId("main")).toBeInTheDocument();
  });

  it("renders empty state when no story selected", () => {
    render(
      <AppShell
        sidebar={
          <StorySidebar
            stories={[]}
            selectedStoryId={null}
            onSelectStory={vi.fn()}
            onNewStory={vi.fn()}
          />
        }
        main={<p>选择一个故事，或新建故事开始按章节记忆单词。</p>}
      />,
    );
    expect(screen.getByText(/选择一个故事/)).toBeInTheDocument();
  });

  it("renders story setup and target words input when story selected", () => {
    render(
      <ConversationView>
        <SetupCard title="My Story" style="web_novel" targetChapterCount={5} />
        <TargetWordsInputDock
          words={[]}
          onWordsChange={vi.fn()}
          onSubmit={vi.fn()}
        />
      </ConversationView>,
    );
    expect(screen.getByText("My Story")).toBeInTheDocument();
    expect(screen.getByLabelText("目标词")).toBeInTheDocument();
  });

  it("shows generation status and chapter output after generation", () => {
    render(
      <ConversationView>
        <GenerationStatusIndicator status="completed" />
        <ChapterCard
          englishContent="She showed great **courage** in the **adventure**."
          highlightedTargetWords={["courage", "adventure"]}
          chineseTranslation="她在冒险中展现了极大的勇气。"
        />
      </ConversationView>,
    );
    expect(screen.getByText("生成通过")).toBeInTheDocument();
    expect(screen.getByText("她在冒险中展现了极大的勇气。")).toBeInTheDocument();
  });

  it("shows fallback status with review card", () => {
    render(
      <ConversationView>
        <GenerationStatusIndicator status="fallback_completed" retryCount={3} />
        <ReviewCard
          outOfSyllabusRate={0.015}
          retryCount={3}
          status="fallback_completed"
        />
      </ConversationView>,
    );
    const labels = screen.getAllByText("已标注少量超纲词");
    expect(labels.length).toBeGreaterThanOrEqual(1);
  });

  it("renders new story dialog without target words", () => {
    render(
      <NewStoryDialog open={true} onClose={vi.fn()} onSubmit={vi.fn()} />,
    );
    expect(screen.getByText("新建故事")).toBeInTheDocument();
    expect(screen.queryByLabelText("目标单词")).not.toBeInTheDocument();
    expect(screen.getByText("故事风格")).toBeInTheDocument();
  });

  it("protected route redirects when not authenticated", () => {
    render(
      <AuthProvider apiClient={createMockClient()}>
        <ProtectedRoute>
          <p>Protected content</p>
        </ProtectedRoute>
      </AuthProvider>,
    );
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
    expect(screen.getByText("请先登录后继续")).toBeInTheDocument();
  });

  it("hides next chapter generation button when next chapter already exists", async () => {
    mockStoryApp([chapterListItem(1), chapterListItem(2, "draft")]);

    render(<App />);
    fireEvent.click(await findStorySelectionButton());
    await screen.findByText("她展现了勇气。");

    expect(screen.queryByRole("button", { name: "生成下一章" })).not.toBeInTheDocument();
  });

  it("shows next chapter generation button when no next chapter exists", async () => {
    mockStoryApp([chapterListItem(1)]);

    render(<App />);
    fireEvent.click(await findStorySelectionButton());
    await screen.findByText("她展现了勇气。");

    expect(screen.getByRole("button", { name: "生成下一章" })).toBeInTheDocument();
  });

  it("keeps existing next chapter entry behavior when button is shown", async () => {
    mockStoryApp([chapterListItem(1)]);

    render(<App />);
    fireEvent.click(await findStorySelectionButton());
    await screen.findByText("她展现了勇气。");

    fireEvent.click(screen.getByRole("button", { name: "生成下一章" }));

    await waitFor(() => {
      expect(screen.getByText("第 2 章 / 共 3 章")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("目标词")).toBeInTheDocument();
  });

  it("shows target words and can confirm generation when selecting an existing draft chapter", async () => {
    mockStoryApp([
      chapterListItem(1),
      draftChapterListItem(2, ["past", "go", "test"]),
    ]);
    const submitChapterTargetWords = vi.spyOn(apiClient, "submitChapterTargetWords").mockResolvedValue({
      id: "chapter-2",
      storyProjectId: story.id,
      chapterNumber: 2,
      status: "draft",
      output: {
        englishContent: "",
        highlightedTargetWords: [],
        chineseTranslation: "",
      },
    });
    const freshTaskTimestamp = new Date().toISOString();
    const generateChapter = vi.spyOn(apiClient, "generateChapter").mockResolvedValue({
      id: "task-draft-2",
      chapterId: "chapter-2",
      status: "queued",
      retryCount: 0,
      createdAt: freshTaskTimestamp,
      updatedAt: freshTaskTimestamp,
    });
    vi.spyOn(apiClient, "getGenerationTask").mockResolvedValue({
      id: "task-draft-2",
      chapterId: "chapter-2",
      status: "queued",
      retryCount: 0,
      createdAt: freshTaskTimestamp,
      updatedAt: freshTaskTimestamp,
    });

    const { container } = render(<App />);
    fireEvent.click(await findStorySelectionButton());
    await screen.findByText("她展现了勇气。");

    fireEvent.click(screen.getByRole("button", { name: /第 2 章/ }));

    await waitFor(() => {
      expect(screen.getByText("第 2 章 / 共 3 章")).toBeInTheDocument();
    });
    expect(screen.getByText("待生成")).toBeInTheDocument();
    expect(screen.getByLabelText("目标词")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "从词库选择" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "确认目标词" })).toBeInTheDocument();
    expect(container.querySelector(".user-words-card")).not.toBeInTheDocument();
    expect(screen.getAllByText("past").length).toBeGreaterThanOrEqual(1);

    fireEvent.click(screen.getByRole("button", { name: "确认目标词" }));

    await waitFor(() => {
      expect(generateChapter).toHaveBeenCalledWith(story.id, 2);
    });
    const generatingChapterButton = await screen.findByRole("button", {
      name: /^第 2 章\s*生成中$/,
    });
    expect(screen.getByRole("status")).toHaveTextContent("排队中");

    fireEvent.click(generatingChapterButton);

    expect(screen.getByRole("status")).toHaveTextContent("排队中");
    expect(screen.queryByLabelText("目标词")).not.toBeInTheDocument();
    expect(submitChapterTargetWords).toHaveBeenCalledWith(story.id, 2, {
      words: [
        { word: "past", source: "manual" },
        { word: "go", source: "manual" },
        { word: "test", source: "manual" },
      ],
    });
  });

  it("can return to a generating chapter after viewing another chapter", async () => {
    const freshTaskTimestamp = new Date().toISOString();
    const runningChapter: ChapterListItem = {
      ...draftChapterListItem(2, ["past", "go", "test"]),
      status: "running",
      latestGenerationTask: {
        id: "task-running-2",
        chapterId: "chapter-2",
        status: "running",
        retryCount: 0,
        createdAt: freshTaskTimestamp,
        updatedAt: freshTaskTimestamp,
      },
    };
    mockStoryApp([
      chapterListItem(1),
      runningChapter,
    ]);
    vi.spyOn(apiClient, "getGenerationTask").mockResolvedValue({
      id: "task-running-2",
      chapterId: "chapter-2",
      status: "running",
      retryCount: 0,
      createdAt: freshTaskTimestamp,
      updatedAt: freshTaskTimestamp,
    });

    render(<App />);
    fireEvent.click(await findStorySelectionButton());

    await screen.findByText("她展现了勇气。");
    fireEvent.click(await screen.findByRole("button", {
      name: /^第 2 章\s*生成中$/,
    }));

    await waitFor(() => {
      expect(screen.getByText("第 2 章 / 共 3 章")).toBeInTheDocument();
    });
    expect(screen.getByRole("status")).toHaveTextContent("生成中");

    fireEvent.click(screen.getByRole("button", {
      name: /^第 1 章\s*已完成$/,
    }));

    await waitFor(() => {
      expect(screen.getByText("第 1 章 / 共 3 章")).toBeInTheDocument();
    });
    expect(screen.getByText("她展现了勇气。")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", {
      name: /^第 2 章\s*生成中$/,
    }));

    await waitFor(() => {
      expect(screen.getByText("第 2 章 / 共 3 章")).toBeInTheDocument();
    });
    expect(screen.getByRole("status")).toHaveTextContent("生成中");
    expect(screen.queryByLabelText("目标词")).not.toBeInTheDocument();
  });

  it("shows target words when opening a history story on a draft chapter", async () => {
    const historyStory = storyWithCurrentChapter(3);
    mockStoryAppWithStory(historyStory, [
      chapterListItem(1),
      chapterListItem(2),
      draftChapterListItem(3, ["past", "go", "test"]),
    ]);

    render(<App />);
    fireEvent.click(await findStorySelectionButton(historyStory));

    await waitFor(() => {
      expect(screen.getByText("第 3 章 / 共 3 章")).toBeInTheDocument();
    });
    expect(screen.getByText("待生成")).toBeInTheDocument();
    expect(screen.getByLabelText("目标词")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "从词库选择" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "确认目标词" })).toBeInTheDocument();
    expect(screen.getAllByText("past").length).toBeGreaterThanOrEqual(1);
  });

  it("creates a story without target words and shows first chapter target word input", async () => {
    sessionStorage.setItem("vsl_token", "test-token");
    const createdStory: StoryProjectResponse = {
      ...story,
      id: "story-new",
      title: "网络爽文词汇故事",
      currentChapterNumber: 1,
    };
    vi.spyOn(apiClient, "listStoryProjects")
      .mockResolvedValueOnce([])
      .mockResolvedValue([createdStory]);
    vi.spyOn(apiClient, "createStoryProject").mockResolvedValue(createdStory);
    vi.spyOn(apiClient, "listChapters").mockResolvedValue([]);
    vi.spyOn(apiClient, "getChapter").mockRejectedValue(new Error("not found"));
    const submitChapterTargetWords = vi.spyOn(apiClient, "submitChapterTargetWords").mockResolvedValue({
      id: "chapter-1",
      storyProjectId: createdStory.id,
      chapterNumber: 1,
      status: "draft",
      output: {
        englishContent: "",
        highlightedTargetWords: [],
        chineseTranslation: "",
      },
    });

    render(<App />);

    fireEvent.click(screen.getAllByRole("button", { name: "新建故事" })[0]);
    expect(screen.queryByLabelText("目标单词")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "创建故事" }));

    await waitFor(() => {
      expect(screen.getByText("第 1 章 / 共 3 章")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("目标词")).toBeInTheDocument();
    expect(submitChapterTargetWords).not.toHaveBeenCalled();
  });

  it("returns to the default empty state after deleting the currently selected story", async () => {
    sessionStorage.setItem("vsl_token", "test-token");
    vi.spyOn(apiClient, "listStoryProjects")
      .mockResolvedValueOnce([story, otherStory])
      .mockResolvedValue([otherStory]);
    vi.spyOn(apiClient, "listChapters").mockResolvedValue([chapterListItem(1)]);
    vi.spyOn(apiClient, "getChapter").mockResolvedValue({
      id: "chapter-1",
      storyProjectId: story.id,
      chapterNumber: 1,
      status: "completed",
      output: {
        englishContent: "She showed great **courage**.",
        highlightedTargetWords: ["courage"],
        chineseTranslation: "她展现了勇气。",
      },
    });
    const deleteStoryProject = vi.spyOn(apiClient, "deleteStoryProject").mockResolvedValue(undefined);

    render(<App />);
    fireEvent.click(await findStorySelectionButton(story));
    await screen.findByText("她展现了勇气。");

    const menu = await openStoryMenu(story);
    fireEvent.click(within(menu).getByRole("menuitem", { name: "删除" }));
    fireEvent.click(screen.getByRole("button", { name: "确认删除" }));

    await waitFor(() => {
      expect(deleteStoryProject).toHaveBeenCalledWith(story.id);
    });
    await waitFor(() => {
      expect(screen.getByText("选择一个故事，或新建故事开始按章节记忆单词。")).toBeInTheDocument();
    });
    expect(screen.queryByText("她展现了勇气。")).not.toBeInTheDocument();
  });

  it("keeps the current reading content after deleting a different story", async () => {
    sessionStorage.setItem("vsl_token", "test-token");
    vi.spyOn(apiClient, "listStoryProjects")
      .mockResolvedValueOnce([story, otherStory])
      .mockResolvedValue([story]);
    vi.spyOn(apiClient, "listChapters").mockResolvedValue([chapterListItem(1)]);
    vi.spyOn(apiClient, "getChapter").mockResolvedValue({
      id: "chapter-1",
      storyProjectId: story.id,
      chapterNumber: 1,
      status: "completed",
      output: {
        englishContent: "She showed great **courage**.",
        highlightedTargetWords: ["courage"],
        chineseTranslation: "她展现了勇气。",
      },
    });
    const deleteStoryProject = vi.spyOn(apiClient, "deleteStoryProject").mockResolvedValue(undefined);

    render(<App />);
    fireEvent.click(await findStorySelectionButton(story));
    await screen.findByText("她展现了勇气。");

    const menu = await openStoryMenu(otherStory);
    fireEvent.click(within(menu).getByRole("menuitem", { name: "删除" }));
    fireEvent.click(screen.getByRole("button", { name: "确认删除" }));

    await waitFor(() => {
      expect(deleteStoryProject).toHaveBeenCalledWith(otherStory.id);
    });
    expect(screen.getByText("她展现了勇气。")).toBeInTheDocument();
    expect(screen.getByText("第 1 章 / 共 3 章")).toBeInTheDocument();
  });
});
