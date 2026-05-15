import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const currentDir = dirname(fileURLToPath(import.meta.url));
const stylesDir = resolve(currentDir, "..");

function readStyle(fileName: string) {
  return readFileSync(resolve(stylesDir, fileName), "utf8");
}

describe("design token styles", () => {
  it("materializes the UI-DESIGN color, type, spacing, radius, and motion tokens", () => {
    const tokens = readStyle("tokens.css");

    expect(tokens).toContain("--color-brand: oklch(0.72 0.16 145);");
    expect(tokens).toContain("--color-bg: oklch(0.985 0.012 92);");
    expect(tokens).toContain("--color-surface: oklch(0.998 0.008 96);");
    expect(tokens).toContain("--color-text-primary: oklch(0.22 0.025 128);");
    expect(tokens).toContain('--font-display: "Fraunces", Georgia, serif;');
    expect(tokens).toContain('--font-body: "Nunito Sans", "Avenir Next", sans-serif;');
    expect(tokens).toContain("--space-sm: 14px;");
    expect(tokens).toContain("--radius-md: 8px;");
    expect(tokens).toContain("--motion-ease-out: cubic-bezier(0.16, 1, 0.3, 1);");
    expect(tokens).toContain("@media (prefers-reduced-motion: reduce)");
  });

  it("keeps forbidden default font families out of the token layer", () => {
    const styles = ["tokens.css", "typography.css", "global.css"].map(readStyle).join("\n");

    expect(styles).not.toMatch(/\b(?:Inter|Roboto|Arial|Helvetica|system-ui)\b/);
  });

  it("connects global styles to tokens and typography", () => {
    const global = readStyle("global.css");
    const typography = readStyle("typography.css");

    expect(global).toContain('@import "./tokens.css";');
    expect(global).toContain('@import "./typography.css";');
    expect(global).toContain("background: var(--color-bg);");
    expect(typography).toContain(".text-reading");
    expect(typography).toContain("max-width: 72ch;");
  });
});
