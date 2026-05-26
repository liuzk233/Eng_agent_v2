import { useState, useCallback, useEffect } from "react";
import type { ChapterListItem, ChapterOutput, GenerationTaskResponse } from "../../lib/api/types";
import { ApiClient } from "../../lib/api/client";

export interface ChapterFlowState {
  chapters: ChapterListItem[];
  chapterNumber: number;
  targetWords: string[];
  isPendingDraft: boolean;
  isGenerating: boolean;
  generationStatus: string | null;
  output: ChapterOutput | null;
  retryCount: number;
  generationTaskId: string | null;
  generationFailureReason: string | null;
}

function createChapterState(chapterNumber = 1, targetWords: string[] = []): Omit<ChapterFlowState, "chapters"> {
  return {
    chapterNumber,
    targetWords,
    isPendingDraft: false,
    isGenerating: false,
    generationStatus: null,
    output: null,
    retryCount: 0,
    generationTaskId: null,
    generationFailureReason: null,
  };
}

function loadChaptersForStory(
  apiClient: ApiClient,
  storyProjectId: string,
): Promise<ChapterListItem[]> {
  return apiClient.listChapters(storyProjectId).catch(() => []);
}

function isPollingStatus(status: string): boolean {
  return ["queued", "running", "reviewing", "retrying"].includes(status);
}

function isFailedStatus(status: string): boolean {
  return status === "failed_internal";
}

function findChapter(chapters: ChapterListItem[], chapterNumber: number): ChapterListItem | undefined {
  return chapters.find((chapter) => chapter.chapterNumber === chapterNumber);
}

function targetWordsFromChapter(chapter: ChapterListItem | undefined): string[] {
  return chapter?.targetWords.map((word) => word.word) ?? [];
}

function isPendingDraftChapter(
  chapter: ChapterListItem | undefined,
  restoredTaskState: Partial<ChapterFlowState>,
): boolean {
  return chapter?.status === "draft" &&
    !chapter.hasOutput &&
    !restoredTaskState.generationTaskId;
}

function restoreTaskState(chapter: ChapterListItem | undefined): Partial<ChapterFlowState> {
  const task = chapter?.latestGenerationTask;
  if (!task || (!isPollingStatus(task.status) && !isFailedStatus(task.status))) return {};
  return {
    generationTaskId: task.id,
    generationStatus: task.status,
    retryCount: task.retryCount,
    isGenerating: isPollingStatus(task.status),
    generationFailureReason: task.status === "failed_internal" ? task.fallbackReason ?? null : null,
  };
}

