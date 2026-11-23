#!/usr/bin/env python3
"""draw.py — renderer for the news-image-20261123 entry (Hunter Office, Kirana).

Renders a 1024x1024 broadsheet front page ("THE WORLD — Monday, 23 November
2026") with PIL, from the verified 23 Nov 2026 story list in stories.json
(39 stories, 32 STRONG, 7 regions). The PNG is committed beside this script;
main.ts only copies it.

Written from scratch in this session. Layout is my own design, built from the
office research (Nadia's verified data + Dimas's template hunt): masthead with
ears, section strip, 3 hero panels (Merkury halftone, Cikande, Dymer), pull
quote, pinned world map + framed numbers table, fold line, Inside-Today index
+ Quote of the Day + Tomorrow boxes, 3 brief columns, 2 rows of illustrated
mini-cards (every Top 10 story illustrated), UTC timeline, dark ticker strip,
DATE CHECK box, footer. 39 stories, 12 illustration elements.

Run:  ~/workspace/office/.venv/bin/python draw.py [out.png]
Fonts are render-time tools only (system Noto/DejaVu); they are NOT part of
the entry. Output is deterministic: same bytes every run.
"""

import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1024
BASE = Path(__file__).resolve().parent
DATA = json.loads((BASE / "stories.json").read_text())
STORIES = DATA["stories"]
HEROES = DATA["heroes"]
CARDS = DATA["cards"]

# ---------------------------------------------------------------- palette
PAPER = (250, 246, 236)      # warm newsprint
INK = (18, 18, 18)           # near-black text
NAVY = (24, 38, 68)          # masthead band / headers
NAVY_SOFT = (38, 58, 100)
RED = (179, 38, 30)          # ONE spot colour (#B3261E)
RED_SOFT = (252, 234, 234)   # date-check fill
RULE = (122, 112, 92)        # hairline rules
SEA = (214, 226, 236)        # map sea
LAND = (233, 223, 192)       # map land
LAND_EDGE = (170, 158, 120)
GREY = (88, 86, 80)          # secondary text
PANEL = (244, 239, 224)      # hero/card panel background
WHITE = (255, 255, 255)

REGION_COLOURS = {
    "EU": (46, 80, 140),
    "AS": (156, 84, 20),
    "ME": (140, 40, 40),
    "AM": (32, 110, 70),
    "AF": (110, 70, 140),
    "OC": (20, 120, 130),
    "WD": (70, 70, 70),
}
REGION_NAMES = {
    "EU": "EUROPE", "AS": "ASIA", "ME": "MIDDLE EAST", "AM": "AMERICAS",
    "AF": "AFRICA", "OC": "OCEANIA", "WD": "WORLD",
}

# ---------------------------------------------------------------- fonts
NOTO = "/usr/share/fonts/truetype/noto/"
DEJ = "/usr/share/fonts/truetype/dejavu/"
FONTS = {
    "display_black": ("NotoSerifDisplay-Black.ttf", "DejaVuSerif-Bold.ttf"),
    "display_bold": ("NotoSerifDisplay-Bold.ttf", "DejaVuSerif-Bold.ttf"),
    "serif_bold": ("NotoSerif-Bold.ttf", "DejaVuSerif-Bold.ttf"),
    "serif": ("NotoSerif-Regular.ttf", "DejaVuSerif.ttf"),
    "serif_italic": ("NotoSerif-Italic.ttf", "DejaVuSerif.ttf"),
    "sans_bold": ("NotoSans-Bold.ttf", "DejaVuSans-Bold.ttf"),
    "sans_semi": ("NotoSans-SemiBold.ttf", "DejaVuSans-Bold.ttf"),
    "sans": ("NotoSans-Regular.ttf", "DejaVuSans.ttf"),
    "mono_bold": ("NotoSansMono-Bold.ttf", "DejaVuSansMono-Bold.ttf"),
    "mono": ("NotoSansMono-Regular.ttf", "DejaVuSansMono.ttf"),
}
_font_cache = {}


def font(kind, size):
    """Noto first (OFL, installed on the VM), DejaVu fallback."""
    key = (kind, size)
    if key in _font_cache:
        return _font_cache[key]
    for name in FONTS[kind]:
        for base in (NOTO, DEJ):
            p = Path(base) / name
            if p.exists():
                try:
                    f = ImageFont.truetype(str(p), size)
                    _font_cache[key] = f
                    return f
                except OSError:
                    continue
    f = ImageFont.load_default()
    _font_cache[key] = f
    return f


# ---------------------------------------------------------------- text helpers
def text_w(draw, s, f):
    return draw.textlength(s, font=f)


def wrap(draw, text, f, max_w):
    """Greedy word wrap by pixel width. Returns list of lines."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if text_w(draw, trial, f) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_font(draw, text, max_w, start, minimum, kind="sans_bold"):
    """Largest font size in [minimum, start] letting text fit one line."""
    size = start
    while size > minimum and text_w(draw, text, font(kind, size)) > max_w:
        size -= 1
    return font(kind, size)


def draw_wrapped(draw, x, y, text, f, max_w, fill, leading=None):
    """Draw wrapped text; returns total height used."""
    lines = wrap(draw, text, f, max_w)
    lh = leading or int(f.size * 1.22)
    for i, line in enumerate(lines):
        draw.text((x, y + i * lh), line, font=f, fill=fill)
    return len(lines) * lh


def centre(draw, y, text, f, fill, cx=W // 2):
    draw.text((cx - text_w(draw, text, f) / 2, y), text, font=f, fill=fill)


# ------------------------------------------------------- box log (verify.py)
BOXES = []


def log_box(label, x0, y0, x1, y1):
    """Record a text block's bounding box for the overlap check."""
    if os.environ.get("DRAW_LOG"):
        BOXES.append([label, round(x0), round(y0), round(x1), round(y1)])


