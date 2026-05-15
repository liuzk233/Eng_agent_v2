import type {
  ChapterContentResponse,
  ChapterGenerationResultResponse,
  CreateStoryProjectRequest,
  LoginRequest,
  RegisterRequest,
  StoryProjectResponse,
  TargetWordsSubmitRequest,
  TokenResponse,
  UserResponse,
  GenerationTaskResponse,
} from "./types";

type Fetcher = typeof fetch;
const TOKEN_STORAGE_KEY = "vsl_token";

export interface ApiClientOptions {
  baseUrl?: string;
  getAccessToken?: () => string | null;
  fetcher?: Fetcher;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: HeadersInit;
}

export class ApiError extends Error {
  readonly status: number;
  readonly data: unknown;

  constructor(status: number, data: unknown, message?: string) {
    super(message ?? `API request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

function resolveDefaultBaseUrl(): string {
  const env = (import.meta as ImportMeta & { env?: { VITE_API_BASE_URL?: string } }).env?.VITE_API_BASE_URL;
  return env?.trim() || "";
}

function readStoredAccessToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function toApiPath(path: string): string {
  return path.startsWith("/api/") ? path : `/api/${path.replace(/^\/+/, "")}`;
}

async function parseResponse(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return null;
  }

  const text = await response.text();
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function camelToSnake(value: string): string {
  return value.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

function snakeToCamel(value: string): string {
  return value.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
}

function mapKeys(value: unknown, keyMapper: (key: string) => string): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => mapKeys(item, keyMapper));
  }
  if (value && typeof value === "object" && value.constructor === Object) {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [keyMapper(key), mapKeys(item, keyMapper)]),
    );
  }
  return value;
}

export class ApiClient {
  private readonly baseUrl: string;
  private readonly getAccessToken: () => string | null;
  private readonly fetcher: Fetcher;

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = trimTrailingSlash(options.baseUrl ?? resolveDefaultBaseUrl());
    this.getAccessToken = options.getAccessToken ?? readStoredAccessToken;
    this.fetcher = options.fetcher ?? fetch.bind(globalThis);
  }

  async request<TResponse>(path: string, options: RequestOptions = {}): Promise<TResponse> {
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...(options.headers as Record<string, string> | undefined),
    };
    const token = this.getAccessToken();

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const init: RequestInit = {
      method: options.method ?? "GET",
      headers,
    };

    if (options.body !== undefined) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(mapKeys(options.body, camelToSnake));
    }

    const response = await this.fetcher(`${this.baseUrl}${toApiPath(path)}`, init);
    const data = await parseResponse(response);

    if (!response.ok) {
      const message =
        typeof data === "object" && data !== null && "detail" in data
          ? String((data as { detail: unknown }).detail)
          : undefined;
      throw new ApiError(response.status, data, message);
    }

    return mapKeys(data, snakeToCamel) as TResponse;
  }

  register(payload: RegisterRequest): Promise<TokenResponse> {
    return this.request<TokenResponse>("/auth/register", { method: "POST", body: payload });
  }

  login(payload: LoginRequest): Promise<TokenResponse> {
    return this.request<TokenResponse>("/auth/login", { method: "POST", body: payload });
  }

  getCurrentUser(): Promise<UserResponse> {
    return this.request<UserResponse>("/auth/me");
  }

  createStoryProject(payload: CreateStoryProjectRequest): Promise<StoryProjectResponse> {
    return this.request<StoryProjectResponse>("/story-projects", { method: "POST", body: payload });
  }

  listStoryProjects(): Promise<StoryProjectResponse[]> {
    return this.request<StoryProjectResponse[]>("/story-projects");
  }

  getStoryProject(storyProjectId: string): Promise<StoryProjectResponse> {
    return this.request<StoryProjectResponse>(`/story-projects/${storyProjectId}`);
  }

  submitChapterTargetWords(
    storyProjectId: string,
    chapterNumber: number,
    payload: TargetWordsSubmitRequest,
  ): Promise<ChapterContentResponse> {
    return this.request<ChapterContentResponse>(
      `/story-projects/${storyProjectId}/chapters/${chapterNumber}/words`,
      { method: "POST", body: payload },
    );
  }

  generateChapter(storyProjectId: string, chapterNumber: number): Promise<GenerationTaskResponse> {
    return this.request<GenerationTaskResponse>(
      `/story-projects/${storyProjectId}/chapters/${chapterNumber}/generate`,
      { method: "POST" },
    );
  }

  getChapter(storyProjectId: string, chapterNumber: number): Promise<ChapterContentResponse> {
    return this.request<ChapterContentResponse>(`/story-projects/${storyProjectId}/chapters/${chapterNumber}`);
  }

  getChapterGenerationResult(
    storyProjectId: string,
    chapterNumber: number,
  ): Promise<ChapterGenerationResultResponse> {
    return this.request<ChapterGenerationResultResponse>(
      `/story-projects/${storyProjectId}/chapters/${chapterNumber}/generation-result`,
    );
  }

  getGenerationTask(taskId: string): Promise<GenerationTaskResponse> {
    return this.request<GenerationTaskResponse>(`/generation-tasks/${taskId}`);
  }
}

export function createApiClient(options: ApiClientOptions = {}): ApiClient {
  return new ApiClient(options);
}

export const apiClient = createApiClient();
