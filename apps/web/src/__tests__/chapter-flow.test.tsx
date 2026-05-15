import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
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
import { useStories } from "../features/stories/useStories";
import { ApiClient } from "../lib/api/client";

function createMockClient(): ApiClient {
  return {
    login: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
    listStoryProjects: vi.fn().mockResolvedValue([]),
    createStoryProject: vi.fn(),
  } as unknown as ApiClient;
}

describe("Chapter Flow Integration", () => {
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

  it("renders new story dialog", () => {
    render(
      <NewStoryDialog open={true} onClose={vi.fn()} onSubmit={vi.fn()} />,
    );
    expect(screen.getByText("新建故事")).toBeInTheDocument();
    expect(screen.getByLabelText("目标单词")).toBeInTheDocument();
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
});
