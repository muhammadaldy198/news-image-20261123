#!/usr/bin/env python3
"""draw.py — news-image-20261123 v3 (Kirana, 24 Nov 2026).

VISUAL REBUILD. v2 was technically clean (verify 16/16, Gate 9 pass) but
visually slop: generic clip-art hero silhouettes, grey-mush density at
300px, weak hierarchy, no focal point. v3 rebuilds the VISUAL LAYER only —
facts come unchanged from stories.json (v2, 39 stories, corrected closes).

Design principles (Alday, 23:09–23:10):
  * ANTI-SLOP — judged on the real render at thumbnail/phone scale.
  * GRID — every box/column/headline sits on one grid; edges aligned,
    baselines aligned, ONE gutter (8px) and ONE margin (12px) everywhere.
  * HEROES DOMINATE — art 156px tall (v2: 80), layered night scenes with
    big contrast masses that still read at 300px.
  * NO COLLISIONS — every text box logged; visual crop check per area.

Render:  python3 draw.py [out.png]   (default: entry.png next to this file)
         DRAW_LOG=1 python3 draw.py  (also writes boxes.json for verify.py)
Deterministic: no unseeded randomness anywhere (hash-based pseudo-random).
"""

import hashlib
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
DATA = json.loads((BASE / "stories.json").read_text())

W = H = 1024
M = 12            # outer margin, all four sides
G = 8             # the ONE gutter between columns/blocks
CW = W - 2 * M    # content width = 1000

# ---------------------------------------------------------------- palette
PAPER = (250, 246, 236)
PANEL = (243, 238, 224)
PANEL_LINE = (196, 186, 164)
INK = (24, 24, 27)
INK_SOFT = (74, 70, 64)
RULE = (150, 142, 124)
RED = (179, 38, 30)
RED_DARK = (140, 28, 22)
NAVY = (13, 27, 46)
NAVY_SOFT = (30, 52, 80)
SEA = (209, 225, 234)
LAND = (233, 221, 193)
LAND_LINE = (176, 160, 120)
WHITE = (255, 255, 255)

# ---------------------------------------------------------------- fonts
FDIR = "/usr/share/fonts/truetype/noto"
_FONTS = {}


def font(name, size):
    key = (name, size)
    if key not in _FONTS:
        _FONTS[key] = ImageFont.truetype(os.path.join(FDIR, name), size)
    return _FONTS[key]


DISPLAY_BLACK = "NotoSerifDisplay-Black.ttf"
DISPLAY_BOLD = "NotoSerifDisplay-Bold.ttf"
DISPLAY_MED = "NotoSerifDisplay-Medium.ttf"
SERIF_BOLD = "NotoSerif-Bold.ttf"
SERIF = "NotoSerif-Regular.ttf"
SERIF_IT = "NotoSerif-Italic.ttf"
SANS = "NotoSans-Regular.ttf"
SANS_MED = "NotoSans-Medium.ttf"
SANS_BOLD = "NotoSans-Bold.ttf"
SANS_BLACK = "NotoSans-Black.ttf"
MONO = "NotoSansMono-Regular.ttf"
MONO_BOLD = "NotoSansMono-Bold.ttf"


# ------------------------------------------------------- deterministic rand
def prand(seed, i, lo=0.0, hi=1.0):
    """Deterministic pseudo-random float in [lo, hi) from (seed, i)."""
    h = hashlib.sha256(f"{seed}:{i}".encode()).digest()
    v = int.from_bytes(h[:4], "big") / 0xFFFFFFFF
    return lo + v * (hi - lo)


def prand_int(seed, i, lo, hi):
    return int(prand(seed, i, lo, hi + 0.999999))


# ---------------------------------------------------------------- box log
class BoxLog:
    """Records tight text boxes; verify.py checks they never overlap."""

    def __init__(self):
        self.boxes = []

    def add(self, name, box):
        x0, y0, x1, y1 = (int(round(v)) for v in box)
        if x1 > x0 and y1 > y0:
            self.boxes.append([name, x0, y0, x1, y1])

    def write(self):
        if os.environ.get("DRAW_LOG") == "1":
            (BASE / "boxes.json").write_text(json.dumps(self.boxes))


LOG = BoxLog()


def txt(d, xy, s, fnt, fill, name):
    """Draw text, log its tight box. Returns (width, height)."""
    x, y = xy
    d.text((x, y), s, font=fnt, fill=fill)
    bb = d.textbbox((x, y), s, font=fnt)
    LOG.add(name, bb)
    return bb[2] - bb[0], bb[3] - bb[1]


def text_w(d, s, fnt):
    bb = d.textbbox((0, 0), s, font=fnt)
    return bb[2] - bb[0]


def wrap(d, s, fnt, width):
    """Greedy wrap; returns list of lines that each fit `width`."""
    words = s.split()
    lines, cur = [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if text_w(d, trial, fnt) <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_lines(d, s, fnt, width, max_lines, shrink_to=None):
    """Wrap to at most max_lines; if it does not fit, shrink the font
    one point at a time down to shrink_to. Returns (lines, font)."""
    f = fnt
    while True:
        lines = wrap(d, s, f, width)
        if len(lines) <= max_lines:
            return lines, f
        if shrink_to is None or f.size <= shrink_to:
            raise AssertionError(f"TEXT DOES NOT FIT ({len(lines)} lines): {s!r}")
        f = font(f.path.rsplit("/", 1)[-1], f.size - 1)


# ------------------------------------------------------------ paint utils
def vgrad(layer, box, top, bottom):
    """Vertical gradient across box (inclusive bands, deterministic)."""
    x0, y0, x1, y1 = box
    h = max(1, y1 - y0)
    d = ImageDraw.Draw(layer)
    for yy in range(y0, y1):
        t = (yy - y0) / h
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        d.line([(x0, yy), (x1 - 1, yy)], fill=c)


def glow(layer, cx, cy, radius, color, peak=200):
    """Soft radial glow: concentric translucent circles, brightest inside."""
    ov = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    steps = 12
    for i in range(steps, 0, -1):
        r = radius * i / steps
        a = int(peak * (1 - i / steps) ** 1.6) + 8
        od.ellipse([cx - r, cy - r, cx + r, cy + r],
                   fill=color + (a,))
    layer.alpha_composite(ov)


def beam(layer, points, color, alpha=60):
    ov = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.polygon(points, fill=color + (alpha,))
    layer.alpha_composite(ov)


def puff(layer, cx, cy, r, color, alpha=150):
    ov = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.ellipse([cx - r, cy - r * 0.72, cx + r, cy + r * 0.72],
               fill=color + (alpha,))
    layer.alpha_composite(ov)


def art_layer(w, h):
    """2x supersampled RGBA layer; paste() downscales it back."""
    return Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))


def paste_art(img, layer, box):
    x0, y0, x1, y1 = box
    small = layer.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    img.paste(small, (x0, y0), small)


def label_bar(d, box, text, fnt):
    """Black caption bar pinned to the bottom-left of an art box."""
    x0, y0, x1, y1 = box
    tw = text_w(d, text, fnt)
    bw, bh = tw + 14, 17
    d.rectangle([x0, y1 - bh, x0 + bw, y1], fill=(12, 12, 14))
    txt(d, (x0 + 7, y1 - bh + 3), text, fnt, (240, 238, 230),
        f"label:{text}")


# ============================================================== HERO ART
# Each painter draws a LAYERED night scene on a 2x RGBA layer.
# Composition rule (anti-slop): one dark ground mass + one bright focal
# mass (explosion/fire/glow) + 2-3 mid-tone shapes + fine detail last.
# Coordinates are relative fractions of the layer size.

def _stars(d, w, h, seed, count, ymax_frac=0.42):
    for i in range(count):
        x = prand(seed, i * 2, 0.02, 0.98) * w
        y = prand(seed, i * 2 + 1, 0.03, ymax_frac) * h
        r = prand(seed, 1000 + i, 0.7, 1.6)
        a = prand_int(seed, 2000 + i, 120, 235)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(225, 232, 240, a))


