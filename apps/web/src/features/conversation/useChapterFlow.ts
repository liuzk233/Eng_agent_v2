import { useState, useCallback, useEffect } from "react";
import type { ChapterListItem, ChapterOutput, GenerationTaskResponse } from "../../lib/api/types";
import { ApiClient } from "../../lib/api/client";

export interface ChapterFlowState {
  chapters: ChapterListItem[];
  chapterNumber: number;
  targetWords: string[];
  isGenerating: boolean;
  generationStatus: string | null;
  output: ChapterOutput | null;
  retryCount: number;
  generationTaskId: string | null;
}

function createChapterState(chapterNumber = 1, targetWords: string[] = []): Omit<ChapterFlowState, "chapters"> {
  return {
    chapterNumber,
    targetWords,
    isGenerating: false,
    generationStatus: null,
    output: null,
    retryCount: 0,
    generationTaskId: null,
  };
}

function loadChaptersForStory(
  apiClient: ApiClient,
  storyProjectId: string,
): Promise<ChapterListItem[]> {
  return apiClient.listChapters(storyProjectId).catch(() => []);
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

    Promise.all([
      apiClient.getChapter(storyProjectId, initialChapterNumber).catch(() => null),
      loadChaptersForStory(apiClient, storyProjectId),
    ]).then(([chapter, chapters]) => {
      if (ignore) return;
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
            }
          : {}),
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
    setState((s) => ({ ...s, isGenerating: true, generationStatus: "queued" }));
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
    setState((s) => ({ ...s, output: null, isGenerating: true, generationStatus: "running" }));
    try {
      const result = await apiClient.generateChapter(storyProjectId, state.chapterNumber);
      setState((s) => ({
        ...s,
        generationTaskId: result.id,
        generationStatus: result.status,
        retryCount: result.retryCount,
        isGenerating: true,
      }));
    } catch {
      setState((s) => ({ ...s, isGenerating: false, generationStatus: "failed_internal" }));
    }
  }, [apiClient, storyProjectId, state.chapterNumber]);

  const applyGenerationTask = useCallback((task: GenerationTaskResponse | null) => {
    if (!task) return;
    setState((s) => ({
      ...s,
      generationStatus: task.status,
      retryCount: task.retryCount,
      isGenerating: ["queued", "running", "reviewing", "retrying"].includes(task.status),
    }));
  }, []);

  const loadCompletedChapter = useCallback(async () => {
    if (!storyProjectId) return;
    const [chapter, chapters] = await Promise.all([
      apiClient.getChapter(storyProjectId, state.chapterNumber),
      loadChaptersForStory(apiClient, storyProjectId),
    ]);
    setState((s) => ({
      ...s,
      chapters,
      chapterNumber: chapter.chapterNumber,
      output: chapter.output,
      generationStatus: chapter.status,
      isGenerating: false,
    }));
  }, [apiClient, storyProjectId, state.chapterNumber]);

  const startNextChapter = useCallback(() => {
    setState((s) => ({ ...s, ...createChapterState(s.chapterNumber + 1) }));
  }, []);

  const selectChapter = useCallback(async (chapterNumber: number) => {
    if (!storyProjectId) return;
    setState((s) => ({
      ...s,
      ...createChapterState(chapterNumber, []),
      generationStatus: null,
    }));
    try {
      const chapter = await apiClient.getChapter(storyProjectId, chapterNumber);
      setState((s) => ({
        ...s,
        chapterNumber: chapter.chapterNumber,
        targetWords: chapter.output.highlightedTargetWords,
        generationStatus: chapter.status,
        output: chapter.output,
        isGenerating: false,
      }));
    } catch {
      // draft chapter — keep empty state
    }
  }, [apiClient, storyProjectId]);

  return {
    ...state,
    setTargetWords,
    submitWords,
    startGeneration,
    applyGenerationTask,
    loadCompletedChapter,
    startNextChapter,
    selectChapter,
  };
}