# ---------------------------------------------------------------- halftone
def halftone(layer, pitch=4):
    """Dot-screen engraving of a rendered layer: black dots on white.

    Genuine halftone (not a filter): each pitch x pitch block becomes one
    dot whose radius follows the block's mean luminance. Holds up when the
    page is shrunk to ~300px, where the dots still read as texture.
    """
    g = layer.convert("L")
    w, h = g.size
    out = Image.new("RGB", (w, h), WHITE)
    d = ImageDraw.Draw(out)
    px = g.load()
    for y in range(0, h, pitch):
        for x in range(0, w, pitch):
            s, n = 0, 0
            for dy in range(pitch):
                for dx in range(pitch):
                    if x + dx < w and y + dy < h:
                        s += px[x + dx, y + dy]
                        n += 1
            lum = s / max(n, 1)
            r = (1.0 - lum / 255.0) * (pitch * 0.72)
            if r > 0.4:
                cx, cy = x + pitch / 2, y + pitch / 2
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=INK)
    return out


# ---------------------------------------------------------------- map data
# Coarse continent outlines (lon, lat) for the schematic map — my own
# simplified tracings, not a copied dataset.
CONTINENTS = [
    # North America
    [(-168, 66), (-140, 70), (-125, 72), (-95, 72), (-80, 73), (-60, 52),
     (-65, 45), (-75, 35), (-81, 25), (-90, 21), (-97, 26), (-105, 22),
     (-114, 29), (-124, 42), (-135, 57), (-150, 61), (-165, 60)],
    # South America
    [(-79, 9), (-60, 8), (-50, 4), (-35, -8), (-48, -27), (-57, -38),
     (-69, -52), (-73, -44), (-70, -30), (-75, -15), (-80, -3)],
    # Africa
    [(-17, 15), (-10, 31), (3, 37), (10, 37), (20, 32), (32, 31), (35, 18),
     (43, 12), (51, 10), (40, -10), (35, -20), (28, -33), (20, -35),
     (14, -22), (12, -12), (9, 4), (-8, 4), (-13, 8)],
    # Eurasia
    [(-10, 36), (-2, 48), (5, 53), (10, 59), (21, 55), (32, 70), (60, 69),
     (90, 75), (120, 73), (150, 70), (178, 65), (165, 60), (158, 52),
     (142, 50), (140, 40), (128, 38), (121, 28), (109, 20), (105, 9),
     (100, 6), (94, 17), (88, 22), (80, 15), (77, 8), (72, 20), (64, 25),
     (54, 27), (48, 30), (39, 21), (35, 28), (30, 36), (23, 36), (16, 38),
     (8, 44), (3, 43), (-2, 37), (-9, 37)],
    # Britain
    [(-5, 50), (-3, 53), (-5, 56), (-1, 57), (1, 51)],
    # Japan
    [(130, 31), (133, 34), (137, 35), (141, 39), (144, 44), (140, 38),
     (135, 34)],
    # Australia
    [(114, -22), (115, -33), (124, -33), (132, -32), (138, -35), (145, -38),
     (150, -37), (153, -27), (146, -19), (142, -11), (135, -15), (130, -13),
     (122, -17)],
    # New Zealand
    [(167, -45), (172, -41), (176, -38), (174, -41), (170, -44)],
    # Indonesia
    [(95, 5), (100, 0), (105, -5), (110, -7), (114, -8), (122, -10),
     (128, -8), (136, -2), (141, -1), (130, 0), (120, 0), (110, 2)],
    # Madagascar
    [(44, -16), (47, -15), (50, -16), (47, -25), (44, -20)],
    # Greenland
    [(-45, 60), (-32, 68), (-22, 70), (-30, 78), (-45, 77), (-58, 70),
     (-55, 64)],
]


def region_counts():
    counts = {}
    for s in STORIES:
        counts[s["region"]] = counts.get(s["region"], 0) + 1
    return counts


# ------------------------------------------------------------- hero art
def _label_bar(draw, x, y, w, text):
    """Small black bar + white label inside an illustration's bottom edge."""
    f = font("sans_bold", 10)
    tw = text_w(draw, text, f)
    draw.rectangle([x, y, x + tw + 12, y + 14], fill=INK)
    draw.text((x + 6, y + 2), text, font=f, fill=WHITE)


def _drone(draw, cx, cy, s=1.0):
    """Quadcopter silhouette: 4 arms, 4 rotors, body, 2 legs."""
    for ax, ay in ((-9, -5), (9, -5), (-9, 5), (9, 5)):
        ax, ay = ax * s, ay * s
        draw.line([cx, cy, cx + ax, cy + ay], fill=INK, width=1)
        draw.ellipse([cx + ax - 5 * s, cy + ay - 1, cx + ax + 5 * s,
                      cy + ay + 1], fill=(70, 70, 70))
    draw.rounded_rectangle([cx - 5 * s, cy - 2, cx + 5 * s, cy + 3],
                           radius=2, fill=INK)
    draw.line([cx - 3 * s, cy + 3, cx - 3 * s, cy + 6], fill=INK, width=1)
    draw.line([cx + 3 * s, cy + 3, cx + 3 * s, cy + 6], fill=INK, width=1)


