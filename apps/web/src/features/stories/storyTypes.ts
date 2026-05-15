import type { StoryStyle } from "../../lib/api/types";

export const STORY_STYLE_OPTIONS: { value: StoryStyle; label: string }[] = [
  { value: "web_novel", label: "网络爽文" },
  { value: "science_fiction", label: "科幻小说" },
  { value: "exam_reading", label: "应试阅读文章" },
];

export interface StoryProject {
  id: string;
  title: string;
  style: StoryStyle;
  targetChapterCount: number;
  currentChapterNumber: number;
  createdAt: string;
  updatedAt: string;
}

export interface NewStoryInput {
  targetWords: string[];
  style: StoryStyle;
  targetChapterCount: number;
}

export const MAX_CHAPTER_COUNT = 50;
export const MIN_CHAPTER_COUNT = 1;
export const EXAM_READING_CHAPTER_COUNT = 1;
