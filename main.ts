// news-image-20261123 — "THE WORLD, Monday 23 November 2026".
//
// The picture is entry.png, rendered before submit by draw.py (PIL) from
// the verified 23 Nov story list in stories.json. The grader's container
// has no Python or Pillow, so this program only copies the committed PNG
// to the output directory. Node 22, standard library only.
//
// Run locally with MAKEFUN_OUTPUT_DIR standing in for /output:
//   mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts

import { chmodSync, copyFileSync, existsSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, 'entry.png');
const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? '/output';
const dest = join(outDir, 'entry.png');

if (!existsSync(src)) {
  throw new Error(`entry.png missing next to main.ts (${src})`);
}
copyFileSync(src, dest);
// The copied file is ours, so chmod on the file alone is safe — never
// chmod the output directory itself (the grader runs as another user and
// that throws EPERM).
chmodSync(dest, 0o644);
const bytes = statSync(dest).size;
if (bytes === 0) {
  throw new Error('entry.png copied but empty');
}
console.log(`entry.png -> ${dest} (${bytes} bytes)`);