def paint_merkury_scene(draw, x, y, w, h):
    """Capsized corvette at Benghazi: keel up, smoke, flames, dark sea.

    Drawn to be halftoned afterwards: mid-tone sky, dark sea and hull,
    pale smoke — the dot screen keeps the shapes readable at 300px.
    """
    draw.rectangle([x, y, x + w, y + h], fill=(198, 212, 222))
    draw.rectangle([x, y + h - 30, x + w, y + h], fill=(70, 110, 150))
    for wx in range(x + 10, x + w - 10, 36):
        draw.arc([wx, y + h - 24, wx + 26, y + h - 8], 180, 360,
                 fill=WHITE, width=2)
    # smoke column, top right (light grey, so the halftone stays airy)
    for cx, cy, r in ((x + 228, y + 12, 12), (x + 248, y + 6, 14),
                      (x + 268, y + 14, 11), (x + 242, y + 24, 10)):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(185, 185, 185))
    # flames above the upturned deck, clear of the hull
    for fx, fh, col in ((150, 24, (235, 120, 25)), (172, 30, (245, 175, 35)),
                        (192, 22, (235, 120, 25))):
        draw.polygon([(x + fx - 10, y + h - 56), (x + fx, y + h - 56 - fh),
                      (x + fx + 10, y + h - 56)], fill=col)
    # capsized hull: smaller, mid-grey (halftones to texture, not a slab),
    # flat deck line on top, works hanging below it
    hx, hy = x + 70, y + h - 56
    hull = (120, 125, 135)
    draw.polygon([(hx, hy), (hx + 150, hy), (hx + 136, hy + 18),
                  (hx + 14, hy + 18)], fill=hull)
    draw.rectangle([hx + 30, hy + 18, hx + 52, hy + 30], fill=hull)
    draw.rectangle([hx + 98, hy + 18, hx + 120, hy + 30], fill=hull)
    draw.line([hx + 75, hy, hx + 75, hy - 18], fill=hull, width=4)
    # white portholes + waterline so the hull keeps structure in dots
    for px in range(hx + 22, hx + 140, 20):
        draw.ellipse([px, hy + 6, px + 5, hy + 11], fill=WHITE)
    draw.line([hx + 10, hy + 18, hx + 140, hy + 18], fill=WHITE, width=1)
    # a sea drone circling the wreck, top left
    _drone(draw, x + 42, y + 18, s=0.9)


def paint_cikande(draw, x, y, w, h):
    """Factory at dusk: chimney smoke, fire-lit windows, searchlight beam,
    rubble at the base. Respectful: no bodies drawn."""
    draw.rectangle([x, y, x + w, y + h], fill=(234, 222, 200))
    # searchlight beam from top right
    draw.polygon([(x + 254, y), (x + w, y), (x + 264, y + 34),
                  (x + 256, y + 34)], fill=(250, 238, 170))
    # factory block + chimney
    draw.rectangle([x + 14, y + 34, x + 150, y + h], fill=(118, 108, 92))
    draw.rectangle([x + 158, y + 14, x + 172, y + h], fill=(98, 90, 76))
    draw.rectangle([x + 150, y + 10, x + 180, y + 16], fill=(98, 90, 76))
    # smoke puffs above the chimney
    for cx, cy, r in ((165, 8, 5), (172, 4, 4), (158, 5, 4)):
        draw.ellipse([x + cx - r, y + cy - r, x + cx + r, y + cy + r],
                     fill=(150, 150, 150))
    # fire-lit windows in two rows
    for wy in (44, 58):
        for wx in (26, 48, 70, 92, 114, 132):
            draw.rectangle([x + wx, y + wy, x + wx + 12, y + wy + 9],
                           fill=(240, 120, 20))
    # second block, right, with a collapsed roofline
    draw.polygon([(x + 190, y + h), (x + 190, y + 52), (x + 214, y + 40),
                  (x + 236, y + 54), (x + 262, y + 44), (x + 286, y + 56),
                  (x + 300, y + h)], fill=(88, 84, 78))
    # rubble triangles at the base
    draw.polygon([(x + 180, y + h), (x + 215, y + h - 22), (x + 250, y + h)],
                 fill=(150, 145, 130))
    draw.polygon([(x + 240, y + h), (x + 272, y + h - 16), (x + 304, y + h)],
                 fill=(170, 164, 148))
    _label_bar(draw, x + 8, y + h - 16, w, "CIKANDE, BANTEN")


def paint_dymer(draw, x, y, w, h):
    """Apartment blocks at dawn: the middle one broken open, drones above,
    dust and rubble below. The 7-year-old's rescue is the story, told by
    the standing blocks around the broken one."""
    draw.rectangle([x, y, x + w, y + h], fill=(232, 228, 216))
    _drone(draw, x + 250, y + 12, s=0.9)
    _drone(draw, x + 210, y + 28, s=0.75)
    # standing blocks, left and right
    for bx, bw, bh in ((14, 72, 62), (228, 72, 80)):
        draw.rectangle([x + bx, y + h - bh, x + bx + bw, y + h],
                       fill=(92, 102, 118))
        for wy in range(y + h - bh + 10, y + h - 8, 15):
            for wx in range(x + bx + 8, x + bx + bw - 8, 15):
                draw.rectangle([wx, wy, wx + 7, wy + 9],
                               fill=(250, 220, 120))
    # broken middle block: jagged top, dark interior, rubble at the base
    mx = x + 98
    draw.polygon([(mx, y + h), (mx, y + 58), (mx + 22, y + 42),
                  (mx + 38, y + 56), (mx + 60, y + 38), (mx + 82, y + 54),
                  (mx + 104, y + 44), (mx + 110, y + h)],
                 fill=(68, 74, 86))
    for wy in range(y + 62, y + h - 8, 15):
        for wx in range(mx + 8, mx + 102, 15):
            draw.rectangle([wx, wy, wx + 7, wy + 9], fill=(250, 220, 120))
    draw.polygon([(mx - 4, y + h), (mx + 30, y + h - 24), (mx + 60, y + h)],
                 fill=(150, 145, 130))
    draw.polygon([(mx + 52, y + h), (mx + 88, y + h - 18), (mx + 114, y + h)],
                 fill=(170, 164, 148))
    _label_bar(draw, x + 8, y + h - 16, w, "DYMER, KYIV REGION")


