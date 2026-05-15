import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

const SRC_DIR = path.resolve(__dirname, "..");

function getAllTsxFiles(dir: string): string[] {
  const files: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...getAllTsxFiles(full));
    } else if (entry.name.endsWith(".tsx") && !entry.name.includes(".test.")) {
      files.push(full);
    }
  }
  return files;
}

function getImplementationCssFiles(dir: string): string[] {
  const files: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...getImplementationCssFiles(full));
    } else if (entry.name.endsWith(".css") && !full.replace(/\\/g, "/").includes("/styles/")) {
      files.push(full);
    }
  }
  return files;
}

describe("UI Anti-Patterns", () => {
  const tsxFiles = getAllTsxFiles(SRC_DIR);
  const implementationCssFiles = getImplementationCssFiles(SRC_DIR);

  it("no component uses const styles = {}", () => {
    for (const file of tsxFiles) {
      const content = fs.readFileSync(file, "utf-8");
      expect(
        content,
        `${path.basename(file)} uses const styles = {}`,
      ).not.toMatch(/const\s+styles\s*=\s*\{/);
    }
  });

  it("no component uses scrollIntoView", () => {
    for (const file of tsxFiles) {
      const content = fs.readFileSync(file, "utf-8");
      expect(
        content,
        `${path.basename(file)} uses scrollIntoView`,
      ).not.toContain("scrollIntoView");
    }
  });

  it("no component uses Object.assign(window", () => {
    for (const file of tsxFiles) {
      const content = fs.readFileSync(file, "utf-8");
      expect(
        content,
        `${path.basename(file)} uses Object.assign(window`,
      ).not.toMatch(/Object\.assign\s*\(\s*window/);
    }
  });

  it("no hardcoded hex colors in component code", () => {
    for (const file of [...tsxFiles, ...implementationCssFiles]) {
      const content = fs.readFileSync(file, "utf-8");
      expect(
        content,
        `${path.basename(file)} has hardcoded hex color`,
      ).not.toMatch(/#[0-9a-fA-F]{3,8}(?!;?\s*\/)/);
    }
  });

  it("no raw rgb or rgba colors in implementation styles", () => {
    for (const file of implementationCssFiles) {
      const content = fs.readFileSync(file, "utf-8");
      expect(
        content,
        `${path.basename(file)} has raw rgb/rgba color`,
      ).not.toMatch(/rgba?\s*\(/);
    }
  });

  it("no decorative gradients in implementation styles", () => {
    for (const file of implementationCssFiles) {
      const content = fs.readFileSync(file, "utf-8");
      expect(
        content,
        `${path.basename(file)} has decorative gradient`,
      ).not.toMatch(/(?:linear|radial)-gradient\s*\(/);
    }
  });

  it("no static card drop shadows in component code", () => {
    for (const file of tsxFiles) {
      const content = fs.readFileSync(file, "utf-8");
      expect(
        content,
        `${path.basename(file)} has static box-shadow`,
      ).not.toMatch(/box-shadow\s*:\s*(?!var\()/);
    }
  });

  it("fallback_completed does not show '失败'", () => {
    const indicator = fs.readFileSync(
      path.join(SRC_DIR, "features/generation/GenerationStatusIndicator.tsx"),
      "utf-8",
    );
    const fallbackEntry = indicator.match(/fallback_completed.*?label.*?"([^"]+)"/);
    if (fallbackEntry) {
      expect(fallbackEntry[1]).not.toContain("失败");
    }
  });

  it("no emoji used as icon in buttons", () => {
    for (const file of tsxFiles) {
      const content = fs.readFileSync(file, "utf-8");
      const buttonMatches = content.matchAll(/<button[^>]*>([^<]+)<\/button>/g);
      for (const match of buttonMatches) {
        const text = match[1].trim();
        expect(
          text,
          `${path.basename(file)} button uses emoji: ${text}`,
        ).not.toMatch(/[\u{1F300}-\u{1F9FF}]/u);
      }
    }
  });
});