def _moon(layer, w, h, fx, fy, r):
    cx, cy = w * fx, h * fy
    glow(layer, cx, cy, r * 3.2, (200, 210, 225), peak=70)
    d = ImageDraw.Draw(layer)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(233, 237, 242, 255))
    d.ellipse([cx - r * 0.55, cy - r * 0.3, cx - r * 0.2, cy + r * 0.05],
              fill=(205, 212, 222, 255))
    d.ellipse([cx + r * 0.25, cy + r * 0.35, cx + r * 0.5, cy + r * 0.6],
              fill=(205, 212, 222, 255))


def paint_merkury(layer):
    """Night sea: corvette + sea drones + explosion off Benghazi."""
    w, h = layer.size
    d = ImageDraw.Draw(layer)
    horizon = int(h * 0.47)
    # sky + sea masses (skies lifted off pure black: crushed blacks hide
    # the stars and the horizon line — dusk-navy keeps the night read)
    vgrad(layer, (0, 0, w, horizon), (18, 30, 52), (36, 62, 92))
    vgrad(layer, (0, horizon, w, h), (15, 40, 63), (7, 22, 38))
    _stars(d, w, h, "merkury-stars", 46)
    _moon(layer, w, h, 0.84, 0.15, 15)
    # horizon light band
    d.rectangle([0, horizon - 2, w, horizon + 1], fill=(70, 105, 135, 255))
    # sea wave strokes (3 tones, deterministic)
    for i in range(30):
        y = prand("merk-w", i, horizon + 8, h - 6)
        x = prand("merk-w", 100 + i, 0.02, 0.9) * w
        ln = prand("merk-w", 200 + i, 18, 90)
        tone = prand_int("merk-w", 300 + i, 0, 2)
        col = [(96, 138, 168, 200), (64, 104, 138, 200),
               (130, 170, 198, 170)][tone]
        d.line([(x, y), (x + ln, y)], fill=col, width=2)
    # explosion, left of centre: glow + layered fireball + smoke
    ex, ey = w * 0.30, horizon - 34
    glow(layer, ex, ey, 120, (255, 110, 30), peak=150)
    glow(layer, ex, ey, 60, (255, 190, 80), peak=170)
    for (r, col) in [(34, (196, 52, 18, 255)), (24, (238, 120, 26, 255)),
                     (15, (255, 200, 90, 255)), (8, (255, 246, 210, 255))]:
        d.ellipse([ex - r, ey - r, ex + r, ey + r], fill=col)
    for i, (ox, oy, r) in enumerate([(-30, -34, 22), (4, -48, 26),
                                     (34, -36, 20), (10, -66, 18)]):
        puff(layer, ex + ox, ey + oy, r, (58, 58, 64), alpha=170)
    # corvette, centre-right: hull + superstructure + mast + funnel
    hx0, hx1 = w * 0.50, w * 0.93
    deck = horizon + 6
    hull = [(hx0, deck), (hx0 + 14, deck + 26), (hx1 - 30, deck + 26),
            (hx1, deck + 10), (hx1, deck)]
    d.polygon(hull, fill=(16, 19, 26, 255))
    d.line([(hx0, deck), (hx1, deck)], fill=(120, 130, 145, 255), width=3)
    d.rectangle([hx0 + 70, deck - 26, hx0 + 150, deck], fill=(22, 26, 34, 255))
    d.rectangle([hx0 + 92, deck - 44, hx0 + 128, deck - 26],
                fill=(26, 30, 38, 255))
    d.line([(hx0 + 110, deck - 44), (hx0 + 110, deck - 72)],
           fill=(140, 150, 165, 255), width=3)
    d.line([(hx0 + 96, deck - 66), (hx0 + 124, deck - 66)],
           fill=(140, 150, 165, 255), width=3)
    d.rectangle([hx0 + 158, deck - 34, hx0 + 172, deck],
                fill=(30, 34, 42, 255))
    d.polygon([(hx1 - 34, deck), (hx1 - 12, deck - 12), (hx1 - 4, deck)],
              fill=(20, 23, 30, 255))
    for i in range(6):  # lit portholes
        px = hx0 + 26 + i * 22
        d.ellipse([px - 3, deck + 9, px + 3, deck + 15],
                  fill=(255, 196, 90, 255))
    # bow wake + stern foam
    d.line([(hx1, deck + 22), (hx1 + 34, deck + 40)], fill=(220, 235, 245, 220),
           width=3)
    d.line([(hx1, deck + 22), (hx1 + 30, deck + 8)], fill=(220, 235, 245, 180),
           width=2)
    for i in range(8):
        fx = hx0 - 8 - i * 12
        fy = deck + 24 + prand("merk-foam", i, -3, 3)
        d.line([(fx, fy), (fx + 8, fy)], fill=(210, 228, 240, 200), width=2)
    # sea drones: 3 small hulls with bow wakes, approaching from the left
    for i, (fx, fy, s) in enumerate([(0.10, 0.60, 1.0), (0.20, 0.68, 0.85),
                                     (0.38, 0.56, 0.7)]):
        bx, by = w * fx, h * fy
        hw, hh = 30 * s, 9 * s
        d.polygon([(bx - hw, by), (bx - hw + 8 * s, by + hh),
                   (bx + hw - 6 * s, by + hh), (bx + hw, by)],
                  fill=(12, 14, 20, 255))
        d.rectangle([bx - 4 * s, by - 6 * s, bx + 6 * s, by],
                    fill=(18, 21, 28, 255))
        d.line([(bx + hw, by + hh), (bx + hw + 26 * s, by + hh + 12 * s)],
               fill=(215, 232, 242, 230), width=2)
        d.line([(bx - hw, by + hh), (bx - hw - 20 * s, by + hh + 6 * s)],
               fill=(215, 232, 242, 160), width=2)
    # firelight shimmer on the water under the explosion
    for i in range(10):
        y = horizon + 8 + i * 9
        ww = 120 - i * 8
        d.line([(ex - ww / 2, y), (ex + ww / 2, y)],
               fill=(255, 140, 50, 150 - i * 12), width=2)