HERO_PAINTERS = {3: paint_merkury_scene, 14: paint_cikande, 5: paint_dymer}


# ------------------------------------------------------------- mini-cards
def paint_nato(draw, x, y, w, h):
    """NATO council table: round table, five flags, one document."""
    draw.rectangle([x, y, x + w, y + h], fill=(24, 38, 68))
    draw.ellipse([x + 4, y + 26, x + w - 4, y + 46], fill=(120, 130, 150))
    draw.rectangle([x + 16, y + 30, x + 40, y + 40], fill=WHITE)
    draw.line([x + 28, y + 30, x + 28, y + 36], fill=RED, width=1)
    for fx in (8, 18, 28, 38, 46):
        draw.line([x + fx, y + 8, x + fx, y + 22], fill=WHITE, width=1)
        draw.rectangle([x + fx, y + 8, x + fx + 6, y + 13], fill=(80, 140, 220))
    draw.text((x + 4, y + h - 12), "NAC", font=font("sans_bold", 9),
              fill=WHITE)


def paint_cop31(draw, x, y, w, h):
    """The blame game: globe above two podiums, red arrows crossing."""
    draw.rectangle([x, y, x + w, y + h], fill=(221, 232, 240))
    gx, gy, r = x + 28, y + 20, 15
    draw.ellipse([gx - r, gy - r, gx + r, gy + r], fill=(168, 200, 220),
                 outline=NAVY, width=1)
    draw.ellipse([gx - 10, gy - 9, gx - 2, gy + 1], fill=(110, 160, 110))
    draw.ellipse([gx + 2, gy + 3, gx + 11, gy + 12], fill=(110, 160, 110))
    # two podiums
    draw.rectangle([x + 6, y + 34, x + 22, y + h - 4], fill=(90, 90, 96))
    draw.rectangle([x + 34, y + 34, x + 50, y + h - 4], fill=(90, 90, 96))
    # crossed red arrows = the argument
    draw.line([x + 10, y + 30, x + 46, y + 16], fill=RED, width=2)
    draw.line([x + 46, y + 30, x + 10, y + 16], fill=RED, width=2)
    draw.text((x + 4, y + 2), "BOWEN?", font=font("sans_bold", 9), fill=RED)


def paint_cricket(draw, x, y, w, h):
    """Cricket pitch: stumps, bat, red ball on green."""
    draw.rectangle([x, y, x + w, y + h], fill=(60, 140, 70))
    draw.rectangle([x + 20, y + 6, x + 36, y + 46], fill=(200, 180, 140))
    draw.line([x + 20, y + 14, x + 36, y + 14], fill=WHITE, width=1)
    draw.line([x + 20, y + 38, x + 36, y + 38], fill=WHITE, width=1)
    for sx in (24, 27, 30):
        draw.rectangle([x + sx, y + 8, x + sx + 2, y + 16],
                       fill=(250, 220, 60))
    draw.polygon([(x + 40, y + 44), (x + 44, y + 28), (x + 48, y + 30),
                  (x + 44, y + 44)], fill=(210, 180, 130))
    draw.line([x + 46, y + 28, x + 48, y + 22], fill=(150, 120, 80), width=2)
    draw.ellipse([x + 10, y + 34, x + 16, y + 40], fill=(180, 30, 30))


def paint_india_nepal(draw, x, y, w, h):
    """New rail link: train front under two flags, mountains behind."""
    draw.rectangle([x, y, x + w, y + h], fill=(214, 226, 236))
    draw.polygon([(x, y + 26), (x + 14, y + 8), (x + 28, y + 26)],
                 fill=(150, 160, 175))
    draw.polygon([(x + 28, y + 26), (x + 42, y + 12), (x + 56, y + 26)],
                 fill=(130, 142, 158))
    # flags: India (saffron/white/green) + Nepal (crimson, blue edge)
    draw.rectangle([x + 8, y + 4, x + 20, y + 7], fill=(255, 153, 51))
    draw.rectangle([x + 8, y + 7, x + 20, y + 10], fill=WHITE)
    draw.rectangle([x + 8, y + 10, x + 20, y + 13], fill=(19, 136, 8))
    draw.polygon([(x + 36, y + 4), (x + 48, y + 8), (x + 36, y + 13)],
                 fill=(220, 20, 60))
    # train front
    draw.rounded_rectangle([x + 12, y + 26, x + 44, y + 48], radius=4,
                           fill=(200, 40, 40))
    draw.rectangle([x + 16, y + 30, x + 26, y + 37], fill=(200, 230, 240))
    draw.rectangle([x + 30, y + 30, x + 40, y + 37], fill=(200, 230, 240))
    draw.ellipse([x + 16, y + 42, x + 21, y + 47], fill=(250, 220, 60))
    draw.ellipse([x + 35, y + 42, x + 40, y + 47], fill=(250, 220, 60))


def paint_49ers(draw, x, y, w, h):
    """American football: field, goalpost, ball, scoreboard 35–10."""
    draw.rectangle([x, y, x + w, y + h], fill=(50, 130, 60))
    for ly in (14, 26, 38):
        draw.line([x, y + ly, x + w, y + ly], fill=WHITE, width=1)
    # goalpost
    draw.line([x + 46, y + 6, x + 46, y + 26], fill=(250, 220, 60), width=2)
    draw.line([x + 40, y + 6, x + 52, y + 6], fill=(250, 220, 60), width=2)
    # football with laces
    draw.ellipse([x + 8, y + 30, x + 26, y + 42], fill=(140, 90, 40))
    draw.line([x + 13, y + 36, x + 21, y + 36], fill=WHITE, width=1)
    # scoreboard
    draw.rectangle([x + 30, y + 30, x + w - 4, y + 44], fill=INK)
    draw.text((x + 33, y + 32), "35–10", font=font("sans_bold", 10),
              fill=WHITE)


