import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const webRoot = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root: resolve(webRoot, "../.."),
  test: {
    environment: "node",
    include: ["tests/e2e/**/*.spec.ts"],
  },
});