export function useChapterFlow(
  apiClient: ApiClient,
  storyProjectId: string | null,
  initialTargetWords: string[] = [],
  initialChapterNumber = 1,
) {
  const [state, setState] = useState<ChapterFlowState>({
    chapters: [],
    ...createChapterState(initialChapterNumber),
  });

  useEffect(() => {
    let ignore = false;
    setState((s) => ({ ...s, chapters: [], ...createChapterState(initialChapterNumber, [...initialTargetWords]) }));

    if (!storyProjectId) {
      return () => {
        ignore = true;
      };
    }

    loadChaptersForStory(apiClient, storyProjectId).then(async (chapters) => {
      if (ignore) return;
      const initialListedChapter = findChapter(chapters, initialChapterNumber);
      const initialRestoredTaskState = restoreTaskState(initialListedChapter);
      const initialTargetWords = targetWordsFromChapter(initialListedChapter);

      if (initialRestoredTaskState.generationTaskId) {
        setState((s) => ({
          ...s,
          chapters,
          chapterNumber: initialChapterNumber,
          targetWords: initialTargetWords.length > 0
            ? initialTargetWords
            : s.targetWords,
          isPendingDraft: false,
          output: null,
          generationFailureReason: null,
          ...initialRestoredTaskState,
        }));
        return;
      }

      if (isPendingDraftChapter(initialListedChapter, initialRestoredTaskState)) {
        setState((s) => ({
          ...s,
          chapters,
          chapterNumber: initialChapterNumber,
          targetWords: initialTargetWords,
          isPendingDraft: false,
          isGenerating: false,
          generationStatus: null,
          output: null,
          generationTaskId: null,
          retryCount: 0,
          generationFailureReason: null,
        }));
        return;
      }

      const chapter = await apiClient.getChapter(storyProjectId, initialChapterNumber).catch(() => null);
      if (ignore) return;
      const listedChapter = findChapter(chapters, chapter?.chapterNumber ?? initialChapterNumber);
      setState((s) => ({
        ...s,
        chapters,
        ...(chapter
          ? {
              chapterNumber: chapter.chapterNumber,
              targetWords: chapter.output.highlightedTargetWords,
              generationStatus: chapter.status,
              output: chapter.output,
              isGenerating: false,
              generationTaskId: null,
              retryCount: 0,
              generationFailureReason: null,
            }
          : {
              chapterNumber: initialChapterNumber,
              targetWords: targetWordsFromChapter(listedChapter).length > 0
                ? targetWordsFromChapter(listedChapter)
                : s.targetWords,
            }),
      }));
    });

    return () => {
      ignore = true;
    };
  }, [apiClient, storyProjectId, initialChapterNumber]);

  const setTargetWords = useCallback((words: string[]) => {
    setState((s) => ({ ...s, targetWords: words }));
  }, []);

  const submitWords = useCallback(async () => {
    if (!storyProjectId || state.targetWords.length === 0) return;
    setState((s) => ({ ...s, isPendingDraft: false, isGenerating: true, generationStatus: "queued", generationFailureReason: null }));
    try {
      await apiClient.submitChapterTargetWords(storyProjectId, state.chapterNumber, {
        words: state.targetWords.map((w) => ({ word: w, source: "manual" })),
      });
    } catch {
      // word submission may fail silently for now
    }
  }, [apiClient, storyProjectId, state.chapterNumber, state.targetWords]);

  const startGeneration = useCallback(async () => {
    if (!storyProjectId) return;
    setState((s) => ({ ...s, output: null, isPendingDraft: false, isGenerating: true, generationStatus: "running", generationFailureReason: null }));
    try {
      const result = await apiClient.generateChapter(storyProjectId, state.chapterNumber);
      setState((s) => ({
        ...s,
        generationTaskId: result.id,
        generationStatus: result.status,
        retryCount: result.retryCount,
        isGenerating: true,
        generationFailureReason: result.status === "failed_internal" ? result.fallbackReason ?? null : null,
      }));
    } catch (error) {
      setState((s) => ({
        ...s,
        isGenerating: false,
        generationStatus: "failed_internal",
        generationFailureReason: error instanceof Error ? error.message : "生成失败，请重试。",
      }));
    }
  }, [apiClient, storyProjectId, state.chapterNumber]);

  const applyGenerationTask = useCallback((task: GenerationTaskResponse | null) => {
    if (!task) return;
    setState((s) => ({
      ...s,
      generationTaskId: task.id,
      generationStatus: task.status,
      retryCount: task.retryCount,
      isGenerating: isPollingStatus(task.status),
      isPendingDraft: false,
      generationFailureReason: task.status === "failed_internal" ? task.fallbackReason ?? null : null,
    }));
  }, []);

  const loadCompletedChapter = useCallback(async () => {
    if (!storyProjectId) return;
    const [chapter, chapters] = await Promise.all([
      apiClient.getChapter(storyProjectId, state.chapterNumber).catch(() => null),
      loadChaptersForStory(apiClient, storyProjectId),
    ]);
    if (!chapter?.output?.englishContent || !chapter.output.chineseTranslation) {
      setState((s) => ({
        ...s,
        chapters,
        output: null,
        generationStatus: "failed_internal",
        isGenerating: false,
        isPendingDraft: false,
        generationFailureReason: s.generationFailureReason || "章节正文不可用，请重试。",
      }));
      return;
    }
    setState((s) => ({
      ...s,
      chapters,
      chapterNumber: chapter.chapterNumber,
      output: chapter.output,
      generationStatus: chapter.status,
      isGenerating: false,
      isPendingDraft: false,
      generationFailureReason: null,
    }));
  }, [apiClient, storyProjectId, state.chapterNumber]);

  const startNextChapter = useCallback(() => {
    setState((s) => ({ ...s, ...createChapterState(s.chapterNumber + 1) }));
  }, []);

  const retryGeneration = useCallback(async () => {
    if (!storyProjectId) return;
    setState((s) => ({ ...s, isGenerating: true, generationStatus: "running", generationFailureReason: null }));
    try {
      const result = await apiClient.generateChapter(storyProjectId, state.chapterNumber);
      setState((s) => ({
        ...s,
        generationTaskId: result.id,
        generationStatus: result.status,
        retryCount: result.retryCount,
        isGenerating: true,
        generationFailureReason: result.status === "failed_internal" ? result.fallbackReason ?? null : null,
      }));
    } catch (error) {
      setState((s) => ({
        ...s,
        isGenerating: false,
        generationStatus: "failed_internal",
        generationFailureReason: error instanceof Error ? error.message : "生成失败，请重试。",
      }));
    }
  }, [apiClient, storyProjectId, state.chapterNumber]);

  const selectChapter = useCallback(async (chapterNumber: number) => {
    if (!storyProjectId) return;
    if (chapterNumber === state.chapterNumber && (state.output || state.generationTaskId)) {
      return;
    }
    const selectedChapter = findChapter(state.chapters, chapterNumber);
    const selectedTargetWords = targetWordsFromChapter(selectedChapter);
    const restoredTaskState = restoreTaskState(selectedChapter);
    const shouldSkipOutputFetch = isPendingDraftChapter(selectedChapter, restoredTaskState);
    setState((s) => ({
      ...s,
      ...createChapterState(chapterNumber, selectedTargetWords),
      isPendingDraft: false,
      generationStatus: null,
      ...restoredTaskState,
    }));
    if (shouldSkipOutputFetch) return;
    if (restoredTaskState.generationTaskId) return;

    try {
      const chapter = await apiClient.getChapter(storyProjectId, chapterNumber);
      setState((s) => ({
        ...s,
        chapterNumber: chapter.chapterNumber,
        targetWords: chapter.output.highlightedTargetWords,
        generationStatus: chapter.status,
        output: chapter.output,
        isGenerating: false,
        isPendingDraft: false,
        generationTaskId: null,
        retryCount: 0,
        generationFailureReason: null,
      }));
    } catch {
      // Draft or in-progress chapters can return 404 before output exists.
    }
  }, [apiClient, storyProjectId, state.chapters]);

  return {
    ...state,
    setTargetWords,
    submitWords,
    startGeneration,
    retryGeneration,
    applyGenerationTask,
    loadCompletedChapter,
    startNextChapter,
    selectChapter,
  };
}
