import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiClient, ApiError, createApiClient } from "../client";
import type { CreateStoryProjectRequest, RenameStoryProjectRequest, StoryProjectResponse } from "../types";
import { queryClient } from "../../query/queryClient";

const okProject: StoryProjectResponse = {
  id: "story-1",
  title: "Mars Station",
  style: "science_fiction",
  targetChapterCount: 6,
  currentChapterNumber: 1,
  createdAt: "2026-05-11T00:00:00.000Z",
  updatedAt: "2026-05-11T00:00:00.000Z",
};

const okProjectApi = {
  id: "story-1",
  title: "Mars Station",
  style: "science_fiction",
  target_chapter_count: 6,
  current_chapter_number: 1,
  created_at: "2026-05-11T00:00:00.000Z",
  updated_at: "2026-05-11T00:00:00.000Z",
};

describe("ApiClient", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  it("attaches JWT bearer tokens and serializes typed request bodies", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(okProjectApi), {
        status: 201,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const client = createApiClient({
      baseUrl: "https://api.example.test",
      getAccessToken: () => "jwt-token",
      fetcher: fetchMock,
    });
    const payload: CreateStoryProjectRequest = {
      title: "Mars Station",
      style: "science_fiction",
      targetChapterCount: 6,
    };

    const response = await client.createStoryProject(payload);

    expect(response).toEqual(okProject);
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/api/story-projects",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer jwt-token",
          "Content-Type": "application/json",
        }),
        body: JSON.stringify({
          title: "Mars Station",
          style: "science_fiction",
          target_chapter_count: 6,
        }),
      }),
    );
  });

  it("renames story projects with PATCH and parses the updated story response", async () => {
    const updatedProjectApi = {
      ...okProjectApi,
      title: "Custom study arc",
      updated_at: "2026-05-25T04:00:00.000Z",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(updatedProjectApi), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const client = createApiClient({
      baseUrl: "https://api.example.test",
      getAccessToken: () => "jwt-token",
      fetcher: fetchMock,
    });
    const payload: RenameStoryProjectRequest = {
      title: "Custom study arc",
    };

    const response = await client.renameStoryProject("story-1", payload);

    expect(response).toEqual({
      ...okProject,
      title: "Custom study arc",
      updatedAt: "2026-05-25T04:00:00.000Z",
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.test/api/story-projects/story-1",
      expect.objectContaining({
        method: "PATCH",
        headers: expect.objectContaining({
          Authorization: "Bearer jwt-token",
          "Content-Type": "application/json",
        }),
        body: JSON.stringify({
          title: "Custom study arc",
        }),
      }),
    );
  });

  it("reads the default JWT token from sessionStorage", async () => {
    sessionStorage.setItem("vsl_token", "stored-jwt-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "user-1", email: "student@example.com", is_active: true, created_at: "2026-05-14T00:00:00.000Z" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const client = createApiClient({
      baseUrl: "https://api.example.test",
      fetcher: fetchMock,
    });

    await client.getCurrentUser();

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers).toMatchObject({
      Authorization: "Bearer stored-jwt-token",
    });
  });

  it("omits authorization when no token is available", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([okProjectApi]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const client = createApiClient({
      baseUrl: "https://api.example.test/",
      getAccessToken: () => null,
      fetcher: fetchMock,
    });

    await client.listStoryProjects();

    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers).not.toHaveProperty("Authorization");
  });

  it("throws ApiError with status and parsed response details on HTTP errors", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Unauthorized" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const client = new ApiClient({
      baseUrl: "https://api.example.test",
      getAccessToken: () => "expired-token",
      fetcher: fetchMock,
    });

    await expect(client.getCurrentUser()).rejects.toMatchObject({
      name: "ApiError",
      status: 401,
      data: { detail: "Unauthorized" },
    });
  });

  it("exposes typed helpers for auth, target words, generation tasks, and chapters", async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })),
    );
    const client = createApiClient({
      baseUrl: "https://api.example.test",
      getAccessToken: () => "jwt-token",
      fetcher: fetchMock,
    });

    await client.login({ email: "student@example.com", password: "strong-password" });
    await client.register({
      email: "student@example.com",
      password: "strong-password",
      inviteCode: "INVITE-2026",
    });
    await client.submitChapterTargetWords("story-1", 2, {
      words: [{ word: "achieve", source: "manual" }],
    });
    await client.generateChapter("story-1", 2);
    await client.getGenerationTask("task-1");
    await client.getChapter("story-1", 2);
    await client.getChapterGenerationResult("story-1", 2);

    expect(fetchMock).toHaveBeenCalledTimes(7);
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "https://api.example.test/api/auth/login",
      "https://api.example.test/api/auth/register",
      "https://api.example.test/api/story-projects/story-1/chapters/2/words",
      "https://api.example.test/api/story-projects/story-1/chapters/2/generate",
      "https://api.example.test/api/generation-tasks/task-1",
      "https://api.example.test/api/story-projects/story-1/chapters/2",
      "https://api.example.test/api/story-projects/story-1/chapters/2/generation-result",
    ]);
  });
});

describe("queryClient", () => {
  it("uses a conservative polling-friendly baseline", () => {
    const defaults = queryClient.getDefaultOptions();

    expect(defaults.queries?.retry).toBe(1);
    expect(defaults.queries?.refetchOnWindowFocus).toBe(false);
    expect(defaults.mutations?.retry).toBe(0);
  });
});
