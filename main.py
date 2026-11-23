#!/usr/bin/env python3
"""World news in one image — Sunday 22 November 2026.

A make.fun program/v1 entry (competition news-image-20261122). It draws a
newspaper-style front page of the day's world news and writes it to
$MAKEFUN_OUTPUT_DIR/entry.png (default /output). Python 3.13, standard
library only; no network. The output is deterministic: same code, same
bytes, every run.

The day's stories, as reported on 22 November 2026: the COP31 climate
talks in Antalya collapse without a deal; a Russian strike hits a Kyiv
apartment block and kills three; an explosion damages a Russian ship
docked at Benghazi port; tanker strikes near the Strait of Hormuz deepen
the US-Iran standoff; settlers torch vehicles and homes in West Bank
villages; China eases margin-trading rules; the US presses Nvidia over
AI chips sold to China. Plus the day's other news in the strip below.
"""

import os
import struct
import zlib

# ---------------------------------------------------------------------------
# 5x7 dot font. Each glyph is 7 strings of 5 cells ('#' = ink).
# Written for this entry; letters, digits and the punctuation the page uses.
# ---------------------------------------------------------------------------
GLYPHS = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", "..##.", "..##.", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "..#..", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "(": ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ")": ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", "#.##.", "#..##"),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "#": (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "*": (".....", ".#.#.", "..#..", "#####", "..#..", ".#.#.", "....."),
    "&": (".#...", "#.#..", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "\u2022": (".....", ".....", ".###.", ".###.", ".###.", ".....", "....."),
}

W, H = 1024, 1024
PAPER = (247, 242, 230)
INK = (24, 32, 54)
RED = (178, 34, 24)
TEAL = (13, 110, 104)
BLUE = (28, 74, 180)
AMBER = (176, 84, 8)
MAROON = (140, 30, 60)
GREY = (96, 102, 116)
CARD = (255, 255, 255)
EDGE = (198, 190, 170)

canvas = bytearray(W * H * 3)


def set_px(x, y, colour):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        canvas[i], canvas[i + 1], canvas[i + 2] = colour


def fill_rect(x, y, w, h, colour):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            set_px(xx, yy, colour)


def h_rule(x, y, w, colour, t=1):
    fill_rect(x, y, w, t, colour)


def v_rule(x, y, h, colour, t=1):
    fill_rect(x, y, t, h, colour)


def ring(cx, cy, r, colour, solid=False):
    for yy in range(cy - r, cy + r + 1):
        for xx in range(cx - r, cx + r + 1):
            d2 = (xx - cx) ** 2 + (yy - cy) ** 2
            if solid:
                if d2 <= r * r:
                    set_px(xx, yy, colour)
            elif r * r - 2 * r <= d2 <= r * r:
                set_px(xx, yy, colour)


