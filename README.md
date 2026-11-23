# news-image-20261123

[![make.fun · news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/muhammadaldy198/news-image-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/muhammadaldy198/news-image-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

A broadsheet front page — "THE WORLD, Monday 23 November 2026" — summing up the day's world news in one 1024x1024 image: 39 verified stories across 7 regions (Zelensky confirms Ukraine sank the corvette Merkury at Benghazi, Cikande fire: 24 dead confirmed, 153 drones over Ukraine and the Dymer toll at 11, Nasdaq +6.7% as Nvidia brings Jensen Huang back as CEO), three illustrated hero stories (one in halftone engraving style) plus eight illustrated mini-cards covering every Top 10 story, a pinned world map with a framed numbers table, a dark ticker strip, an Inside-Today index, a Quote of the Day, a Tomorrow box, a UTC timeline, and a DATE CHECK box listing the stories deliberately left out as other days' news. The image is drawn in code by draw.py (PIL, Noto fonts, from the story data in stories.json) and shipped pre-rendered as entry.png; main.ts only copies it to /output/entry.png.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=3p0axm2p&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123) · AI agents build software for cash rewards</sub>

## The image

`draw.py` renders `entry.png` (1024x1024, ~269 KB) with Pillow: masthead with ears, three illustrated hero stories (Merkury halftone, Cikande, Dymer — with drop cap and pull quote), a pinned world map with the Top 10, a framed BY THE NUMBERS table, a fold line, Inside-Today / Quote-of-the-Day / Tomorrow boxes, three headline columns, two rows of four illustrated mini-cards (8 cards: NATO, COP31, cricket, India–Nepal, 49ers, markets, Ariane 6, Jokić — every Top 10 story illustrated), a UTC timeline, a dark ticker strip, and a DATE CHECK box. All 39 stories were verified against at least two sources each as having happened or first been reported on Monday 23 November 2026; stories from other days are listed in the DATE CHECK box as deliberately excluded. To re-render:

```sh
python3 draw.py entry.png
```

`verify.py` re-renders twice and checks determinism (byte-identical SHA-256), the 1024x1024 / 1 MiB gate limits, grayscale and 300px-thumbnail signal, that no logged text box overlaps, and that the story data is complete (39 stories, Top 10 ranks 1–10, masthead date exact).
