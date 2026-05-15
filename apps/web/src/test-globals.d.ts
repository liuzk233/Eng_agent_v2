/// <reference types="vitest/globals" />

declare const __dirname: string;

declare module "fs" {
  interface Dirent {
    name: string;
    isDirectory(): boolean;
  }

  const fs: {
    readFileSync(path: string, encoding: BufferEncoding): string;
    readdirSync(path: string): string[];
    readdirSync(path: string, options: { withFileTypes: true }): Dirent[];
  };
  export default fs;
}

declare module "node:fs" {
  export function readFileSync(path: string, encoding: BufferEncoding): string;
}

declare module "path" {
  const path: {
    basename(path: string): string;
    join(...paths: string[]): string;
    resolve(...paths: string[]): string;
  };
  export default path;
}

declare module "node:path" {
  export function dirname(path: string): string;
  export function resolve(...paths: string[]): string;
}

declare module "node:url" {
  export function fileURLToPath(url: string | URL): string;
}
