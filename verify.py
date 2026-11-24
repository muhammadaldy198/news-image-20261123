#!/usr/bin/env python3
"""verify.py — verification for the news-image-20261123 entry (Kirana).

Checks, all offline and deterministic:
  1. render determinism — draw.py twice, byte-identical SHA-256;
  2. gate limits — entry.png is 1024x1024 and <= 1 MiB;
  3. content sanity — grayscale mean/stddev/dark-fraction in sane bands,
     and the 300px downscale still carries signal (thumbnail test);
     NOTE (v3, 24 Nov 2026): the mean band is 175–245, recalibrated from
     200–245 because v3's hero art is deliberately dark night scenes
     (14% of the page at mean ~45). The band still catches a broken
     render (a blacked page scores <100); the dark-fraction cap 0.25 is
     the binding guard against a dark poster.
  4. overlap — the text boxes draw.py logged (DRAW_LOG=1) must not
     intersect (strict area overlap);
  5. data integrity — 39 stories numbered 1..39, Top 10 ranks 1..10,
     masthead date exactly "MONDAY, 23 NOVEMBER 2026", section tags unique.

Run:  ~/workspace/office/.venv/bin/python verify.py
Exit 0 = all checks pass.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageStat

BASE = Path(__file__).resolve().parent
ENTRY = BASE / "entry.png"
DATA = json.loads((BASE / "stories.json").read_text())
VENV_PY = "/home/hatch/workspace/office/.venv/bin/python"

failures = []
notes = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")
    if not ok:
        failures.append(name)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    # 1. determinism: render twice to /tmp, compare hashes
    a, b = "/tmp/news23_verify_a.png", "/tmp/news23_verify_b.png"
    for out in (a, b):
        r = subprocess.run([VENV_PY, str(BASE / "draw.py"), out],
                           capture_output=True, text=True, cwd=BASE)
        if r.returncode != 0:
            print(r.stdout)
            print(r.stderr, file=sys.stderr)
            check("render runs", False, r.stderr.strip().splitlines()[-1])
            return 1
    ha, hb = sha256(a), sha256(b)
    check("determinism (2x render byte-identical)", ha == hb,
          f"sha {ha[:12]}…")
    check("committed entry.png matches fresh render",
          sha256(ENTRY) == ha, f"entry sha {sha256(ENTRY)[:12]}…")

    # 2. gate limits
    im = Image.open(ENTRY)
    check("dimensions 1024x1024", im.size == (1024, 1024), str(im.size))
    size = ENTRY.stat().st_size
    check("size <= 1 MiB", size <= 1048576, f"{size} B ({size / 1024:.0f} KB)")

    # 3. content sanity in grayscale
    g = im.convert("L")
    st = ImageStat.Stat(g)
    mean, std = st.mean[0], st.stddev[0]
    hist = g.histogram()
    dark_frac = sum(hist[:80]) / (1024 * 1024)
    check("grayscale mean in paper band", 175 <= mean <= 245,
          f"mean {mean:.1f}")
    check("grayscale stddev shows content", std > 35, f"stddev {std:.1f}")
    check("dark-pixel fraction sane", 0.02 <= dark_frac <= 0.25,
          f"{dark_frac:.3f}")
    small = g.resize((300, 300), Image.LANCZOS)
    sst = ImageStat.Stat(small)
    check("300px downscale still carries signal", sst.stddev[0] > 25,
          f"stddev {sst.stddev[0]:.1f}")

    # 4. overlap from the logged text boxes
    boxes_path = BASE / "boxes.json"
    if not boxes_path.exists():
        check("boxes.json present (run with DRAW_LOG=1)", False)
    else:
        boxes = json.loads(boxes_path.read_text())
        bad = []
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                _, ax0, ay0, ax1, ay1 = boxes[i]
                _, bx0, by0, bx1, by1 = boxes[j]
                ox = min(ax1, bx1) - max(ax0, bx0)
                oy = min(ay1, by1) - max(ay0, by0)
                if ox > 0 and oy > 0:
                    bad.append((boxes[i][0], boxes[j][0], ox, oy))
        check(f"no text-box overlap ({len(boxes)} boxes)", not bad,
              str(bad[:5]) if bad else "")

    # 5. data integrity
    stories = DATA["stories"]
    check("39 stories", len(stories) == 39, f"{len(stories)}")
    check("stories numbered 1..39",
          [s["n"] for s in stories] == list(range(1, 40)))
    ranks = sorted(s["top10"] for s in stories if s["top10"])
    check("Top 10 ranks 1..10", ranks == list(range(1, 11)))
    check("masthead date exact",
          DATA["date_line"] == "MONDAY, 23 NOVEMBER 2026")
    tags = [h["tag"] for h in DATA["heroes"]] + \
        [c["tag"] for c in DATA["cards"]]
    check("11 section tags unique", len(tags) == len(set(tags)) == 11)
    check("3 heroes + 8 cards",
          len(DATA["heroes"]) == 3 and len(DATA["cards"]) == 8)
    check("all 39 headlines non-empty",
          all(s["headline"].strip() for s in stories))

    print()
    if failures:
        print(f"VERIFY FAILED: {len(failures)} check(s): {failures}")
        return 1
    print("VERIFY OK — all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