def paint_markets(draw, x, y, w, h):
    """Wall Street rebound: green arrow climbing over candlesticks."""
    draw.rectangle([x, y, x + w, y + h], fill=(24, 32, 48))
    # candlesticks
    for bx, bh, col in ((8, 14, (120, 200, 120)), (20, 20, (120, 200, 120)),
                        (32, 10, (220, 90, 90)), (44, 24, (120, 200, 120))):
        draw.rectangle([x + bx, y + h - 8 - bh, x + bx + 8, y + h - 8],
                       fill=col)
    # rising arrow
    draw.line([x + 4, y + 34, x + 18, y + 26, x + 30, y + 28, x + 50, y + 10],
              fill=(120, 220, 120), width=3)
    draw.polygon([(x + 44, y + 8), (x + 52, y + 6), (x + 50, y + 14)],
                 fill=(120, 220, 120))
    draw.text((x + 4, y + 2), "+6.7%", font=font("sans_bold", 10),
              fill=(120, 220, 120))


def paint_ariane(draw, x, y, w, h):
    """Ariane 6 on the pad at Kourou: rocket, gantry, grey scrub sky."""
    draw.rectangle([x, y, x + w, y + h], fill=(206, 216, 224))
    draw.ellipse([x + 4, y + 6, x + 20, y + 14], fill=WHITE)
    draw.ellipse([x + 36, y + 4, x + 52, y + 12], fill=WHITE)
    # gantry tower
    draw.rectangle([x + 36, y + 12, x + 44, y + 48], fill=(110, 115, 125))
    for gy in range(16, 46, 8):
        draw.line([x + 36, y + gy, x + 44, y + gy], fill=(80, 85, 95),
                  width=1)
    # rocket: white body, orange tip, fins
    draw.rectangle([x + 20, y + 12, x + 30, y + 48], fill=WHITE,
                   outline=GREY)
    draw.polygon([(x + 20, y + 12), (x + 25, y + 4), (x + 30, y + 12)],
                 fill=(240, 120, 20))
    draw.polygon([(x + 20, y + 48), (x + 15, y + 52), (x + 20, y + 52)],
                 fill=(200, 60, 40))
    draw.polygon([(x + 30, y + 48), (x + 35, y + 52), (x + 30, y + 52)],
                 fill=(200, 60, 40))
    # HOLD tag
    draw.rectangle([x + 2, y + 2, x + 30, y + 12], fill=RED)
    draw.text((x + 4, y + 2), "HOLD", font=font("sans_bold", 8), fill=WHITE)


def paint_jokic(draw, x, y, w, h):
    """Basketball: backboard, hoop, ball dropping through the net."""
    draw.rectangle([x, y, x + w, y + h], fill=(220, 120, 40))
    draw.rectangle([x, y + 40, x + w, y + h], fill=(190, 100, 30))
    # backboard + hoop + net
    draw.rectangle([x + 14, y + 6, x + 42, y + 22], fill=WHITE,
                   outline=INK)
    draw.ellipse([x + 22, y + 22, x + 34, y + 28], outline=(200, 40, 40),
                 width=2)
    draw.line([x + 24, y + 28, x + 26, y + 36], fill=WHITE, width=1)
    draw.line([x + 32, y + 28, x + 30, y + 36], fill=WHITE, width=1)
    draw.line([x + 28, y + 28, x + 28, y + 36], fill=WHITE, width=1)
    # ball, mid-air above the hoop
    draw.ellipse([x + 38, y + 30, x + 52, y + 44], fill=(240, 120, 30),
                 outline=INK)
    draw.arc([x + 38, y + 30, x + 52, y + 44], 200, 340, fill=INK, width=1)
    draw.text((x + 4, y + 44), "202", font=font("sans_bold", 9), fill=WHITE)


CARD_PAINTERS = {4: paint_nato, 1: paint_cop31, 28: paint_cricket,
                 15: paint_india_nepal, 30: paint_49ers, 16: paint_markets,
                 36: paint_ariane, 29: paint_jokic}


# ---------------------------------------------------------------- sections
def draw_kicker(draw):
    draw.rectangle([0, 0, W, 18], fill=NAVY)
    centre(draw, 3, DATA["kicker"], font("sans_bold", 11), WHITE)


def draw_masthead(draw):
    # ears: factual furniture only — no invented weather or edition numbers
    draw.rectangle([16, 26, 116, 88], fill=WHITE, outline=RULE)
    centre(draw, 30, "MONDAY", font("sans_bold", 12), INK, cx=66)
    centre(draw, 46, "23 NOV", font("serif_bold", 15), INK, cx=66)
    centre(draw, 63, "2026", font("serif_bold", 15), INK, cx=66)
    draw.rectangle([908, 26, 1008, 88], fill=WHITE, outline=RULE)
    centre(draw, 28, "39", font("display_black", 22), NAVY, cx=958)
    centre(draw, 52, "STORIES", font("sans_bold", 11), INK, cx=958)
    centre(draw, 68, "7 REGIONS", font("sans_bold", 11), INK, cx=958)
    centre(draw, 20, DATA["edition"], font("display_black", 52), INK)
    centre(draw, 74, DATA["date_line"], font("serif_bold", 20), RED)
    draw.line([16, 96, W - 16, 96], fill=INK, width=2)
    draw.line([16, 99, W - 16, 99], fill=INK, width=1)


