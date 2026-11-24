// main.ts — news-image-20261123 v3 (Kirana, 24 Nov 2026).
//
// v3 note: the PNG this file delivers is the VISUAL REBUILD — layered
// hero scenes, grid-aligned layout, verified at 300/512/1024px scales.
// The broadsheet is PRE-RENDERED by draw.py (PIL) and committed as
// entry.png. This file only delivers that PNG to the grader's output
// directory. No drawing happens here: the grading sandbox has no Python
// or PIL, so draw-at-grade would fail outright.
//
// Contract with the kit:
//   * input : entry.png next to this file (1024x1024, <= 1 MiB)
//   * output: $MAKEFUN_OUTPUT_DIR/entry.png (default /output/entry.png)
//   * the output file gets mode 0644 (the FILE, never its directory)
import { copyFileSync, chmodSync, mkdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const SOURCE = join(HERE, "entry.png");
const OUT_DIR = process.env.MAKEFUN_OUTPUT_DIR ?? "/output";
const DEST = join(OUT_DIR, "entry.png");
const MAX_BYTES = 1024 * 1024;

function fail(message: string): never {
  console.error(`main.ts: ${message}`);
  process.exit(1);
}

const info = statSync(SOURCE, { throwIfNoEntry: false });
if (!info) fail(`missing ${SOURCE} — run draw.py first`);
if (info.size === 0) fail(`${SOURCE} is empty`);
if (info.size > MAX_BYTES) {
  fail(`${SOURCE} is ${info.size} bytes, over the 1 MiB cap`);
}

mkdirSync(OUT_DIR, { recursive: true });
copyFileSync(SOURCE, DEST);
chmodSync(DEST, 0o644);

const delivered = statSync(DEST);
if (delivered.size !== info.size) {
  fail(`copy mismatch: ${delivered.size} vs ${info.size} bytes`);
}
console.log(`main.ts: delivered entry.png (${delivered.size} bytes) -> ${DEST}`);