def paint_cikande(layer):
    """Factory fire at night: flames, smoke, fire truck, rescuers."""
    w, h = layer.size
    d = ImageDraw.Draw(layer)
    ground = int(h * 0.84)
    # night sky, warm dark (lifted: pure-black sky crushed the smoke)
    vgrad(layer, (0, 0, w, ground), (38, 26, 20), (70, 44, 28))
    _stars(d, w, h, "cik-stars", 22, ymax_frac=0.30)
    # smoke column rising from the roof breach
    sx = w * 0.42
    for i, (oy, r, a) in enumerate([(0, 30, 200), (-34, 38, 180),
                                    (-66, 46, 160), (-96, 54, 140),
                                    (-122, 60, 115)]):
        puff(layer, sx + prand("cik-smoke", i, -14, 14),
             ground - 150 + oy, r, (74, 62, 54), alpha=a)
    # fire glow behind the factory
    glow(layer, sx, ground - 120, 170, (255, 110, 25), peak=130)
    # factory main hall: long block + sawtooth roof
    fx0, fx1 = w * 0.05, w * 0.60
    roof = ground - 108
    d.rectangle([fx0, roof + 26, fx1, ground], fill=(46, 38, 34, 255))
    teeth = []
    x = fx0
    while x < fx1:
        teeth += [(x, roof + 26), (x + 26, roof), (x + 52, roof + 26)]
        x += 52
    d.polygon(teeth, fill=(38, 31, 28, 255))
    d.line([(fx0, roof + 26), (fx1, roof + 26)], fill=(90, 78, 68, 255),
           width=3)
    # windows: grid, some burning bright
    for r in range(2):
        for c in range(9):
            wx = fx0 + 14 + c * 36
            wy = roof + 44 + r * 30
            burn = prand("cik-win", r * 10 + c, 0, 1)
            col = (255, 170, 60, 255) if burn > 0.55 else (28, 24, 22, 255)
            if burn > 0.85:
                col = (255, 220, 110, 255)
            d.rectangle([wx, wy, wx + 20, wy + 16], fill=col)
    # second block + chimney, right
    d.rectangle([w * 0.64, ground - 132, w * 0.90, ground],
                fill=(52, 43, 38, 255))
    for i, col in enumerate([(255, 150, 50, 255), (255, 210, 100, 255),
                             (30, 26, 24, 255)]):
        wx = w * (0.67 + i * 0.065)
        d.rectangle([wx, ground - 120, wx + w * 0.045, ground - 96],
                    fill=col)
    d.rectangle([w * 0.92, ground - 190, w * 0.97, ground],
                fill=(40, 33, 30, 255))
    puff(layer, w * 0.945, ground - 200, 18, (80, 70, 62), alpha=170)
    puff(layer, w * 0.96, ground - 224, 22, (80, 70, 62), alpha=140)
    # flames: layered teardrops at roof breach + two windows
    def flame(cx, cy, s):
        for (sc, col) in [(1.0, (198, 44, 18, 255)),
                          (0.72, (240, 116, 22, 255)),
                          (0.46, (255, 198, 66, 255)),
                          (0.24, (255, 244, 190, 255))]:
            r = 34 * s * sc
            d.polygon([(cx - r, cy), (cx - r * 0.55, cy - r * 1.7),
                       (cx, cy - r * 2.1), (cx + r * 0.55, cy - r * 1.7),
                       (cx + r, cy)], fill=col)
    flame(sx, roof + 26, 1.15)
    flame(w * 0.20, roof + 30, 0.7)
    flame(w * 0.75, ground - 96, 0.55)
    # embers rising
    for i in range(30):
        ex = sx + prand("cik-emb", i, -90, 90)
        ey = roof - prand("cik-emb", 100 + i, 0, 150)
        r = prand("cik-emb", 200 + i, 1.0, 2.6)
        d.ellipse([ex - r, ey - r, ex + r, ey + r],
                  fill=(255, 150, 50, 230))
    # ground band
    d.rectangle([0, ground, w, h], fill=(18, 15, 13, 255))
    d.line([(0, ground), (w, ground)], fill=(120, 90, 60, 255), width=2)
    # fire truck: body + cab + ladder + wheels
    tx0, ty = w * 0.58, ground + 6
    d.rectangle([tx0, ty, tx0 + 150, ty + 26], fill=(178, 34, 26, 255))
    d.rectangle([tx0 + 118, ty - 16, tx0 + 150, ty + 26],
                fill=(150, 28, 22, 255))
    d.rectangle([tx0 + 124, ty - 12, tx0 + 144, ty - 2],
                fill=(180, 220, 240, 255))
    d.line([(tx0 + 10, ty), (tx0 + 96, ty - 52)], fill=(200, 200, 205, 255),
           width=4)
    for i in range(4):
        lx = tx0 + 22 + i * 20
        ly = ty - 10 - i * 11
        d.line([(lx, ly), (lx + 8, ly - 4)], fill=(200, 200, 205, 255),
               width=2)
    for wx in (tx0 + 24, tx0 + 66, tx0 + 122):
        d.ellipse([wx - 9, ty + 20, wx + 9, ty + 38], fill=(10, 10, 12, 255))
        d.ellipse([wx - 4, ty + 25, wx + 4, ty + 33], fill=(140, 140, 145, 255))
    # water arc: dotted pale arc from ladder tip toward the fire
    for i in range(16):
        t = i / 15
        ax = tx0 + 96 - t * 150
        ay = ty - 52 - t * 26 + t * t * 60
        d.ellipse([ax - 2, ay - 2, ax + 2, ay + 2],
                  fill=(170, 215, 240, 220))
    # two rescuer silhouettes with helmets
    for rx in (w * 0.30, w * 0.36):
        d.ellipse([rx - 7, ground + 2, rx + 7, ground + 16],
                  fill=(8, 8, 10, 255))
        d.polygon([(rx - 11, ground + 8), (rx + 11, ground + 8),
                   (rx + 6, ground + 2), (rx - 6, ground + 2)],
                  fill=(255, 200, 40, 255))
        d.rectangle([rx - 6, ground + 16, rx + 6, ground + 40],
                    fill=(8, 8, 10, 255))


