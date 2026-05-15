import { useState, useCallback } from "react";
import type { ChapterOutput, GenerationTaskResponse } from "../../lib/api/types";
import { ApiClient } from "../../lib/api/client";

export interface ChapterFlowState {
  targetWords: string[];
  isGenerating: boolean;
  generationStatus: string | null;
  output: ChapterOutput | null;
  retryCount: number;
  generationTaskId: string | null;
}

export function useChapterFlow(apiClient: ApiClient, storyProjectId: string | null) {
  const [state, setState] = useState<ChapterFlowState>({
    targetWords: [],
    isGenerating: false,
    generationStatus: null,
    output: null,
    retryCount: 0,
    generationTaskId: null,
  });

  const setTargetWords = useCallback((words: string[]) => {
    setState((s) => ({ ...s, targetWords: words }));
  }, []);

  const submitWords = useCallback(async () => {
    if (!storyProjectId || state.targetWords.length === 0) return;
    setState((s) => ({ ...s, isGenerating: true, generationStatus: "queued" }));
    try {
      await apiClient.submitChapterTargetWords(storyProjectId, 1, {
        words: state.targetWords.map((w) => ({ word: w, source: "manual" })),
      });
    } catch {
      // word submission may fail silently for now
    }
  }, [apiClient, storyProjectId, state.targetWords]);

  const startGeneration = useCallback(async () => {
    if (!storyProjectId) return;
    setState((s) => ({ ...s, isGenerating: true, generationStatus: "running" }));
    try {
      const result = await apiClient.generateChapter(storyProjectId, 1);
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
  }, [apiClient, storyProjectId]);

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
    const chapter = await apiClient.getChapter(storyProjectId, 1);
    setState((s) => ({
      ...s,
      output: chapter.output,
      generationStatus: chapter.status,
      isGenerating: false,
    }));
  }, [apiClient, storyProjectId]);

  return {
    ...state,
    setTargetWords,
    submitWords,
    startGeneration,
    applyGenerationTask,
    loadCompletedChapter,
  };
}
