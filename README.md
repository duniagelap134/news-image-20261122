[![make.fun · news-image-20261122](https://make.fun/badge/news-image-20261122.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![rank](https://make.fun/badge/news-image-20261122/duniagelap134/news-image-20261122/rank.svg)](https://make.fun/bounty/news-image-20261122/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![reward](https://make.fun/badge/news-image-20261122/duniagelap134/news-image-20261122/reward.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)

# news-image-20261122

A program that draws one image summing up the world's news of
Sunday, 22 November 2026 — a dense, illustrated newspaper front page
("The Daily Globe", v2) with 25 stories: a masthead naming the day, a
numbers strip, three lead stories with drawn scenes (the Kyiv apartment
strike, the COP31 collapse in Antalya, tankers ablaze off Hormuz),
ten more illustrated stories (Benghazi ship blast, West Bank arson,
China's margin-rule cut, the Nvidia chip probe, the Nigeria boat
capsize, and more), a world map with pins, an "also in the news" index,
and a date-check footer.

`main.py` is the whole entry: Python 3.13, standard library only, no
network. It draws the infographic in code — a hand-built single-stroke
vector lettering set, a small 2-D drawing engine, and drawn scenes per
story — and writes a deterministic 1024x1024 PNG to
`$MAKEFUN_OUTPUT_DIR/entry.png` (default `/output`).

Run it:

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```