def draw_section_strip(draw):
    counts = region_counts()
    assert sum(counts.values()) == 39, counts
    parts = [f"{REGION_NAMES[c]} {counts.get(c, 0)}"
             for c in ("EU", "AS", "ME", "AM", "AF", "OC", "WD")]
    centre(draw, 103, "  ·  ".join(parts), font("sans_bold", 12), INK)
    draw.line([16, 115, W - 16, 115], fill=INK, width=1)


def _draw_deck(draw, x, y, text, max_w, drop_cap=False):
    """Hero deck, 12px serif, max 2 lines. Hero 1 gets a 2-line drop cap."""
    f = font("serif", 12)
    if not drop_cap:
        lines = wrap(draw, text, f, max_w)
        assert len(lines) <= 2, f"deck wraps to {len(lines)}: {text}"
        for i, line in enumerate(lines):
            draw.text((x, y + i * 14), line, font=f, fill=GREY)
        return len(lines)
    cap = text[0]
    rest = text[1:]
    cap_f = font("display_black", 30)
    draw.text((x, y - 3), cap, font=cap_f, fill=INK)
    cap_w = text_w(draw, cap, cap_f) + 6
    # The cap spans two lines, so BOTH lines are indented by its width.
    words, lines, cur = rest.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if text_w(draw, trial, f) <= max_w - cap_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    assert len(lines) <= 2, f"deck wraps to {len(lines)}: {text}"
    for i, line in enumerate(lines):
        draw.text((x + cap_w, y + i * 14), line, font=f, fill=GREY)
    return len(lines)


def draw_heroes(draw, img):
    pw, gap, y0, ph = 322, 12, 118, 210
    for i, hero in enumerate(HEROES):
        x = 16 + i * (pw + gap)
        draw.rectangle([x, y0, x + pw, y0 + ph], fill=PANEL, outline=RULE)
        bx, by = x + 10, y0 + 8
        draw.ellipse([bx, by, bx + 22, by + 22], fill=NAVY)
        nf = font("sans_bold", 13)
        num = str(hero["n"])
        draw.text((bx + 11 - text_w(draw, num, nf) / 2, by + 3), num,
                  font=nf, fill=WHITE)
        draw.text((bx + 30, by + 4), hero["kicker"],
                  font=font("sans_bold", 11), fill=RED)
        if hero.get("critical"):
            rx = x + pw - 74
            draw.rectangle([rx, y0 + 8, rx + 64, y0 + 24], fill=RED)
            centre(draw, y0 + 10, "CRITICAL", font("sans_bold", 9), WHITE,
                   cx=rx + 32)
        draw.text((x + 10, y0 + 34), hero["tag"], font=font("sans_bold", 10),
                  fill=RED)
        ax, ay, aw, ah = x + 8, y0 + 48, pw - 16, 80
        if hero.get("halftone"):
            layer = Image.new("RGB", (aw, ah), (198, 212, 222))
            ld = ImageDraw.Draw(layer)
            HERO_PAINTERS[hero["n"]](ld, 0, 0, aw, ah)
            img.paste(halftone(layer, pitch=4), (ax, ay))
            _label_bar(draw, ax, ay + ah - 16, aw, "BENGHAZI, LIBYA")
        else:
            HERO_PAINTERS[hero["n"]](draw, ax, ay, aw, ah)
        hl = wrap(draw, hero["headline"], font("display_bold", 18), pw - 20)
        assert len(hl) <= 2, f"hero headline wraps to {len(hl)}"
        hy = y0 + 132
        for j, line in enumerate(hl):
            draw.text((x + 10, hy + j * 21), line,
                      font=font("display_bold", 18), fill=INK)
        log_box(f"hero{hero['n']}", x, y0, x + pw, y0 + ph)
        _draw_deck(draw, x + 10, hy + len(hl) * 21 + 3, hero["deck"],
                   pw - 20, drop_cap=(i == 0))


def draw_pull_quote(draw):
    draw.line([16, 330, W - 16, 330], fill=INK, width=2)
    centre(draw, 334, DATA["pull_quote"], font("serif_italic", 14), INK)
    draw.line([16, 349, W - 16, 349], fill=INK, width=1)