def paint_dymer(layer):
    """Night air war: apartment blocks, drones, searchlights, rubble."""
    w, h = layer.size
    d = ImageDraw.Draw(layer)
    ground = int(h * 0.86)
    # night sky (lifted: pure-black sky crushed the beams and drones)
    vgrad(layer, (0, 0, w, ground), (16, 22, 40), (34, 48, 72))
    _stars(d, w, h, "dym-stars", 34, ymax_frac=0.34)
    # searchlight beams from the ground, narrow and faint (wide beams
    # read as a grey roof at thumbnail scale — draft 2 lesson)
    beam(layer, [(w * 0.07, ground), (w * 0.09, ground),
                 (w * 0.40, h * 0.08), (w * 0.36, h * 0.08)],
         (255, 244, 200), alpha=24)
    beam(layer, [(w * 0.93, ground), (w * 0.91, ground),
                 (w * 0.60, h * 0.08), (w * 0.64, h * 0.08)],
         (255, 244, 200), alpha=20)
    # explosion glow high in the sky, above the damaged block
    glow(layer, w * 0.48, h * 0.30, 110, (255, 120, 30), peak=110)
    # apartment blocks: 3 masses, window grids, one damaged top
    def block(x0, x1, top, damaged=False):
        d.rectangle([x0, top, x1, ground], fill=(26, 32, 46, 255))
        d.rectangle([x0, top, x1, top + 6], fill=(44, 52, 70, 255))
        if damaged:
            jag = [(x0, top), (x0 + 22, top - 16), (x0 + 44, top - 4),
                   (x0 + 66, top - 20), (x0 + 90, top - 6),
                   (x0 + 112, top - 14), (x1, top - 2), (x1, top + 10),
                   (x0, top + 10)]
            d.polygon(jag, fill=(26, 32, 46, 255))
            puff(layer, x0 + 56, top - 26, 20, (70, 70, 78), alpha=160)
            puff(layer, x0 + 84, top - 44, 24, (70, 70, 78), alpha=130)
        cols = int((x1 - x0 - 16) // 20)
        rows = int((ground - top - 16) // 22)
        for r in range(rows):
            for c in range(cols):
                wx = x0 + 10 + c * 20
                wy = top + 14 + r * 22
                lit = prand("dym-win", r * 1000 + c * 10 + int(x0), 0, 1)
                col = (255, 190, 85, 255) if lit > 0.62 else (14, 18, 28, 255)
                d.rectangle([wx, wy, wx + 11, wy + 13], fill=col)
    block(w * 0.04, w * 0.30, h * 0.30)
    block(w * 0.34, w * 0.62, h * 0.44, damaged=True)
    block(w * 0.66, w * 0.95, h * 0.26)
    # drones: small quadcopters with rotor dots + red light
    for i, (fx, fy, s) in enumerate([(0.16, 0.14, 1.0), (0.48, 0.20, 0.8),
                                     (0.72, 0.12, 1.1), (0.88, 0.22, 0.7)]):
        cx, cy = w * fx, h * fy
        arm = 14 * s
        d.line([(cx - arm, cy - arm), (cx + arm, cy + arm)],
               fill=(8, 8, 10, 255), width=3)
        d.line([(cx - arm, cy + arm), (cx + arm, cy - arm)],
               fill=(8, 8, 10, 255), width=3)
        for (ox, oy) in [(-arm, -arm), (arm, -arm), (-arm, arm), (arm, arm)]:
            d.ellipse([cx + ox - 4, cy + oy - 4, cx + ox + 4, cy + oy + 4],
                      fill=(120, 130, 145, 255))
        d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(255, 60, 50, 255))
    # rubble mound + tilted slab at the base
    d.polygon([(w * 0.30, ground), (w * 0.42, ground - 34),
               (w * 0.56, ground - 26), (w * 0.68, ground)],
              fill=(16, 18, 24, 255))
    for i in range(12):
        rx = prand("dym-rub", i, 0.32, 0.66) * w
        ry = ground - prand("dym-rub", 100 + i, 2, 26)
        d.line([(rx, ry), (rx + 10, ry - 4)], fill=(90, 96, 110, 255),
               width=2)
    slab = [(w * 0.60, ground - 30), (w * 0.64, ground - 52),
            (w * 0.70, ground - 48), (w * 0.66, ground - 26)]
    d.polygon(slab, fill=(40, 44, 56, 255))
    # ground band
    d.rectangle([0, ground, w, h], fill=(12, 13, 18, 255))
    d.line([(0, ground), (w, ground)], fill=(90, 100, 120, 255), width=2)


# ============================================================== WORLD MAP
# Simplified continent outlines (lon/lat), drawn equirectangular.
# Deliberately rough — recognisable at 560px wide, not a survey map.
CONTINENTS = [
    # North America
    [(-168, 66), (-155, 58), (-140, 60), (-130, 54), (-125, 49), (-124, 42),
     (-120, 35), (-114, 29), (-110, 24), (-105, 20), (-97, 16), (-92, 15),
     (-87, 13), (-83, 9), (-79, 9), (-80, 7), (-77, 8), (-75, 11),
     (-70, 12), (-64, 10), (-61, 9), (-55, 5), (-52, 5), (-60, 8),
     (-62, 11), (-68, 12), (-72, 12), (-76, 18), (-79, 22), (-81, 25),
     (-84, 30), (-89, 30), (-91, 29), (-94, 29), (-97, 26), (-97, 22),
     (-105, 20), (-110, 23), (-114, 28), (-117, 33), (-122, 37),
     (-124, 41), (-124, 48), (-132, 56), (-140, 60), (-152, 58),
     (-162, 58), (-168, 66)],
    # South America
    [(-79, 9), (-75, 11), (-71, 12), (-64, 10), (-60, 8), (-54, 6),
     (-50, 4), (-44, -3), (-38, -5), (-35, -8), (-38, -13), (-40, -20),
     (-48, -27), (-52, -33), (-57, -38), (-62, -41), (-65, -45),
     (-68, -50), (-69, -54), (-72, -54), (-73, -44), (-73, -37),
     (-71, -30), (-70, -20), (-75, -15), (-77, -12), (-81, -6),
     (-81, -1), (-80, 4), (-79, 9)],
    # Africa
    [(-17, 15), (-16, 21), (-10, 31), (-6, 35), (0, 36), (10, 37),
     (11, 34), (15, 32), (20, 32), (25, 32), (30, 31), (32, 31),
     (35, 28), (37, 22), (39, 18), (43, 12), (48, 11), (51, 12),
     (46, 5), (41, -2), (40, -10), (36, -18), (33, -26), (28, -33),
     (20, -35), (17, -32), (15, -27), (12, -18), (13, -12), (12, -6),
     (9, -1), (9, 4), (6, 4), (0, 6), (-8, 4), (-13, 8), (-17, 15)],
    # Eurasia
    [(-10, 36), (-9, 38), (-9, 43), (-2, 44), (-2, 48), (-4, 50),
     (0, 51), (2, 53), (5, 58), (8, 57), (10, 59), (18, 56),
     (21, 55), (24, 58), (28, 60), (30, 62), (28, 66), (32, 70),
     (40, 68), (48, 69), (58, 69), (68, 73), (75, 73), (85, 75),
     (95, 77), (105, 77), (115, 74), (125, 72), (135, 72), (145, 72),
     (155, 70), (165, 68), (175, 66), (178, 65), (172, 62), (162, 60),
     (158, 52), (150, 46), (142, 50), (140, 40), (135, 35), (129, 35),
     (126, 38), (122, 32), (120, 28), (116, 23), (110, 20), (108, 15),
     (105, 10), (103, 8), (100, 7), (99, 10), (98, 14), (96, 16),
     (93, 17), (91, 22), (88, 22), (86, 20), (83, 18), (80, 15),
     (78, 8), (76, 9), (73, 20), (70, 21), (67, 24), (62, 25),
     (58, 26), (54, 27), (51, 28), (49, 30), (47, 30), (44, 29),
     (40, 30), (37, 32), (36, 36), (33, 36), (30, 36), (28, 37),
     (24, 36), (22, 37), (19, 40), (16, 40), (14, 38), (12, 38),
     (10, 44), (7, 44), (3, 43), (0, 39), (-2, 37), (-6, 36), (-9, 37),
     (-10, 36)],
    # United Kingdom
    [(-5, 50), (-3, 53), (-5, 56), (-4, 58), (-2, 58), (-1, 57),
     (1, 53), (1, 51), (-1, 50), (-5, 50)],
    # Japan
    [(130, 31), (132, 33), (134, 34), (137, 35), (139, 35), (141, 39),
     (142, 42), (144, 44), (142, 45), (140, 41), (138, 38), (136, 36),
     (133, 35), (131, 33), (130, 31)],
    # Borneo
    [(109, 1), (113, 4), (117, 6), (119, 2), (117, -3), (112, -3),
     (109, -1), (109, 1)],
    # Sumatra
    [(95, 5), (98, 3), (101, 0), (104, -3), (106, -6), (104, -6),
     (101, -2), (98, 1), (95, 5)],
    # Java
    [(105, -6), (110, -7), (114, -8), (114, -9), (109, -8), (105, -7),
     (105, -6)],
    # New Guinea
    [(131, -1), (136, -2), (141, -3), (146, -6), (150, -10), (147, -9),
     (141, -8), (136, -6), (131, -3), (131, -1)],
    # Australia
    [(113, -22), (114, -28), (115, -33), (118, -35), (124, -33),
     (129, -32), (132, -32), (135, -35), (138, -35), (140, -38),
     (145, -38), (150, -37), (153, -30), (153, -27), (151, -24),
     (146, -19), (142, -15), (142, -11), (140, -17), (136, -12),
     (132, -12), (130, -13), (126, -14), (122, -17), (118, -20),
     (113, -22)],
    # New Zealand
    [(167, -45), (169, -43), (172, -41), (174, -39), (176, -38),
     (178, -38), (175, -40), (173, -42), (170, -44), (168, -46),
     (167, -45)],
]

# Per-pin label placement (dx, dy in px from the pin centre, + leader).
# Tuned so no two labels touch at the map's 560x92 size.
PIN_LABEL = {
    3: (8, 8),      # Merkury — label down-right (keeps clear of Dymer pin)
    14: (8, -14),   # Cikande — label up-right
    4: (-8, -14),   # NATO — label up-left (keeps clear of Dymer)
    5: (8, -14),    # Dymer — label up-right
    15: (8, -4),    # India-Nepal — label right
    16: (8, -14),   # Nasdaq — label up-right
    28: (-8, -24),  # NZ — label high up-left (COP31 pin sits below it)
    30: (-8, 6),    # 49ers — label left, below pin (keeps clear of Ariane)
    36: (8, -14),   # Ariane — label up-right
    1: (-30, 6),    # COP31 — label far left, below pin
}

# Short display labels for the map (full text stays in the Top-10 list).
MAP_LABEL_SHORT = {28: "NZ draw"}


def paint_map(d, box):
    """Sea + continents + numbered pins + labels. Returns nothing."""
    x0, y0, x1, y1 = box
    mw, mh = x1 - x0, y1 - y0

    def proj(lon, lat):
        px = x0 + (lon + 180.0) / 360.0 * mw
        py = y0 + (72.0 - lat) / 122.0 * mh
        return px, py

    d.rectangle(box, fill=SEA)
    for poly in CONTINENTS:
        pts = [proj(lon, lat) for lon, lat in poly]
        d.polygon(pts, fill=LAND, outline=LAND_LINE)
    # graticule: equator + tropics, faint
    for lat in (0, 23.4, -23.4):
        _, gy = proj(0, lat)
        d.line([(x0, gy), (x1, gy)], fill=(178, 200, 214, 255), width=1)
    # pins + labels
    f_pin = font(SANS_BLACK, 11)
    f_lab = font(SANS_BOLD, 9)
    pins = [s for s in DATA["stories"] if s.get("lat") is not None]
    for s in sorted(pins, key=lambda p: p["top10"]):
        px, py = proj(s["lon"], s["lat"])
        r = 9
        d.ellipse([px - r, py - r, px + r, py + r], fill=NAVY,
                  outline=WHITE, width=2)
        num = str(s["top10"])
        nw = text_w(d, num, f_pin)
        txt(d, (px - nw / 2, py - 7), num, f_pin, WHITE, f"pin:{s['n']}")
        dx, dy = PIN_LABEL[s["n"]]
        lx = px + dx + (10 if dx > 0 else -10)
        ly = py + dy
        lab = MAP_LABEL_SHORT.get(s["n"], s["map_label"])
        lw = text_w(d, lab, f_lab)
        if dx < 0:
            lx -= lw
        # clamp inside the map box
        lx = max(x0 + 2, min(lx, x1 - lw - 2))
        ly = max(y0 + 1, min(ly, y1 - 11))
        d.line([(px, py), (lx + (lw if dx < 0 else 0), ly + 5)],
               fill=INK_SOFT, width=1)
        txt(d, (lx, ly), lab, f_lab, INK, f"maplabel:{s['n']}")


# ============================================================== CARD ICONS
# Bold 2-3 element pictograms on 2x layers. No text inside icons.

def paint_icon(tag, layer):
    w, h = layer.size
    d = ImageDraw.Draw(layer)
    cx, cy = w / 2, h / 2
    if tag == "NATO DESK":  # radar sweep + blips + jet
        d.ellipse([cx - 34, cy - 34, cx + 34, cy + 34],
                  fill=(28, 68, 44, 255))
        d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26],
                  outline=(90, 200, 130, 255), width=3)
        d.ellipse([cx - 13, cy - 13, cx + 13, cy + 13],
                  outline=(90, 200, 130, 255), width=2)
        d.polygon([(cx, cy), (cx + 30, cy - 18), (cx + 12, cy + 6)],
                  fill=(140, 235, 170, 255))
        for (bx, by) in [(-16, -10), (8, 14), (-6, 18)]:
            d.ellipse([cx + bx - 3, cy + by - 3, cx + bx + 3, cy + by + 3],
                      fill=(180, 255, 200, 255))
        d.polygon([(cx + 44, cy - 26), (cx + 62, cy - 20), (cx + 44, cy - 16)],
                  fill=(40, 40, 46, 255))
    elif tag == "CLIMATE DESK":  # globe + rising red arrow
        d.ellipse([cx - 30, cy - 30, cx + 30, cy + 30],
                  fill=(52, 110, 160, 255))
        d.ellipse([cx - 30, cy - 10, cx - 2, cy + 12],
                  fill=(96, 160, 90, 255))
        d.ellipse([cx + 6, cy - 24, cx + 26, cy - 4],
                  fill=(96, 160, 90, 255))
        d.ellipse([cx - 30, cy - 30, cx + 30, cy + 30],
                  outline=(24, 60, 96, 255), width=3)
        d.line([(cx + 30, cy + 26), (cx + 56, cy - 6)],
               fill=RED + (255,), width=6)
        d.polygon([(cx + 56, cy - 6), (cx + 42, cy - 8), (cx + 54, cy + 8)],
                  fill=RED + (255,))
    elif tag == "THE PITCH":  # cricket bat + ball + stumps
        d.line([(cx - 34, cy + 30), (cx - 2, cy - 34)],
               fill=(196, 158, 104, 255), width=12)
        d.line([(cx - 2, cy - 34), (cx + 8, cy - 52)],
               fill=(120, 84, 50, 255), width=6)
        d.ellipse([cx + 22, cy - 8, cx + 44, cy + 14],
                  fill=(178, 40, 34, 255))
        for sx in (cx + 20, cx + 30, cx + 40):
            d.line([(sx, cy + 18), (sx, cy + 40)],
                   fill=(230, 200, 120, 255), width=4)
    elif tag == "DIPLOMACY":  # two flags
        d.line([(cx - 26, cy - 40), (cx - 26, cy + 40)],
               fill=(90, 84, 74, 255), width=4)
        d.line([(cx + 26, cy - 40), (cx + 26, cy + 40)],
               fill=(90, 84, 74, 255), width=4)
        for i, col in enumerate([(255, 153, 51), (255, 255, 255),
                                 (19, 136, 8)]):
            d.rectangle([cx - 26, cy - 40 + i * 11, cx + 2,
                         cy - 29 + i * 11], fill=col + (255,))
        d.ellipse([cx - 16, cy - 24, cx - 8, cy - 16],
                  outline=(0, 0, 128, 255), width=2)
        d.polygon([(cx + 26, cy - 40), (cx + 58, cy - 30), (cx + 26, cy - 20),
                   (cx + 48, cy - 12), (cx + 26, cy - 4)],
                  fill=(220, 20, 60, 255))
    elif tag == "THE GRIDIRON":  # field + football
        d.rectangle([cx - 40, cy - 26, cx + 40, cy + 26],
                    fill=(36, 122, 58, 255))
        for i in range(5):
            lx = cx - 32 + i * 16
            d.line([(lx, cy - 26), (lx, cy + 26)],
                   fill=(235, 240, 235, 255), width=2)
        d.ellipse([cx - 26, cy - 12, cx + 26, cy + 12],
                  fill=(139, 90, 43, 255))
        d.line([(cx - 12, cy), (cx + 12, cy)], fill=(240, 235, 225, 255),
               width=2)
        for lx in (-8, -3, 2, 7):
            d.line([(cx + lx, cy - 4), (cx + lx, cy + 4)],
                   fill=(240, 235, 225, 255), width=2)
    elif tag == "MARKETS":  # ascending bars, last one red
        base = cy + 30
        for i, bh in enumerate([18, 28, 38, 52]):
            bx = cx - 36 + i * 19
            col = RED + (255,) if i == 3 else (36, 110, 62, 255)
            d.rectangle([bx, base - bh, bx + 14, base], fill=col)
        d.line([(cx - 40, base + 4), (cx + 40, base + 4)],
               fill=(60, 58, 54, 255), width=3)
        d.line([(cx - 38, cy - 28), (cx + 38, cy - 44)],
               fill=(36, 110, 62, 255), width=4)
        d.polygon([(cx + 38, cy - 44), (cx + 26, cy - 44), (cx + 38, cy - 32)],
                  fill=(36, 110, 62, 255))
    elif tag == "LAUNCH PAD":  # rocket + tower + smoke
        d.rectangle([cx - 8, cy - 44, cx + 8, cy + 18],
                    fill=(232, 234, 236, 255))
        d.polygon([(cx - 8, cy - 44), (cx, cy - 62), (cx + 8, cy - 44)],
                  fill=RED + (255,))
        d.polygon([(cx - 8, cy + 6), (cx - 20, cy + 24), (cx - 8, cy + 18)],
                  fill=(180, 60, 50, 255))
        d.polygon([(cx + 8, cy + 6), (cx + 20, cy + 24), (cx + 8, cy + 18)],
                  fill=(180, 60, 50, 255))
        d.line([(cx + 26, cy - 48), (cx + 26, cy + 26)],
               fill=(120, 122, 128, 255), width=5)
        for i in range(4):
            d.line([(cx + 20, cy - 40 + i * 16), (cx + 32, cy - 40 + i * 16)],
                   fill=(120, 122, 128, 255), width=3)
        for (ox, r) in [(-14, 10), (0, 13), (14, 10)]:
            d.ellipse([cx + ox - r, cy + 26 - r, cx + ox + r, cy + 26 + r],
                      fill=(200, 200, 205, 255))
        d.line([(cx - 34, cy + 40), (cx + 34, cy + 40)],
               fill=(90, 88, 84, 255), width=3)
    elif tag == "THE HARDWOOD":  # basketball + hoop
        d.ellipse([cx - 30, cy - 30, cx + 30, cy + 30],
                  fill=(226, 114, 44, 255))
        d.ellipse([cx - 30, cy - 30, cx + 30, cy + 30],
                  outline=(120, 60, 20, 255), width=3)
        d.line([(cx - 30, cy), (cx + 30, cy)], fill=(120, 60, 20, 255),
               width=3)
        d.line([(cx, cy - 30), (cx, cy + 30)], fill=(120, 60, 20, 255),
               width=3)
        d.arc([cx - 30, cy - 30, cx + 30, cy + 30], 300, 60,
              fill=(120, 60, 20, 255), width=3)
        d.rectangle([cx + 30, cy - 34, cx + 58, cy - 6],
                    outline=(240, 240, 240, 255), width=4)
        d.line([(cx + 34, cy - 6), (cx + 54, cy - 6)],
               fill=(226, 114, 44, 255), width=4)
        d.line([(cx + 38, cy - 6), (cx + 42, cy + 8)],
               fill=(240, 240, 240, 255), width=2)
        d.line([(cx + 50, cy - 6), (cx + 46, cy + 8)],
               fill=(240, 240, 240, 255), width=2)
    else:  # fallback: plain disc (should never happen)
        d.ellipse([cx - 24, cy - 24, cx + 24, cy + 24], fill=NAVY_SOFT)


