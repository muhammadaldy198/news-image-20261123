// main.ts — entrypoint for the news-image-20261123 entry (Hunter Office,
// Kirana). v2 resubmit: the broadsheet is pre-rendered by draw.py from the
// verified Monday 23 November 2026 story list (stories.json) and committed
// beside this file as entry.png; the grader has no Python or PIL, so this
// program's only job is to copy the finished image to /output.
//
// Usage (grader):  node main.ts        → writes /output/entry.png
// Node >= 22, stdlib only. Deterministic: one file in, one file out.
//
// Node 22 runs this file as ESM under type stripping, so the script's own
// directory comes from import.meta.dirname (no __dirname in ESM scope).
// v2: the committed entry.png is the 24 Nov re-render; the copy below
// never re-draws — it only moves the finished broadsheet to /output.

import { chmodSync, copyFileSync, existsSync, mkdirSync, statSync } from "node:fs";
import { join } from "node:path";

const IMAGE = "entry.png";
const OUT_DIR = "/output";
const SIZE_LIMIT = 1024 * 1024;

function sourcePath(): string {
  return join(import.meta.dirname, IMAGE);
}

function outputDir(): string {
  const override = process.env.MAKEFUN_OUTPUT_DIR;
  return override !== undefined && override !== "" ? override : OUT_DIR;
}

function destinationPath(): string {
  return join(outputDir(), IMAGE);
}

function copyBroadsheet(): void {
  const src = sourcePath();
  if (!existsSync(src)) {
    throw new Error(`missing pre-rendered image: ${src}`);
  }
  const bytes = statSync(src).size;
  if (bytes === 0 || bytes > SIZE_LIMIT) {
    throw new Error(`entry.png has an unexpected size: ${bytes} bytes`);
  }
  const dest = destinationPath();
  mkdirSync(outputDir(), { recursive: true });
  copyFileSync(src, dest);
  // Make the copy world-readable so the grader can open it. Only the
  // file gets a mode change: touching the output directory's own mode
  // breaks under the grader's user (EPERM), so leave the directory alone.
  chmodSync(dest, 0o644);
  console.log(`entry.png -> ${dest} (${bytes} bytes)`);
}

copyBroadsheet();