def draw_map_zone(draw, img):
    draw.text((16, 352), "WHERE IT HAPPENED — THE TOP 10, PINNED",
              font=font("sans_bold", 12), fill=NAVY)
    # --- legend (left) ---
    lx = 16
    draw.text((lx, 368), "TOP 10", font=font("sans_bold", 11), fill=RED)
    top = sorted([s for s in STORIES if s["top10"]],
                 key=lambda s: s["top10"])
    assert len(top) == 10
    for i, s in enumerate(top):
        yy = 382 + i * 9.2
        draw.text((lx, yy), f"{s['top10']}.", font=font("sans_bold", 9),
                  fill=NAVY)
        draw.text((lx + 16, yy), s["map_label"], font=font("sans", 9),
                  fill=INK)
        log_box(f"legend{s['top10']}", lx, yy, lx + 260, yy + 9)
    # --- map (centre) ---
    mx, my, mw, mh = 286, 368, 444, 106
    layer = Image.new("RGB", (mw, mh), SEA)
    md = ImageDraw.Draw(layer)
    lon0, lon1, lat0, lat1 = -180.0, 180.0, 72.0, -50.0

    def proj(lon, lat):
        return ((lon - lon0) / (lon1 - lon0) * mw,
                (lat0 - lat) / (lat0 - lat1) * mh)

    for poly in CONTINENTS:
        md.polygon([proj(lon, lat) for lon, lat in poly], fill=LAND,
                   outline=LAND_EDGE)
    for lon in range(-150, 181, 30):
        gx = (lon - lon0) / (lon1 - lon0) * mw
        md.line([gx, 0, gx, mh], fill=(200, 214, 226), width=1)
    label_off = {2: (-118, 4), 8: (-68, -16), 10: (12, 4)}
    pin_nudge = {1: (-8, 8), 5: (8, -6), 9: (10, 6)}
    for s in top:
        px, py = proj(s["lon"], s["lat"])
        dx, dy = pin_nudge.get(s["top10"], (0, 0))
        px, py = px + dx, py + dy
        r = 9
        md.ellipse([px - r, py - r, px + r, py + r], fill=NAVY,
                   outline=WHITE, width=2)
        nf = font("sans_bold", 11)
        t = str(s["top10"])
        md.text((px - text_w(md, t, nf) / 2, py - 7), t, font=nf, fill=WHITE)
        if s["top10"] in label_off:
            dx, dy = label_off[s["top10"]]
            md.text((px + dx, py + dy), s["map_label"],
                    font=font("sans_bold", 10), fill=NAVY)
    img.paste(layer, (mx, my))
    draw.rectangle([mx, my, mx + mw, my + mh], outline=RULE)
    # --- numbers table (right, framed) ---
    rx = 740
    draw.text((rx, 368), "BY THE NUMBERS", font=font("sans_bold", 11),
              fill=RED)
    draw.rectangle([rx, 382, W - 16, 474], fill=WHITE, outline=RULE)
    for i, (num, label) in enumerate(DATA["numbers_table"]):
        yy = 384 + i * 13
        vf = font("serif_bold", 13)
        draw.text((rx + 64 - text_w(draw, num, vf), yy), num, font=vf,
                  fill=NAVY)
        draw.text((rx + 70, yy + 2), label, font=font("sans", 10), fill=INK)
        log_box(f"num{i}", rx, yy, W - 16, yy + 13)
    draw.text((rx + 6, 464), DATA["numbers_footnote"],
              font=font("serif_italic", 9), fill=GREY)


def draw_fold(draw):
    x = 16
    while x < W - 16:
        draw.line([x, 478, min(x + 10, W - 16), 478], fill=RULE, width=1)
        x += 16
    draw.rectangle([492, 471, 532, 483], fill=PAPER)
    centre(draw, 473, "FOLD", font("sans_bold", 8), GREY, cx=512)


def draw_index_row(draw):
    # Inside today — first 5 lines (D2 lives in the legend + ticker)
    draw.rectangle([16, 482, 340, 552], fill=WHITE, outline=RULE)
    draw.text((24, 488), "INSIDE TODAY", font=font("sans_bold", 11),
              fill=NAVY)
    for i, line in enumerate(DATA["inside_today"][:5]):
        draw.text((24, 502 + i * 10), line, font=font("sans", 10), fill=INK)
        log_box(f"index{i}", 24, 502 + i * 10, 332, 512 + i * 10)
    # Quote of the day — verified Huang quote
    draw.rectangle([352, 482, 676, 552], fill=WHITE, outline=RULE)
    draw.text((360, 488), "QUOTE OF THE DAY", font=font("sans_bold", 11),
              fill=NAVY)
    draw.text((360, 506), DATA["quote_of_day"],
              font=font("serif_italic", 14), fill=INK)
    draw.text((360, 528), DATA["quote_attribution"], font=font("sans", 10),
              fill=GREY)
    # Tomorrow — only items verified in Nadia's refresh notes
    draw.rectangle([688, 482, 1008, 552], fill=WHITE, outline=RULE)
    draw.text((696, 488), "TOMORROW — TUESDAY 24 NOV",
              font=font("sans_bold", 11), fill=NAVY)
    for i, line in enumerate(DATA["tomorrow"]):
        draw.text((696, 506 + i * 11), line, font=font("sans", 10),
                  fill=INK)


