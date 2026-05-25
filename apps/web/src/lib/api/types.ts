export type StoryStyle = "web_novel" | "science_fiction" | "exam_reading";

export type GenerationStatus =
  | "queued"
  | "running"
  | "reviewing"
  | "retrying"
  | "completed"
  | "fallback_completed"
  | "failed_internal";

export type ReviewResult = "passed" | "retry_required" | "fallback_accepted";

export type TargetWordSource = "manual" | "library";

export interface RegisterRequest {
  email: string;
  password: string;
  inviteCode: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  accessToken: string;
  tokenType: "bearer";
}

export interface UserResponse {
  id: string;
  email: string;
  isActive: boolean;
  createdAt: string;
}

export interface CreateStoryProjectRequest {
  title: string;
  style: StoryStyle;
  targetChapterCount: number;
}

export interface RenameStoryProjectRequest {
  title: string;
}

export interface StoryProjectResponse {
  id: string;
  title: string;
  style: StoryStyle;
  targetChapterCount: number;
  currentChapterNumber: number;
  createdAt: string;
  updatedAt: string;
}

export interface TargetWordInput {
  word: string;
  source: TargetWordSource;
  lemma?: string;
}

export interface TargetWordsSubmitRequest {
  words: TargetWordInput[];
}

export interface ChapterOutput {
  englishContent: string;
  highlightedTargetWords: string[];
  chineseTranslation: string;
}

export interface ChapterContentResponse {
  id: string;
  storyProjectId: string;
  chapterNumber: number;
  status: string;
  output: ChapterOutput;
}

export interface GenerationTaskResponse {
  id: string;
  chapterId: string;
  status: GenerationStatus;
  retryCount: number;
  createdAt: string;
  updatedAt: string;
  startedAt?: string | null;
  completedAt?: string | null;
  fallbackReason?: string | null;
}

export interface OutOfSyllabusWord {
  word: string;
  translationCn: string;
}

export interface QualityReportResponse {
  id: string;
  generationTaskId: string;
  chapterId: string;
  result: ReviewResult;
  outOfSyllabusRate: number;
  outOfSyllabusWords: OutOfSyllabusWord[];
  targetWordHits: Record<string, number>;
  passed: boolean;
  createdAt: string;
  reviewNotes?: string | null;
}

export interface ChapterGenerationResultResponse {
  task: GenerationTaskResponse;
  output: ChapterOutput;
  qualityReport: QualityReportResponse;
}

export interface ChapterTargetWordResponse {
  word: string;
  lemma: string;
  source: string;
  position: number;
}

export interface ChapterLatestGenerationTaskResponse {
  id: string;
  chapterId: string;
  status: GenerationStatus;
  retryCount: number;
  createdAt: string;
  updatedAt: string;
  startedAt?: string | null;
  completedAt?: string | null;
  fallbackReason?: string | null;
}

export interface ChapterListItem {
  id: string;
  storyProjectId: string;
  chapterNumber: number;
  status: string;
  targetWords: ChapterTargetWordResponse[];
  hasOutput: boolean;
  latestGenerationTask?: ChapterLatestGenerationTaskResponse | null;
}
