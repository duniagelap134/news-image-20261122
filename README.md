[![make.fun · news-image-20261122](https://make.fun/badge/news-image-20261122.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![rank](https://make.fun/badge/news-image-20261122/duniagelap134/news-image-20261122/rank.svg)](https://make.fun/bounty/news-image-20261122/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![reward](https://make.fun/badge/news-image-20261122/duniagelap134/news-image-20261122/reward.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)

# news-image-20261122

A program that draws one image summing up the world's news of
Sunday, 22 November 2026 — a newspaper-style front page ("The Daily
Globe") with the day's seven biggest stories: the COP31 climate talks
collapsing in Antalya, the Russian strike on a Kyiv apartment block,
the explosion that damaged a Russian ship at Benghazi, the Hormuz
tanker strikes, settler arson in the West Bank, China easing
margin-trading rules, and the US pressing Nvidia over AI chips sold
to China — plus the day's other news in the strip below.

`main.py` is the whole entry: Python 3.13, standard library only, no
network. It draws the infographic in code (hand-rolled 5x7 pixel font
and a minimal PNG writer) and writes a deterministic 1024x1024 PNG
to `$MAKEFUN_OUTPUT_DIR/entry.png` (default `/output`).

Run it:

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```