def draw_columns(draw):
    draw.text((16, 554), "THE DAY IN BRIEF", font=font("sans_bold", 13),
              fill=NAVY)
    draw.line([16, 570, W - 16, 570], fill=INK, width=1)
    rest = [s for s in STORIES if not s["top10"]]
    assert len(rest) == 29, len(rest)
    cols = [rest[0:10], rest[10:20], rest[20:29]]
    cw, gap = 322, 12
    shrunk = []
    for ci, col in enumerate(cols):
        x = 16 + ci * (cw + gap)
        for ri, s in enumerate(col):
            y = 574 + ri * 18
            draw.text((x, y), f"{s['n']}.", font=font("sans_bold", 12),
                      fill=RED)
            cx = x + 24
            draw.rounded_rectangle([cx, y + 1, cx + 26, y + 15], radius=3,
                                   fill=REGION_COLOURS[s["region"]])
            cf = font("sans_bold", 10)
            code = s["region"]
            draw.text((cx + 13 - text_w(draw, code, cf) / 2, y + 2), code,
                      font=cf, fill=WHITE)
            hx, hw = cx + 32, cw - 56
            f = fit_font(draw, s["headline"], hw, 13, 11)
            if f.size < 13:
                shrunk.append((s["n"], f.size))
            draw.text((hx, y), s["headline"], font=f, fill=INK)
            log_box(f"col{s['n']}", x, y, x + cw, y + 15)
        if ci:
            draw.line([x - gap // 2 - 1, 574, x - gap // 2 - 1, 749],
                      fill=(215, 205, 180), width=1)
    return shrunk


def _card_headline(draw, x, y, tag, headline, max_w):
    """Tag (red caps) + headline sharing two 12px lines; returns lines used."""
    tag_f = font("sans_bold", 10)
    hl_f = font("sans_bold", 12)
    tag_w = text_w(draw, tag + " ", tag_f)
    words, lines, cur, first = headline.split(), [], "", True
    for word in words:
        avail = max_w - tag_w if first else max_w
        trial = f"{cur} {word}".strip()
        if text_w(draw, trial, hl_f) <= avail or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur, first = word, False
    if cur:
        lines.append(cur)
    assert len(lines) <= 2, f"card headline wraps to {len(lines)}: {headline}"
    draw.text((x, y), tag, font=tag_f, fill=RED)
    draw.text((x + tag_w, y + 1), lines[0], font=hl_f, fill=INK)
    if len(lines) > 1:
        draw.text((x, y + 14), lines[1], font=hl_f, fill=INK)
    return len(lines)


def draw_cards(draw, y0, cards):
    cw, gap, ch = 239, 12, 62
    for i, card in enumerate(cards):
        x = 16 + i * (cw + gap)
        draw.rectangle([x, y0, x + cw, y0 + ch], fill=PANEL, outline=RULE)
        CARD_PAINTERS[card["n"]](draw, x + 6, y0 + 5, 56, 52)
        tx, tw = x + 68, 165
        used = _card_headline(draw, tx, y0 + 5, card["tag"],
                              card["headline"], tw)
        cap = wrap(draw, card["caption"], font("sans", 10), tw)[:2]
        cy = y0 + 5 + used * 14 + 2
        for j, line in enumerate(cap):
            draw.text((tx, cy + j * 12), line, font=font("sans", 10),
                      fill=GREY)
        log_box(f"card{card['n']}", x, y0, x + cw, y0 + ch)


def draw_timeline(draw):
    draw.text((16, 888), "THE DAY\nIN UTC", font=font("sans_bold", 11),
              fill=NAVY)
    x0, x1 = 170, 990
    step = (x1 - x0) / (len(DATA["timeline"]) - 1)
    draw.line([x0, 900, x1, 900], fill=RULE, width=2)
    for i, (when, text) in enumerate(DATA["timeline"]):
        cx = x0 + i * step
        draw.ellipse([cx - 5, 895, cx + 5, 905], fill=RED, outline=WHITE,
                     width=1)
        wf = font("sans_bold", 11)
        wlab = text_w(draw, when, wf)
        draw.text((min(max(cx - wlab / 2, 16), W - 16 - wlab), 888), when,
                  font=wf, fill=NAVY)
        tf = font("sans", 10)
        tlab = text_w(draw, text, tf)
        draw.text((min(max(cx - tlab / 2, 16), W - 16 - tlab), 904), text,
                  font=tf, fill=INK)


def draw_ticker(draw):
    draw.rectangle([0, 918, W, 944], fill=NAVY)
    f = fit_font(draw, DATA["ticker"], W - 32, 12, 10, kind="mono_bold")
    centre(draw, 924, DATA["ticker"], f, WHITE)


def draw_date_check(draw):
    draw.rectangle([16, 948, W - 16, 998], fill=RED_SOFT, outline=RED,
                   width=2)
    draw.text((24, 952), "DATE CHECK — WHAT WE LEFT OUT ON PURPOSE",
              font=font("sans_bold", 11), fill=RED)
    for xx, text in ((24, DATA["date_check_left"]),
                     (516, DATA["date_check_right"])):
        lines = wrap(draw, text, font("sans", 10), 472 if xx == 24 else 484)
        assert len(lines) <= 3, f"date-check wraps to {len(lines)}"
        for j, line in enumerate(lines):
            draw.text((xx, 964 + j * 11), line, font=font("sans", 10),
                      fill=INK)
        log_box(f"datecheck{xx}", xx, 964, xx + 480, 964 + len(lines) * 11)


def draw_footer(draw):
    centre(draw, 1001, DATA["footer_bold"], font("sans_bold", 12), INK)
    centre(draw, 1013, DATA["footer_small"], font("sans", 10), GREY)


# ---------------------------------------------------------------- main
def build(out_path):
    assert len(STORIES) == 39, f"{len(STORIES)} stories, want 39"
    assert [s["n"] for s in STORIES] == list(range(1, 40))
    ranks = sorted(s["top10"] for s in STORIES if s["top10"])
    assert ranks == list(range(1, 11)), ranks
    assert DATA["date_line"] == "MONDAY, 23 NOVEMBER 2026"
    tags = [h["tag"] for h in HEROES] + [c["tag"] for c in CARDS]
    assert len(tags) == len(set(tags)), f"duplicate section tag: {tags}"
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)
    draw_kicker(draw)
    draw_masthead(draw)
    draw_section_strip(draw)
    draw_heroes(draw, img)
    draw_pull_quote(draw)
    draw_map_zone(draw, img)
    draw_fold(draw)
    draw_index_row(draw)
    shrunk = draw_columns(draw)
    draw_cards(draw, 756, CARDS[:4])
    draw_cards(draw, 822, CARDS[4:])
    draw_timeline(draw)
    draw_ticker(draw)
    draw_date_check(draw)
    draw_footer(draw)
    img.save(out_path, optimize=True)
    size = Path(out_path).stat().st_size
    print(f"saved {out_path}  {img.size[0]}x{img.size[1]}  {size} bytes "
          f"({size / 1024:.0f} KB, limit 1024 KB)")
    print("regions:", region_counts(), "sum:",
          sum(region_counts().values()))
    print("headlines shrunk below 13px:", shrunk or "none")
    print("illustration elements: 3 heroes (1 halftone) + 8 mini-cards = 11, "
          "plus pinned map")
    if os.environ.get("DRAW_LOG"):
        (BASE / "boxes.json").write_text(json.dumps(BOXES, indent=1))
        print(f"logged {len(BOXES)} text boxes to boxes.json")
    return size


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "entry.png"
    build(out)
