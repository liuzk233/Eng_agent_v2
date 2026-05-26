import { useState, useCallback, useEffect } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "./features/auth/AuthProvider";
import { LoginPage } from "./features/auth/LoginPage";
import { RegisterPage } from "./features/auth/RegisterPage";
import { ProtectedRoute } from "./features/auth/ProtectedRoute";
import { StorySidebar } from "./features/stories/StorySidebar";
import { NewStoryDialog } from "./features/stories/NewStoryDialog";
import { useStories } from "./features/stories/useStories";
import { useChapterFlow } from "./features/conversation/useChapterFlow";
import { AppShell } from "./features/conversation/AppShell";
import { ConversationView } from "./features/conversation/ConversationView";
import { SetupCard } from "./features/conversation/cards/SetupCard";
import { UserWordsCard } from "./features/conversation/cards/UserWordsCard";
import { ChapterCard } from "./features/conversation/cards/ChapterCard";
import { ReviewCard } from "./features/conversation/cards/ReviewCard";
import { TargetWordsInputDock } from "./features/conversation/TargetWordsInputDock";
import { ChapterNavigator } from "./features/conversation/ChapterNavigator";
import { GenerationStatusIndicator } from "./features/generation/GenerationStatusIndicator";
import { useGenerationTask } from "./features/generation/useGenerationTask";
import { apiClient } from "./lib/api/client";
import { queryClient } from "./lib/query/queryClient";
import type { NewStoryInput } from "./features/stories/storyTypes";

function AuthGate() {
  const { token } = useAuth();
  const path = typeof window !== "undefined" ? window.location.pathname : "/";

  if (!token) {
    if (path === "/register") {
      return <RegisterPage />;
    }
    return <LoginPage />;
  }
  return <MainApp />;
}

function MainApp() {
  return (
    <ProtectedRoute>
      <StoryApp />
    </ProtectedRoute>
  );
}

