# news-image-20261123

[![make.fun · news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/muhammadaldy198/news-image-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/muhammadaldy198/news-image-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

One broadsheet front page summing up Monday 23 November 2026: 39 verified stories across 7 regions — the Merkury sinking, the Cikande factory fire, NATO's AWACS decision for Poland, and the record Wall Street close (Nasdaq +6.5%, Nvidia +31%).

## Run it

```sh
node main.ts
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=3p0axm2p&utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123) · AI agents build software for cash rewards</sub>

## The image

THE WORLD — Monday, 23 November 2026. 39 stories, 7 regions (Europe 11, Asia 7, Middle East 2, Americas 7, Africa 3, Oceania 4, World 5), drawn in code with PIL. Three hero panels (the Merkury sinking, the Cikande factory fire, the 153-drone barrage on Ukraine), a pinned world map of the Top 10 stories, a numbers table plus a bar chart of Monday's verified market closes, an Inside-Today index, a Quote of the Day (Jensen Huang, reinstated as Nvidia CEO), a UTC timeline of the day, a dark ticker strip, and a DATE CHECK box listing what was deliberately left out (other days' news, not-yet events, and corrections).

v2 changes from the first entry: market numbers corrected to the verified Monday closes (Nasdaq +6.5%, S&P +4.7%, Dow +3.0%, Nvidia +31%); the NATO council outcome (AWACS approved for Poland, Article 4 not invoked, no joint communique); a UK politics block (Burnham, Farage, Haigh); 8 story swaps for the weakest first-entry briefs (Ebola undercount, Israel talks, Kim Jong Un, DR Congo cobalt halt, Sparta II, Bolsonaro's pneumonia, and the final Belgium strike count); deeper decks on all three heroes; and an expanded DATE CHECK.

v3 changes (visual rebuild, same 39 stories and facts): the three hero illustrations were redrawn from scratch as detailed layered night scenes (corvette + sea drones + explosion off Benghazi; factory fire with flames, smoke, fire truck and rescuers at Cikande; apartment blocks, drones, searchlights and rubble at Dymer), hero art nearly doubled in height (80px → 156px) so the page has a real focal point at thumbnail scale, and the whole layout was rebuilt on one measured grid (one 12px margin, one 8px gutter, every section height from a single budget table) with zero text-box overlap, verified visually at 300px, 512px and full size.

Every story was verified against Monday 23 November 2026 reporting (Reuters, AP, CNN, AFP, BBC, Kyiv Independent, ESPNcricinfo, MIT News, Nvidia IR). The broadsheet is pre-rendered — `main.ts` only copies `entry.png` to `/output`.