# ============================================================== GRID
# ONE budget table drives every y position. Gaps between sections are
# exactly 4px (2px where a rule already separates). Assert sum == 1024.
BUDGET = [
    ("top", 8), ("kicker", 18), ("gap", 2), ("masthead", 80), ("gap", 2),
    ("strip", 14), ("gap", 4), ("heroes", 288), ("gap", 4), ("maprow", 108),
    ("fold", 4), ("gap", 4), ("index", 68), ("gap", 4), ("briefhead", 16),
    ("gap", 2), ("brief", 158), ("gap", 4), ("cards1", 56), ("gap", 4),
    ("cards2", 56), ("gap", 4), ("timeline", 24), ("gap", 4), ("ticker", 24),
    ("gap", 4), ("datecheck", 42), ("gap", 2), ("footer", 16),
]
assert sum(h for _, h in BUDGET) == H, "budget must sum to 1024"

Y = {}
_cursor = 0
for _name, _h in BUDGET:
    Y[_name] = _cursor
    _cursor += _h

HERO_PAINT = {"NAVAL WAR": paint_merkury, "DISASTER": paint_cikande,
              "AIR WAR": paint_dymer}
HERO_LABEL = {"NAVAL WAR": "BENGHAZI, LIBYA", "DISASTER": "CIKANDE, BANTEN",
              "AIR WAR": "DYMER, KYIV REGION"}


