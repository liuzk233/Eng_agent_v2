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
  const { stories, isLoading, createStory } = useStories(apiClient);
  const [selectedStoryId, setSelectedStoryId] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [draftTargetWordsByStoryId, setDraftTargetWordsByStoryId] = useState<Record<string, string[]>>({});

  const selectedStory = stories.find((s) => s.id === selectedStoryId) ?? null;
  const chapterFlow = useChapterFlow(
    apiClient,
    selectedStoryId,
    selectedStoryId ? draftTargetWordsByStoryId[selectedStoryId] ?? [] : [],
  );
  const generationTask = useGenerationTask(apiClient, chapterFlow.generationTaskId);
  const { applyGenerationTask, loadCompletedChapter, output } = chapterFlow;

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
        title: generateStoryTitle(input.targetWords),
        style: input.style,
        targetChapterCount: input.targetChapterCount,
      });
      await apiClient.submitChapterTargetWords(created.id, 1, {
        words: input.targetWords.map((word) => ({ word, source: "manual" })),
      });
      setDraftTargetWordsByStoryId((current) => ({
        ...current,
        [created.id]: input.targetWords,
      }));
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
    />
  );

  const main = selectedStory ? (
    <ConversationView>
      <SetupCard
        title={selectedStory.title}
        style={selectedStory.style}
        targetChapterCount={selectedStory.targetChapterCount}
      />

      {chapterFlow.targetWords.length > 0 && (
        <UserWordsCard words={chapterFlow.targetWords} />
      )}

      {chapterFlow.generationStatus && (
        <GenerationStatusIndicator
          status={chapterFlow.generationStatus as "queued" | "running" | "reviewing" | "retrying" | "completed" | "fallback_completed" | "failed_internal"}
          retryCount={chapterFlow.retryCount}
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
        </>
      )}

      {!chapterFlow.isGenerating && !chapterFlow.output && (
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
      <p className="text-body">选择一个故事，或新建故事开始按章节记忆单词。</p>
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

function generateStoryTitle(targetWords: string[]): string {
  const previewWords = targetWords.slice(0, 3).join(", ");
  if (targetWords.length <= 3) {
    return `${previewWords} 词汇故事`;
  }
  return `${previewWords} 等 ${targetWords.length} 个词的故事`;
}