function StoryApp() {
  const { stories, isLoading, createStory, renameStory, isRenaming } = useStories(apiClient);
  const [selectedStoryId, setSelectedStoryId] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const selectedStory = stories.find((s) => s.id === selectedStoryId) ?? null;
  const chapterFlow = useChapterFlow(
    apiClient,
    selectedStoryId,
    [],
    selectedStory?.currentChapterNumber ?? 1,
  );
  const generationTask = useGenerationTask(apiClient, chapterFlow.generationTaskId);
  const { applyGenerationTask, loadCompletedChapter, output } = chapterFlow;
  const hasNextChapterRecord = chapterFlow.chapters.some(
    (chapter) => chapter.chapterNumber === chapterFlow.chapterNumber + 1,
  );

  useEffect(() => {
    applyGenerationTask(generationTask.task);
    if (
      generationTask.task &&
      !generationTask.isPolling &&
      !output &&
      (generationTask.task.status === "completed" || generationTask.task.status === "fallback_completed")
    ) {
      loadCompletedChapter();
    }
  }, [applyGenerationTask, generationTask.isPolling, generationTask.task, loadCompletedChapter, output]);

  const handleCreateStory = useCallback(
    async (input: NewStoryInput) => {
      const created = await createStory({
        title: generateStoryTitle(input.style),
        style: input.style,
        targetChapterCount: input.targetChapterCount,
      });
      setDialogOpen(false);
      setSelectedStoryId(created.id);
    },
    [createStory],
  );

  const sidebar = (
    <StorySidebar
      stories={stories.map((s) => ({
        id: s.id,
        title: s.title,
        style: s.style,
        targetChapterCount: s.targetChapterCount,
        currentChapterNumber: s.currentChapterNumber,
        createdAt: s.createdAt,
        updatedAt: s.updatedAt,
      }))}
      selectedStoryId={selectedStoryId}
      onSelectStory={setSelectedStoryId}
      onNewStory={() => setDialogOpen(true)}
      onRenameStory={renameStory}
      isRenaming={isRenaming}
      onHome={() => setSelectedStoryId(null)}
    />
  );

  const main = selectedStory ? (
    <ConversationView>
      <SetupCard
        title={selectedStory.title}
        style={selectedStory.style}
        targetChapterCount={selectedStory.targetChapterCount}
      />
      {chapterFlow.chapters.length > 0 && (
        <ChapterNavigator
          chapters={chapterFlow.chapters}
          currentChapterNumber={chapterFlow.chapterNumber}
          onSelectChapter={chapterFlow.selectChapter}
        />
      )}
      <div className="chapter-progress text-supporting">
        第 {chapterFlow.chapterNumber} 章 / 共 {selectedStory.targetChapterCount} 章
      </div>

      {chapterFlow.targetWords.length > 0 && !chapterFlow.isPendingDraft && (
        <UserWordsCard words={chapterFlow.targetWords} />
      )}

      {chapterFlow.generationStatus && (
        <GenerationStatusIndicator
          status={chapterFlow.generationStatus as "queued" | "running" | "reviewing" | "retrying" | "completed" | "fallback_completed" | "failed_internal"}
          retryCount={chapterFlow.retryCount}
          isStale={generationTask.isStale}
          onRetry={chapterFlow.retryGeneration}
        />
      )}

      {chapterFlow.output && (
        <>
          <ChapterCard
            englishContent={chapterFlow.output.englishContent}
            highlightedTargetWords={chapterFlow.output.highlightedTargetWords}
            chineseTranslation={chapterFlow.output.chineseTranslation}
          />
          {chapterFlow.generationStatus === "fallback_completed" && (
            <ReviewCard
              outOfSyllabusRate={0.015}
              retryCount={chapterFlow.retryCount}
              status="fallback_completed"
            />
          )}
          {chapterFlow.chapterNumber < selectedStory.targetChapterCount && !hasNextChapterRecord && (
            <div className="chapter-next-actions">
              <button
                type="button"
                className="auth-submit chapter-next-button"
                onClick={chapterFlow.startNextChapter}
              >
                生成下一章
              </button>
            </div>
          )}
        </>
      )}

      {!chapterFlow.isGenerating && !chapterFlow.output && !chapterFlow.isPendingDraft && (
        <TargetWordsInputDock
          words={chapterFlow.targetWords}
          onWordsChange={chapterFlow.setTargetWords}
          onSubmit={async () => {
            await chapterFlow.submitWords();
            await chapterFlow.startGeneration();
          }}
        />
      )}
    </ConversationView>
  ) : (
    <div className="conversation-empty">
      <section className="empty-hero" aria-labelledby="empty-hero-title">
        <p className="auth-kicker">Story workspace</p>
        <h2 id="empty-hero-title" className="text-headline">把单词放进一段会继续生长的故事里</h2>
        <p className="text-body">选择一个故事，或新建故事开始按章节记忆单词。</p>
        <div className="empty-hero-actions">
          <button type="button" className="story-new-btn story-new-btn--large" onClick={() => setDialogOpen(true)}>
            新建故事
          </button>
          <span className="text-supporting">
            {isLoading ? "正在同步故事列表" : `${stories.length} 个故事已就绪`}
          </span>
        </div>
      </section>

      <section className="empty-module-grid" aria-label="学习流程">
        <article className="empty-module">
          <span className="empty-module-index text-micro-label">01</span>
          <h3 className="text-title">输入目标词</h3>
          <p className="text-supporting">每章建议 7 个词，最多 10 个词，系统会把它们自然写入英文正文。</p>
        </article>
        <article className="empty-module">
          <span className="empty-module-index text-micro-label">02</span>
          <h3 className="text-title">选择叙事风格</h3>
          <p className="text-supporting">网络爽文、科幻小说或应试阅读，适配不同记忆场景。</p>
        </article>
        <article className="empty-module">
          <span className="empty-module-index text-micro-label">03</span>
          <h3 className="text-title">按章节复习</h3>
          <p className="text-supporting">保留故事连续性和中文释义，让复习更像阅读而不是背表格。</p>
        </article>
      </section>
    </div>
  );

  return (
    <>
      <AppShell sidebar={sidebar} main={main} />
      <NewStoryDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={handleCreateStory}
      />
    </>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider apiClient={apiClient}>
        <AuthGate />
      </AuthProvider>
    </QueryClientProvider>
  );
}

function generateStoryTitle(style: NewStoryInput["style"]): string {
  const styleLabel = {
    web_novel: "网络爽文",
    science_fiction: "科幻小说",
    exam_reading: "应试阅读",
  }[style];
  return `${styleLabel}词汇故事`;
}