def tracked_text(d, cx, y, s, fnt, fill, track, name):
    """Centre text with letter tracking; log its TIGHT ink box."""
    widths = [text_w(d, ch, fnt) for ch in s]
    total = sum(widths) + track * (len(s) - 1)
    x = cx - total / 2
    x0 = x
    boxes = []
    for ch, wd in zip(s, widths):
        d.text((x, y), ch, font=fnt, fill=fill)
        boxes.append(d.textbbox((x, y), ch, font=fnt))
        x += wd + track
    tight = (min(b[0] for b in boxes), min(b[1] for b in boxes),
             max(b[2] for b in boxes), max(b[3] for b in boxes))
    LOG.add(name, tight)
    return total


def render_kicker(img, d):
    y0, y1 = Y["kicker"], Y["kicker"] + 18
    d.rectangle([M, y0, M + CW, y1], fill=NAVY)
    f = font(MONO_BOLD, 10)
    s = DATA["kicker"]
    w = text_w(d, s, f)
    txt(d, (M + (CW - w) / 2, y0 + 4), s, f, (232, 230, 222), "kicker")


def render_masthead(img, d):
    y0 = Y["masthead"]
    # ears: boxed, 108 wide, same height as the title block
    ear_w, ear_h = 108, 68
    ear_y = y0 + 6
    f_ear_b = font(SANS_BLACK, 13)
    f_ear = font(SANS_BOLD, 10)
    for (ex, lines) in [(M, [("MONDAY", f_ear_b), ("23 NOV", f_ear_b),
                             ("2026", f_ear)]),
                        (M + CW - ear_w, [("39", f_ear_b),
                                           ("STORIES", f_ear),
                                           ("7 REGIONS", f_ear)])]:
        d.rectangle([ex, ear_y, ex + ear_w, ear_y + ear_h],
                    outline=RULE, width=1)
        ly = ear_y + 9
        for (s, f) in lines:
            w = text_w(d, s, f)
            txt(d, (ex + (ear_w - w) / 2, ly), s, f, INK, f"ear:{s}")
            ly += 18
    # title, tracked, centred between the ears
    cx = M + CW / 2
    tracked_text(d, cx, y0 + 2, DATA["edition"],
                 font(DISPLAY_BLACK, 52), INK, 6, "masthead")
    f_date = font(SERIF_BOLD, 14)
    dl = DATA["date_line"]
    w = text_w(d, dl, f_date)
    txt(d, (cx - w / 2, y0 + 62), dl, f_date, RED, "dateline")
    # double rule under the masthead
    d.line([(M, y0 + 78), (M + CW, y0 + 78)], fill=INK, width=2)
    d.line([(M, y0 + 79), (M + CW, y0 + 79)], fill=INK, width=1)


def render_strip(img, d):
    y0 = Y["strip"]
    counts = {"EU": 11, "AS": 7, "ME": 2, "AM": 7, "AF": 3, "OC": 4, "WD": 5}
    names = {"EU": "EUROPE", "AS": "ASIA", "ME": "MIDDLE EAST",
             "AM": "AMERICAS", "AF": "AFRICA", "OC": "OCEANIA", "WD": "WORLD"}
    s = "  ·  ".join(f"{names[k]} {counts[k]}" for k in
                     ["EU", "AS", "ME", "AM", "AF", "OC", "WD"])
    f = font(SANS_BOLD, 10)
    w = text_w(d, s, f)
    d.line([(M, y0), (M + CW, y0)], fill=RULE, width=1)
    txt(d, (M + (CW - w) / 2, y0 + 2), s, f, INK_SOFT, "strip")
    d.line([(M, y0 + 13), (M + CW, y0 + 13)], fill=RULE, width=1)


