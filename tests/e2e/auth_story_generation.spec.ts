/**
 * API-backed end-to-end test for auth + story creation + generation.
 *
 * Run: npx vitest run tests/e2e/auth_story_generation.spec.ts
 */
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { ApiClient } from "../../apps/web/src/lib/api/client";
import type { GenerationTaskResponse } from "../../apps/web/src/lib/api/types";

const BASE_URL = process.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const TEST_INVITE_CODE = "DEMO2026";
const TEST_EMAIL = `uat_${Date.now()}@wordflow.test`;
const TEST_PASSWORD = "testpassword123";

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForTerminalTask(client: ApiClient, taskId: string): Promise<GenerationTaskResponse> {
  let lastTask: GenerationTaskResponse | null = null;
  for (let attempt = 0; attempt < 30; attempt += 1) {
    const task = await client.getGenerationTask(taskId);
    lastTask = task;
    if (["completed", "fallback_completed", "failed_internal"].includes(task.status)) {
      return task;
    }
    await sleep(1000);
  }
  throw new Error(`generation task did not finish; last status=${lastTask?.status ?? "unknown"}`);
}

describe("Auth + Story Generation E2E", () => {
  let client: ApiClient;
  let token: string;

  beforeAll(() => {
    client = new ApiClient({ baseUrl: BASE_URL });
  });

  describe("AC-2: Invite code registration gate", () => {
    it("rejects registration without invite code", async () => {
      await expect(
        client.register({ email: "no-invite@test.com", password: "pass123", inviteCode: "" }),
      ).rejects.toThrow();
    });

    it("rejects registration with invalid invite code", async () => {
      await expect(
        client.register({ email: "bad-invite@test.com", password: "pass123", inviteCode: "INVALID" }),
      ).rejects.toThrow();
    });
  });

  describe("AC-3: Email/password login", () => {
    it("registers with valid invite code", async () => {
      const res = await client.register({
        email: TEST_EMAIL,
        password: TEST_PASSWORD,
        inviteCode: TEST_INVITE_CODE,
      });
      token = res.accessToken;
      expect(token).toBeTruthy();
    });

    it("logs in with correct credentials", async () => {
      const res = await client.login({ email: TEST_EMAIL, password: TEST_PASSWORD });
      token = res.accessToken;
      expect(token).toBeTruthy();
    });

    it("gets current user", async () => {
      const authClient = new ApiClient({
        baseUrl: BASE_URL,
        getAccessToken: () => token,
      });
      const user = await authClient.getCurrentUser();
      expect(user.email).toBe(TEST_EMAIL);
    });
  });

  describe("AC-4/5/6/7/8/9/12/13/14: Story project generation", () => {
    let authClient: ApiClient;
    let storyId: string;

    beforeAll(() => {
      authClient = new ApiClient({
        baseUrl: BASE_URL,
        getAccessToken: () => token,
      });
    });

    it("creates a web_novel story project", async () => {
      const project = await authClient.createStoryProject({
        title: "E2E Test Story",
        style: "web_novel",
        targetChapterCount: 3,
      });
      storyId = project.id;
      expect(project.style).toBe("web_novel");
      expect(project.targetChapterCount).toBe(3);
    });

    it("creates an exam_reading story with forced chapter count", async () => {
      const project = await authClient.createStoryProject({
        title: "E2E Exam Reading",
        style: "exam_reading",
        targetChapterCount: 5, // should be forced to 1
      });
      expect(project.style).toBe("exam_reading");
      expect(project.targetChapterCount).toBe(1);
    });

    it("lists story projects", async () => {
      const projects = await authClient.listStoryProjects();
      expect(projects.length).toBeGreaterThanOrEqual(2);
    });

    it("submits target words, generates chapter content, and reads completed output", async () => {
      await authClient.submitChapterTargetWords(storyId, 1, {
        words: [
          { word: "adventure", source: "manual" },
          { word: "courage", source: "manual" },
        ],
      });

      const task = await authClient.generateChapter(storyId, 1);
      expect(task.status).toBe("queued");

      const terminalTask = await waitForTerminalTask(authClient, task.id);
      expect(["completed", "fallback_completed"]).toContain(terminalTask.status);

      const chapter = await authClient.getChapter(storyId, 1);
      expect(chapter.output.englishContent.length).toBeGreaterThan(0);
      expect(chapter.output.highlightedTargetWords).toContain("adventure");
      expect(chapter.output.chineseTranslation.length).toBeGreaterThan(0);

      const result = await authClient.getChapterGenerationResult(storyId, 1);
      expect(result.task.id).toBe(task.id);
      expect(["completed", "fallback_completed"]).toContain(result.task.status);
      expect(result.output.highlightedTargetWords).toContain("adventure");
      expect(result.qualityReport.chapterId).toBe(chapter.id);
      expect(["passed", "fallback_accepted"]).toContain(result.qualityReport.result);
      if (result.task.status === "completed") {
        expect(result.qualityReport.passed).toBe(true);
      }
      expect(result.qualityReport.outOfSyllabusRate).toBeGreaterThanOrEqual(0);
      expect(result.qualityReport.outOfSyllabusRate).toBeLessThanOrEqual(1);
      expect(result.qualityReport.targetWordHits.adventure).toBeGreaterThan(0);
    });
  });

  describe("AC-1: Auth protection", () => {
    it("unauthenticated user cannot create story projects", async () => {
      const unauthClient = new ApiClient({ baseUrl: BASE_URL });
      await expect(
        unauthClient.createStoryProject({
          title: "Should Fail",
          style: "web_novel",
          targetChapterCount: 1,
        }),
      ).rejects.toThrow();
    });
  });
});