def seg(x0, y0, x1, y1, colour, t=2):
    dx, dy = x1 - x0, y1 - y0
    steps = max(abs(dx), abs(dy), 1)
    for i in range(steps + 1):
        x = x0 + dx * i // steps
        y = y0 + dy * i // steps
        fill_rect(x - t // 2, y - t // 2, t, t, colour)


def text_w(s, scale):
    return len(s) * 6 * scale - scale


def put_text(s, x, y, scale, colour):
    cx = x
    for ch in s.upper():
        g = GLYPHS.get(ch, GLYPHS[" "])
        for r in range(7):
            row = g[r]
            for c in range(5):
                if row[c] == "#":
                    fill_rect(cx + c * scale, y + r * scale, scale, scale, colour)
        cx += 6 * scale
    return cx - scale


def put_text_centred(s, cx, y, scale, colour):
    put_text(s, cx - text_w(s, scale) // 2, y, scale, colour)


def wrap(s, scale, max_w):
    words = s.upper().split(" ")
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if text_w(trial, scale) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------------------
# Minimal PNG writer: IHDR + IDAT (zlib) + IEND, CRC32 on each chunk.
# ---------------------------------------------------------------------------
def _png_chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    return out + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def save_png(path):
    raw = b"".join(b"\x00" + bytes(canvas[y * W * 3:(y + 1) * W * 3]) for y in range(H))
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------------------
# Pictograms, drawn with primitives into a square centred at (cx, cy).
# ---------------------------------------------------------------------------
def pic_globe(cx, cy, s, c):
    r = s // 2
    ring(cx, cy, r, c)
    h_rule(cx - r, cy, 2 * r, c, 3)
    h_rule(cx - r * 3 // 4, cy - r // 2, r * 3 // 2, c, 3)
    h_rule(cx - r * 3 // 4, cy + r // 2, r * 3 // 2, c, 3)
    v_rule(cx, cy - r, 2 * r, c, 3)


def pic_building(cx, cy, s, c):
    w, h = s * 3 // 5, s
    x0, y0 = cx - w // 2, cy - h // 2
    fill_rect(x0, y0, w, h, c)
    for gx in range(3):
        for gy in range(4):
            fill_rect(x0 + 6 + gx * (w // 3), y0 + 8 + gy * (h // 4),
                      w // 6, h // 8, CARD)
    # crack down the middle
    seg(cx - 4, y0, cx + 3, y0 + h // 3, CARD, 2)
    seg(cx + 3, y0 + h // 3, cx - 3, y0 + h * 2 // 3, CARD, 2)
    seg(cx - 3, y0 + h * 2 // 3, cx + 4, y0 + h, CARD, 2)


def pic_ship(cx, cy, s, c):
    # hull
    seg(cx - s // 2, cy + s // 4, cx + s // 2, cy + s // 4, c, 4)
    seg(cx - s // 2, cy + s // 4, cx - s // 3, cy + s // 2, c, 4)
    seg(cx + s // 2, cy + s // 4, cx + s // 3, cy + s // 2, c, 4)
    seg(cx - s // 3, cy + s // 2, cx + s // 3, cy + s // 2, c, 4)
    # mast + funnel
    v_rule(cx - s // 6, cy - s // 2, s // 2 + s // 4, c, 4)
    fill_rect(cx + s // 8, cy - s // 3, s // 6, s // 3, c)
    # smoke puffs
    ring(cx + s // 6, cy - s // 2 - 4, 5, c, solid=True)
    ring(cx + s // 4, cy - s // 2 - 12, 4, c, solid=True)


def pic_flame(cx, cy, s, c):
    ring(cx, cy + s // 5, s // 4, c, solid=True)
    ring(cx, cy, s // 5, c, solid=True)
    ring(cx, cy - s // 4, s // 6, c, solid=True)
    seg(cx - s // 3, cy + s // 5, cx, cy - s // 2, c, 3)
    seg(cx + s // 3, cy + s // 5, cx, cy - s // 2, c, 3)


def pic_house_fire(cx, cy, s, c):
    # house body + roof
    w, h = s * 3 // 5, s // 2
    x0, y0 = cx - w // 2, cy
    fill_rect(x0, y0, w, h, c)
    seg(cx - w // 2 - 4, y0, cx, y0 - s // 4, c, 3)
    seg(cx + w // 2 + 4, y0, cx, y0 - s // 4, c, 3)
    # flame above the roof
    ring(cx, y0 - s // 3, s // 8, c, solid=True)
    ring(cx, y0 - s // 2, s // 10, c, solid=True)


def pic_chart_down(cx, cy, s, c):
    bw = s // 6
    for i, h in enumerate((s * 3 // 4, s // 2, s // 4)):
        x = cx - s // 2 + i * (bw + s // 12)
        fill_rect(x, cy + s // 2 - h, bw, h, c)
    seg(cx - s // 2, cy - s // 4, cx + s // 2, cy + s // 4, c, 3)
    seg(cx + s // 2, cy + s // 4, cx + s // 2 - s // 6, cy + s // 4, c, 3)
    seg(cx + s // 2, cy + s // 4, cx + s // 2, cy + s // 4 - s // 6, c, 3)


def pic_chip(cx, cy, s, c):
    d = s * 3 // 5
    x0, y0 = cx - d // 2, cy - d // 2
    fill_rect(x0, y0, d, d, c)
    fill_rect(x0 + d // 4, y0 + d // 4, d // 2, d // 2, CARD)
    for i in range(3):
        off = d // 4 + i * d // 4
        h_rule(x0 - s // 8, y0 + off, s // 8, c, 3)
        h_rule(x0 + d, y0 + off, s // 8, c, 3)
        v_rule(x0 + off, y0 - s // 8, s // 8, c, 3)
        v_rule(x0 + off, y0 + d, s // 8, c, 3)


# ---------------------------------------------------------------------------
# Layout: newspaper front page, 1024 x 1024.
# ---------------------------------------------------------------------------
def draw_card(x, y, w, h, accent):
    fill_rect(x, y, w, h, CARD)
    h_rule(x, y, w, INK, 2)
    h_rule(x, y + h - 2, w, INK, 2)
    v_rule(x, y, h, INK, 2)
    v_rule(x + w - 2, y, h, INK, 2)
    fill_rect(x + 2, y + 2, w - 4, 6, accent)


def draw_page():
    fill_rect(0, 0, W, H, PAPER)
    fill_rect(12, 12, W - 24, H - 24, INK)
    fill_rect(16, 16, W - 32, H - 32, PAPER)

    # masthead
    put_text_centred("THE WORLD IN ONE DAY", W // 2, 38, 3, GREY)
    put_text_centred("THE DAILY GLOBE", W // 2, 64, 6, INK)
    put_text_centred("SUNDAY, 22 NOVEMBER 2026", W // 2, 116, 5, RED)
    h_rule(48, 158, W - 96, RED, 4)
    put_text_centred("SEVEN STORIES THAT DEFINED THE DAY", W // 2, 168, 3, INK)

    # lead feature: COP31 collapse
    lx, ly, lw, lh = 48, 204, 928, 176
    draw_card(lx, ly, lw, lh, TEAL)
    fill_rect(64, ly + 24, 128, 128, TEAL)
    pic_globe(64 + 64, ly + 24 + 64, 92, CARD)
    put_text("ANTALYA  \u2022  CLIMATE", 212, ly + 16, 3, TEAL)
    put_text("COP31 COLLAPSES", 212, ly + 44, 6, INK)
    lead_body = ("CLIMATE TALKS IN ANTALYA END WITHOUT A DEAL AFTER "
                 "OVERTIME TALKS, DEADLOCKED OVER FOSSIL FUELS.")
    by = ly + 100
    for ln in wrap(lead_body, 3, 740)[:3]:
        put_text(ln, 212, by, 3, INK)
        by += 26

    # 2 x 2 grid of story cards
    grid = [
        {
            "tag": "KYIV  \u2022  UKRAINE", "colour": RED, "icon": pic_building,
            "headline": "KYIV: 3 DEAD",
            "body": ("RUSSIAN STRIKE HITS A KYIV FLAT, 3 KILLED; "
                     "RESCUERS SEARCH THE RUBBLE."),
        },
        {
            "tag": "BENGHAZI  \u2022  LIBYA", "colour": BLUE, "icon": pic_ship,
            "headline": "BENGHAZI BLAST",
            "body": ("BLAST DAMAGES A RUSSIAN SHIP AT BENGHAZI; "
                     "DRONE ATTACK SUSPECTED."),
        },
        {
            "tag": "HORMUZ  \u2022  GULF", "colour": AMBER, "icon": pic_flame,
            "headline": "HORMUZ ABLAZE",
            "body": ("TANKERS ABLAZE NEAR THE STRAIT OF HORMUZ; "
                     "BAHRAIN SITE HIT, 2 HURT."),
        },
        {
            "tag": "WEST BANK  \u2022  PALESTINE", "colour": MAROON,
            "icon": pic_house_fire,
            "headline": "WEST BANK ARSON",
            "body": ("SETTLERS TORCH 12 VEHICLES AND HOMES IN WEST "
                     "BANK VILLAGES."),
        },
    ]
    gx0, gy0 = 48, 392
    cw, chh, gap = 458, 176, 12
    for i, st in enumerate(grid):
        x = gx0 + (i % 2) * (cw + gap)
        y = gy0 + (i // 2) * (chh + gap)
        draw_card(x, y, cw, chh, st["colour"])
        put_text(st["tag"], x + 16, y + 16, 3, st["colour"])
        put_text(st["headline"], x + 16, y + 42, 4, INK)
        fill_rect(x + 16, y + 80, 64, 64, st["colour"])
        st["icon"](x + 48, y + 112, 44, CARD)
        by = y + 80
        for ln in wrap(st["body"], 3, 346)[:4]:
            put_text(ln, x + 96, by, 3, INK)
            by += 22

    # bottom row: two compact items
    bx, byy, bw, bh = 48, 768, 928, 96
    draw_card(bx, byy, bw, bh, INK)
    v_rule(bx + bw // 2, byy + 10, bh - 20, EDGE, 2)
    bottom = [
        {
            "tag": "BEIJING  \u2022  MARKETS", "colour": BLUE,
            "headline": "MARGIN RULES EASED",
            "body": ("CHINA CUTS THE MINIMUM MARGIN RATIO TO 80% "
                     "FROM 100%, FROM 30 NOV."),
        },
        {
            "tag": "WASHINGTON  \u2022  TECH", "colour": AMBER,
            "headline": "NVIDIA CHIP PROBE",
            "body": "US PRESSES NVIDIA OVER AI CHIPS SOLD TO CHINA.",
        },
    ]
    for i, st in enumerate(bottom):
        x = bx + 16 + i * (bw // 2)
        put_text(st["tag"], x, byy + 12, 2, st["colour"])
        put_text(st["headline"], x, byy + 30, 3, INK)
        ly2 = byy + 58
        for ln in wrap(st["body"], 2, 430)[:2]:
            put_text(ln, x, ly2, 2, INK)
            ly2 += 17

    # also in the news
    ay = 872
    put_text("ALSO IN THE NEWS", 48, ay, 3, RED)
    also = [
        "ALCARAZ WINS FIRST ATP FINALS TITLE",
        "NIGERIA BOAT CAPSIZE KILLS AT LEAST 24",
        "INDONESIA FACTORY FIRE: MORE REMAINS FOUND",
        "ICE DRAGS PASSENGERS OFF SEATTLE JET BRIDGE",
    ]
    ly3 = ay + 26
    for a in also:
        put_text("\u2022  " + a, 48, ly3, 3, INK)
        ly3 += 22

    put_text_centred("REPORTED 22 NOV 2026  \u2022  SOURCES: MULTIPLE NEWS OUTLETS",
                     W // 2, 988, 2, GREY)


def main():
    draw_page()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    n = save_png(os.path.join(out_dir, "entry.png"))
    print(f"wrote entry.png ({n} bytes)")


if __name__ == "__main__":
    main()