def render_heroes(img, d):
    y0 = Y["heroes"]
    col_w = (CW - 2 * G) // 3  # 328
    f_kick = font(SANS_BOLD, 11)
    f_num = font(SANS_BLACK, 10)
    f_tag = font(SANS_BLACK, 10)
    f_crit = font(SANS_BLACK, 8)
    f_deck = font(SERIF, 12)
    for i, hero in enumerate(DATA["heroes"]):
        x0 = M + i * (col_w + G)
        x1 = x0 + col_w
        d.rectangle([x0, y0, x1, y0 + 288], outline=RULE, width=1)
        ix0, ix1 = x0 + 6, x1 - 6  # inner text edges (6px panel padding)
        # kicker row: number badge + kicker + CRITICAL ribbon
        ky = y0 + 6
        d.ellipse([ix0, ky, ix0 + 16, ky + 16], fill=NAVY)
        num = str(hero["n"])
        nw = text_w(d, num, f_num)
        txt(d, (ix0 + (16 - nw) / 2, ky + 3), num, f_num, WHITE,
            f"hero-num:{hero['n']}")
        txt(d, (ix0 + 21, ky + 2), hero["kicker"], f_kick, INK_SOFT,
            f"hero-kicker:{hero['n']}")
        if hero.get("critical"):
            rw = 62
            d.rectangle([ix1 - rw, ky, ix1, ky + 16], fill=RED)
            cw = text_w(d, "CRITICAL", f_crit)
            txt(d, (ix1 - rw + (rw - cw) / 2, ky + 4), "CRITICAL", f_crit,
                WHITE, f"hero-crit:{hero['n']}")
        # tag row
        ty = ky + 18
        txt(d, (ix0, ty), hero["tag"], f_tag, RED, f"hero-tag:{hero['n']}")
        d.line([(ix0, ty + 13), (ix1, ty + 13)], fill=PANEL_LINE, width=1)
        # art: 156 tall, layered scene + label bar
        ay0, ay1 = ty + 17, ty + 17 + 156
        layer = art_layer(col_w - 12, 156)
        HERO_PAINT[hero["tag"]](layer)
        paste_art(img, layer, (ix0, ay0, ix1, ay1))
        d.rectangle([ix0, ay0, ix1, ay1], outline=INK_SOFT, width=1)
        label_bar(d, (ix0, ay0, ix1, ay1), HERO_LABEL[hero["tag"]],
                  font(SANS_BOLD, 9))
        # headline: 2 lines max, shrink 26 -> 23 if needed
        hy = ay1 + 6
        lines, hf = fit_lines(d, hero["headline"], font(DISPLAY_BLACK, 26),
                              ix1 - ix0, 2, shrink_to=23)
        for j, ln in enumerate(lines):
            txt(d, (ix0, hy + j * 27), ln, hf, INK,
                f"hero-head:{hero['n']}:{j}")
        # deck: 2 lines max, plain serif (no drop cap in v3)
        dy = hy + 54 + 3
        dlines, df = fit_lines(d, hero["deck"], f_deck, ix1 - ix0, 2,
                               shrink_to=11)
        for j, ln in enumerate(dlines):
            txt(d, (ix0, dy + j * 13), ln, df, INK_SOFT,
                f"hero-deck:{hero['n']}:{j}")


def render_maprow(img, d):
    y0 = Y["maprow"]
    # row header spanning list + map
    f_head = font(SANS_BLACK, 10)
    txt(d, (M, y0 + 1), "WHERE IT HAPPENED — THE TOP 10, PINNED",
        f_head, INK, "maprow-head")
    # Top-10 list (left, 196 wide)
    lx0, lx1 = M, M + 196
    f_row = font(SANS, 9)
    f_rowb = font(SANS_BOLD, 9)
    top10 = sorted([s for s in DATA["stories"] if s["top10"]],
                   key=lambda s: s["top10"])
    ry = y0 + 14
    for s in top10:
        rank = f"{s['top10']}."
        txt(d, (lx0, ry), rank, f_rowb, RED, f"top10:{s['n']}")
        txt(d, (lx0 + 14, ry), s["map_label"], f_row, INK,
            f"top10lab:{s['n']}")
        ry += 9.4
    # map (centre, 560 wide)
    mx0, mx1 = M + 196 + G, M + 196 + G + 560
    paint_map(d, (mx0, y0 + 14, mx1, y0 + 108))
    d.rectangle([mx0, y0 + 14, mx1, y0 + 108], outline=RULE, width=1)
    # numbers + market bars (right, 228 wide)
    nx0, nx1 = mx1 + G, M + CW
    f_nh = font(SANS_BLACK, 10)
    f_num = font(SERIF_BOLD, 17)
    f_lab = font(SANS, 9)
    txt(d, (nx0, y0 + 1), "BY THE NUMBERS", f_nh, RED, "numbers-head")
    ny = y0 + 14
    for (val, lab) in DATA["numbers_table"]:
        vw = text_w(d, val, f_num)
        txt(d, (nx0 + 44 - vw, ny), val, f_num, INK, f"num:{val}")
        txt(d, (nx0 + 50, ny + 4), lab, f_lab, INK_SOFT, f"numlab:{val}")
        ny += 14
    d.line([(nx0, ny + 1), (nx1, ny + 1)], fill=PANEL_LINE, width=1)
    txt(d, (nx0, ny + 4), "MONDAY'S CLOSE — WALL STREET", f_nh, RED,
        "bars-head")
    f_bar = font(MONO_BOLD, 8)
    by = ny + 17
    for (name, val, pct) in DATA["market_bars"]:
        txt(d, (nx0, by), name, f_bar, INK_SOFT, f"bar:{name}")
        bx0 = nx0 + 56
        bw = int(pct / 31.0 * 118)
        col = RED if name == "NVIDIA" else (36, 110, 62)
        d.rectangle([bx0, by + 1, bx0 + bw, by + 7], fill=col)
        txt(d, (bx0 + bw + 5, by), val, f_bar, INK, f"barval:{name}")
        by += 8.2


def render_fold(img, d):
    y = Y["fold"] + 2
    x = M
    while x < M + CW:
        d.line([(x, y), (min(x + 8, M + CW), y)], fill=RULE, width=1)
        x += 14
    f = font(SANS_BOLD, 8)
    w = text_w(d, "FOLD", f)
    cx = M + CW / 2
    d.rectangle([cx - w / 2 - 6, y - 6, cx + w / 2 + 6, y + 6], fill=PAPER)
    txt(d, (cx - w / 2, y - 5), "FOLD", f, INK_SOFT, "fold")


def render_index(img, d):
    y0 = Y["index"]
    col_w = (CW - 2 * G) // 3  # 328
    f_head = font(SANS_BLACK, 10)
    # INSIDE TODAY — two columns x three rows (single-column 6-row pitch
    # collided at 8px; index entries are abbreviated like a real paper)
    INSIDE_SHORT = {"A1": "Merkury sunk", "A2": "Cikande: 24 dead",
                    "B1": "NATO AWACS", "C1": "Nasdaq +6.5%",
                    "D1": "NZ draw; 49ers", "D2": "Ariane scrubbed"}
    x0 = M
    d.rectangle([x0, y0, x0 + col_w, y0 + 68], outline=RULE, width=1)
    txt(d, (x0 + 6, y0 + 3), "INSIDE TODAY", f_head, INK, "inside-head")
    f_row = font(SANS, 8)
    pairs = [("A1", "A2"), ("B1", "C1"), ("D1", "D2")]
    for ri, (left, right) in enumerate(pairs):
        ry = y0 + 17 + ri * 16
        txt(d, (x0 + 6, ry), f"{left}  {INSIDE_SHORT[left]}", f_row,
            INK_SOFT, f"inside:{left}")
        txt(d, (x0 + 168, ry), f"{right}  {INSIDE_SHORT[right]}", f_row,
            INK_SOFT, f"inside:{right}")
    # QUOTE OF THE DAY
    x0 = M + col_w + G
    d.rectangle([x0, y0, x0 + col_w, y0 + 68], outline=RULE, width=1)
    txt(d, (x0 + 6, y0 + 3), "QUOTE OF THE DAY", f_head, INK, "quote-head")
    f_q = font(SERIF_IT, 13)
    qlines, _ = fit_lines(d, DATA["quote_of_day"], f_q, col_w - 12, 2,
                          shrink_to=11)
    for j, ln in enumerate(qlines):
        txt(d, (x0 + 6, y0 + 18 + j * 15), ln, f_q, INK, f"quote:{j}")
    txt(d, (x0 + 6, y0 + 51), DATA["quote_attribution"], font(SANS, 9),
        INK_SOFT, "quote-attr")
    # TOMORROW
    x0 = M + 2 * (col_w + G)
    d.rectangle([x0, y0, x0 + col_w, y0 + 68], outline=RULE, width=1)
    txt(d, (x0 + 6, y0 + 3), "TOMORROW — TUESDAY 24 NOV", f_head, INK,
        "tom-head")
    f_t = font(SANS, 9)
    ry = y0 + 17
    for line in DATA["tomorrow"]:
        txt(d, (x0 + 6, ry), line, f_t, INK_SOFT, f"tom:{line[:8]}")
        ry += 12


REGION_COL = {"EU": (30, 52, 80), "AS": (0, 110, 110), "ME": (140, 90, 40),
              "AM": (36, 110, 62), "AF": (200, 110, 30), "OC": (110, 70, 140),
              "WD": (100, 98, 94)}


def render_briefhead(img, d):
    y0 = Y["briefhead"]
    f = font(DISPLAY_BLACK, 14)
    txt(d, (M, y0 + 1), "THE DAY IN BRIEF", f, INK, "brief-head")
    tw = text_w(d, "THE DAY IN BRIEF", f)
    d.line([(M + tw + 10, y0 + 8), (M + CW, y0 + 8)], fill=INK, width=1)


def render_brief(img, d):
    y0 = Y["brief"]
    featured = {h["n"] for h in DATA["heroes"]} | \
        {c["n"] for c in DATA["cards"]}
    brief = [s for s in DATA["stories"] if s["n"] not in featured]
    assert len(brief) == 28, f"expected 28 brief stories, got {len(brief)}"
    cols = [brief[0:10], brief[10:19], brief[19:28]]
    col_w = (CW - 2 * G) // 3
    f_num = font(SANS_BLACK, 11)
    f_chip = font(SANS_BLACK, 8)
    f_head = font(SERIF_BOLD, 12)
    pitch = 158 / 10
    for ci, col in enumerate(cols):
        x0 = M + ci * (col_w + G)
        for ri, s in enumerate(col):
            ry = y0 + ri * pitch
            num = f"{s['n']}."
            txt(d, (x0, ry + 1), num, f_num, RED, f"brief-num:{s['n']}")
            chip_x = x0 + 20
            d.rectangle([chip_x, ry + 2, chip_x + 22, ry + 13],
                        fill=REGION_COL[s["region"]])
            cw = text_w(d, s["region"], f_chip)
            txt(d, (chip_x + (22 - cw) / 2, ry + 3), s["region"], f_chip,
                WHITE, f"brief-chip:{s['n']}")
            lines, hf = fit_lines(d, s["headline"], f_head, col_w - 46, 1,
                                  shrink_to=10)
            txt(d, (x0 + 46, ry + 1), lines[0], hf, INK,
                f"brief-head:{s['n']}")


def render_cards(img, d, row):
    y0 = Y["cards1" if row == 0 else "cards2"]
    cards = DATA["cards"][row * 4:(row + 1) * 4]
    card_w = (CW - 3 * G) // 4  # 244
    f_tag = font(SANS_BLACK, 9)
    f_head = font(SERIF_BOLD, 11)
    f_cap = font(SANS, 8)
    for i, c in enumerate(cards):
        x0 = M + i * (card_w + G)
        x1 = x0 + card_w
        d.rectangle([x0, y0, x1, y0 + 56], outline=RULE, width=1)
        # icon, 44x44, supersampled
        layer = art_layer(44, 44)
        paint_icon(c["tag"], layer)
        paste_art(img, layer, (x0 + 5, y0 + 6, x0 + 49, y0 + 50))
        d.rectangle([x0 + 5, y0 + 6, x0 + 49, y0 + 50],
                    outline=PANEL_LINE, width=1)
        tx0, tx1 = x0 + 55, x1 - 5
        txt(d, (tx0, y0 + 2), c["tag"], f_tag, RED, f"card-tag:{c['n']}")
        lines, hf = fit_lines(d, c["headline"], f_head, tx1 - tx0, 2,
                              shrink_to=10)
        for j, ln in enumerate(lines):
            txt(d, (tx0, y0 + 12.5 + j * 12.5), ln, hf, INK,
                f"card-head:{c['n']}:{j}")
        clines, cf = fit_lines(d, c["caption"], f_cap, tx1 - tx0, 2,
                               shrink_to=8)
        for j, ln in enumerate(clines):
            txt(d, (tx0, y0 + 38 + j * 9), ln, cf, INK_SOFT,
                f"card-cap:{c['n']}:{j}")


def render_timeline(img, d):
    y0 = Y["timeline"]
    f_lab = font(SANS_BLACK, 9)
    f_t = font(MONO_BOLD, 8)
    f_e = font(SANS, 8)
    txt(d, (M, y0 + 7), "THE DAY IN UTC", f_lab, INK, "tl-lab")
    lx0, lx1 = M + 96, M + CW
    ly = y0 + 13
    d.line([(lx0, ly), (lx1, ly)], fill=RULE, width=1)
    slots = DATA["timeline"]
    span = lx1 - lx0
    for i, (t, ev) in enumerate(slots):
        cx = lx0 + (i + 0.5) * span / len(slots)
        d.ellipse([cx - 3, ly - 3, cx + 3, ly + 3], fill=RED)
        tw = text_w(d, t, f_t)
        txt(d, (cx - tw / 2, y0 + 1), t, f_t, INK, f"tl-time:{t}")
        ew = text_w(d, ev, f_e)
        assert ew <= span / len(slots) - 8, f"timeline event too wide: {ev}"
        txt(d, (cx - ew / 2, y0 + 15), ev, f_e, INK_SOFT, f"tl-ev:{t}")


def render_ticker(img, d):
    y0 = Y["ticker"]
    d.rectangle([M, y0, M + CW, y0 + 24], fill=NAVY)
    s = DATA["ticker"]
    size = 11
    while text_w(d, s, font(MONO_BOLD, size)) > CW - 16 and size > 9:
        size -= 1
    f = font(MONO_BOLD, size)
    w = text_w(d, s, f)
    txt(d, (M + (CW - w) / 2, y0 + 6), s, f, (232, 230, 222), "ticker")


def render_datecheck(img, d):
    y0 = Y["datecheck"]
    d.rectangle([M, y0, M + CW, y0 + 42], outline=RED, width=1)
    f_h = font(SANS_BLACK, 10)
    txt(d, (M + 6, y0 + 2), "DATE CHECK — WHAT WE LEFT OUT ON PURPOSE",
        f_h, RED, "dc-head")
    f_t = font(SANS, 9)
    half = (CW - 12) // 2
    for j, key in enumerate(["date_check_left", "date_check_right"]):
        x0 = M + 6 + j * (half + 6)
        lines, tf = fit_lines(d, DATA[key], f_t, half, 3, shrink_to=8)
        for k, ln in enumerate(lines):
            txt(d, (x0, y0 + 13 + k * 10), ln, tf, INK_SOFT,
                f"dc:{key}:{k}")


def render_footer(img, d):
    y0 = Y["footer"]
    f_b = font(SERIF_BOLD, 9)
    f_s = font(SANS, 7)
    s = DATA["footer_bold"]
    w = text_w(d, s, f_b)
    txt(d, (M + (CW - w) / 2, y0), s, f_b, INK, "footer-bold")
    s2 = DATA["footer_small"]
    w2 = text_w(d, s2, f_s)
    txt(d, (M + (CW - w2) / 2, y0 + 9), s2, f_s, INK_SOFT, "footer-small")


def main():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    render_kicker(img, d)
    render_masthead(img, d)
    render_strip(img, d)
    render_heroes(img, d)
    render_maprow(img, d)
    render_fold(img, d)
    render_index(img, d)
    render_briefhead(img, d)
    render_brief(img, d)
    render_cards(img, d, 0)
    render_cards(img, d, 1)
    render_timeline(img, d)
    render_ticker(img, d)
    render_datecheck(img, d)
    render_footer(img, d)
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "entry.png"
    img.save(out, optimize=True)
    LOG.write()
    print(f"wrote {out} ({out.stat().st_size} B, {len(LOG.boxes)} boxes)")


if __name__ == "__main__":
    main()
