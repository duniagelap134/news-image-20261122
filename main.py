#!/usr/bin/env python3
"""The Daily Globe — v2. Sunday 22 November 2026 in one picture.

Draws a dense, illustrated newspaper front page at runtime (stdlib only,
no network) and writes it to /output/entry.png. 1024x1024, deterministic.

Design, written fresh in-session: a hand-built single-stroke vector
lettering set (proportional advances, cap height 14 units, x-height 7),
a small 2-D drawing engine (rects, discs, thick strokes, polygon fills),
drawn news scenes per story, a numbers strip, a world map with pins, an
"also in the news" index and a date-check footer. No pixel font, no
pre-rendered image, no copied art.
"""

import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 242, 231)   # warm newsprint cream
PAPER2 = (240, 233, 214)  # slightly darker cream
INK = (22, 22, 22)
INK_SOFT = (58, 58, 58)
RED = (178, 34, 34)
RED_DK = (140, 22, 22)
NAVY = (20, 33, 61)
NAVY_LT = (38, 58, 94)
BLUE = (46, 111, 168)
SKY = (159, 199, 224)
SKY_DK = (110, 160, 200)
SEA = (52, 110, 158)
SEA_DK = (30, 74, 116)
SAND = (224, 200, 148)
GREEN = (26, 122, 58)
GREEN_LT = (210, 232, 214)
GOLD = (201, 162, 39)
ORANGE = (232, 110, 24)
FLAME = (245, 158, 32)
YELLOW = (250, 204, 64)
GREY = (120, 120, 116)
GREY_LT = (205, 205, 200)
GREY_DK = (74, 74, 72)
SMOKE = (150, 150, 148)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
TEAL = (18, 110, 105)
BROWN = (122, 82, 42)

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def _off(self, x, y):
        return (y * self.w + x) * 3

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            o = self._off(x, y)
            self.px[o], self.px[o + 1], self.px[o + 2] = c

    def fill_rect(self, x, y, w, h, c):
        x0 = max(0, int(x)); y0 = max(0, int(y))
        x1 = min(self.w, int(x + w)); y1 = min(self.h, int(y + h))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            o = self._off(x0, yy)
            self.px[o:o + len(row)] = row

    def hline(self, x, y, w, c):
        self.fill_rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        self.fill_rect(x, y, 1, h, c)

    def disc(self, cx, cy, r, c):
        r = int(r)
        if r <= 0:
            self.set(int(cx), int(cy), c)
            return
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def ring(self, cx, cy, r, t, c):
        cx, cy = int(cx), int(cy)
        for k in range(t):
            rr = r - k
            for dy in range(-rr, rr + 1):
                dx = int((rr * rr - dy * dy) ** 0.5)
                self.set(cx - dx, cy + dy, c)
                self.set(cx + dx, cy + dy, c)

    def poly(self, pts, c):
        # scanline fill of a simple polygon (float coords allowed)
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0 = max(0, int(min(ys))); y1 = min(self.h - 1, int(max(ys)) + 1)
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, y0p = pts[i]
                x1, y1p = pts[(i + 1) % n]
                if (y0p <= y < y1p) or (y1p <= y < y0p):
                    if y1p != y0p:
                        xs.append(x0 + (y - y0p) * (x1 - x0) / (y1p - y0p))
            if len(xs) >= 2:
                xs.sort()
                for a, b in zip(xs[0::2], xs[1::2]):
                    self.fill_rect(int(a), y, int(b) - int(a) + 1, 1, c)

    def line(self, x0, y0, x1, y1, w, c):
        # thick segment drawn as a filled quad (square caps)
        dx, dy = x1 - x0, y1 - y0
        ln = (dx * dx + dy * dy) ** 0.5
        if ln < 0.5:
            self.disc((x0 + x1) / 2, (y0 + y1) / 2, max(1, w / 2), c)
            return
        nx, ny = -dy / ln * w / 2, dx / ln * w / 2
        self.poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                   (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], c)

    def frame(self, x, y, w, h, c, t=1):
        self.fill_rect(x, y, w, t, c)
        self.fill_rect(x, y + h - t, w, t, c)
        self.fill_rect(x, y, t, h, c)
        self.fill_rect(x + w - t, y, t, h, c)

# ---------------------------------------------------------------- PNG out
def write_png(cv, path):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        raw += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
           + chunk(b"IEND", b""))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ---------------------------------------------------------------- vector font
# Glyphs on a 0..10 x 0..18 grid; baseline y=14, cap top 0, x-top 7.
# Format: "advance|stroke;stroke" with strokes as "x,y x,y ..." polylines.
FONT = {
"A": "11|0,14 5,0 10,14;2.5,7 7.5,7",
"B": "10|0,14 0,0 7,0 9,2 9,5 7,7 0,7;7,7 9,9 9,12 7,14 0,14",
"C": "10|9,3 7,0 3,0 0,3 0,11 3,14 7,14 9,11",
"D": "11|0,14 0,0 7,0 10,3 10,11 7,14 0,14",
"E": "10|9,0 0,0 0,14 9,14;0,7 7,7",
"F": "9|0,14 0,0 9,0;0,7 7,7",
"G": "10|9,3 7,0 3,0 0,3 0,11 3,14 7,14 9,11 9,7 6,7",
"H": "11|0,0 0,14;10,0 10,14;0,7 10,7",
"I": "10|5,0 5,14;2,0 8,0;2,14 8,14",
"J": "9|8,0 8,11 6,14 3,14 1,12",
"K": "11|0,0 0,14;10,0 1,7;3,6 10,14",
"L": "9|0,0 0,14 9,14",
"M": "12|0,14 0,0 5,8 10,0 10,14",
"N": "11|0,14 0,0 10,14 10,0",
"O": "11|5,0 1,2 0,7 1,12 5,14 9,12 10,7 9,2 5,0",
"P": "11|0,14 0,0 8,0 10,2 10,6 8,8 0,8",
"Q": "11|5,0 1,2 0,7 1,12 5,14 9,12 10,7 9,2 5,0;7,11 10,14",
"R": "11|0,14 0,0 8,0 10,2 10,6 8,8 0,8;3,8 10,14",
"S": "10|9,2 7,0 3,0 1,2 1,5 3,7 7,7 9,9 9,12 7,14 3,14 1,12",
"T": "11|0,0 10,0;5,0 5,14",
"U": "11|0,0 0,11 2,14 8,14 10,11 10,0",
"V": "11|0,0 5,14 10,0",
"W": "12|0,0 2.5,14 5,5 7.5,14 10,0",
"X": "11|0,0 10,14;10,0 0,14",
"Y": "11|0,0 5,7 10,0;5,7 5,14",
"Z": "11|0,0 10,0 0,14 10,14",
"a": "10|9,14 9,7 7,5 3,5 1,7 1,11 3,13 7,13 9,11",
"b": "9|0,0 0,14;0,9 2,7 6,7 8,9 8,11 6,13 2,13 0,11",
"c": "8|8,8 6,7 3,7 1,9 1,11 3,13 6,13 8,12",
"d": "9|9,0 9,14;9,9 7,7 3,7 1,9 1,11 3,13 7,13 9,11",
"e": "9|8,12 6,13 3,13 1,11 1,9 3,7 6,7 8,9 8,10 1,10",
"f": "7|7,0 4,0 3,2 3,14;1,5 6,5",
"g": "10|9,7 7,5 3,5 1,7 1,11 3,13 7,13 9,11 9,14 7,18 3,18",
"h": "9|0,0 0,14;0,9 2,7 6,7 8,9 8,14",
"i": "5|4,7 4,14;4,2 4,3",
"j": "8|7,7 7,15 5,18 2,18;7,2 7,3",
"k": "9|0,0 0,14;8,7 1,11;3,10 8,14",
"l": "5|4,0 4,14",
"m": "11|0,14 0,7 2,5 4,7 4,14;4,7 6,5 8,7 8,14",
"n": "9|0,14 0,7 2,5 6,5 8,7 8,14",
"o": "10|5,7 2,8 1,10 2,12 5,13 8,12 9,10 8,8 5,7",
"p": "9|0,7 0,18;0,10 2,7 6,7 8,9 8,11 6,13 2,13 0,11",
"q": "9|9,7 9,18;9,10 7,7 3,7 1,9 1,11 3,13 7,13 9,11",
"r": "7|0,14 0,7;0,9 2,7 5,7 7,8",
"s": "9|8,8 6,7 3,7 1,8 1,10 3,11 7,11 8,12 6,13 3,13",
"t": "7|5,0 5,14;2,5 7,5;5,14 7,13",
"u": "9|0,7 0,11 2,13 6,13 8,11 8,7;8,7 8,14",
"v": "9|0,7 4,14 8,7",
"w": "10|0,7 2,14 4,9 6,14 8,7",
"x": "9|0,7 8,14;8,7 0,14",
"y": "9|0,7 4,14 8,7;8,7 8,15 6,18 3,18",
"z": "9|0,7 8,7 0,14 8,14",
"0": "11|5,0 1,2 0,7 1,12 5,14 9,12 10,7 9,2 5,0",
"1": "9|5,0 5,14;2,3 5,0;2,14 8,14",
"2": "10|1,3 3,0 7,0 9,3 9,6 1,14 9,14",
"3": "10|1,2 3,0 7,0 9,2 9,6 7,8 9,10 9,12 7,14 3,14 1,12",
"4": "10|7,0 7,14;1,10 9,10;7,0 1,10",
"5": "10|9,0 0,0 0,6 6,6 9,8 9,12 7,14 3,14 1,12",
"6": "10|9,2 7,0 3,0 1,3 0,7 1,11 3,14 7,14 9,12 9,9 7,7 3,7 1,9",
"7": "10|0,0 10,0 5,14",
"8": "10|5,0 2,1 1,3 2,6 5,7 8,6 9,3 8,1 5,0;5,7 2,8 1,11 2,13 5,14 8,13 9,11 8,8 5,7",
"9": "10|9,7 9,3 7,0 3,0 1,3 1,6 3,8 7,8 9,6 9,11 7,14 3,14 1,12",
".": "5|4,13 4,14",
",": "5|4,13 4,15 2,18",
":": "5|4,5 4,6;4,12 4,13",
";": "5|4,5 4,6;4,12 4,14 2,18",
"'": "4|4,0 3,4",
"-": "9|1,8 9,8",
"–": "11|0,8 10,8",
"—": "11|0,8 10,8",
"/": "8|2,14 8,0",
"(": "7|7,0 4,3 4,11 7,14",
")": "7|3,0 6,3 6,11 3,14",
"%": "11|2,1 1,2 1,4 2,5 4,4 4,2 2,1;8,9 7,10 7,12 8,13 10,12 10,10 8,9;0,14 10,0",
"+": "10|5,3 5,11;1,7 9,7",
"=": "10|1,5 9,5;1,10 9,10",
"?": "10|2,3 4,0 7,0 9,2 9,5 7,7 5,8 5,11;5,13 5,14",
"!": "6|5,0 5,10;5,13 5,14",
"·": "5|4,7 5,7",
'"': "8|3,0 2,4;7,0 6,4",
"&": "10|8,2 6,0 3,0 1,3 3,6 7,9 9,12 7,14 3,14",
"$": "10|8,3 6,0 3,0 1,3 1,8 3,11 7,11 9,13 9,15 7,18 3,18;5,0 5,18",
"*": "8|4,1 4,13;1,4 7,10;7,4 1,10",
"_": "10|0,14 10,14",
" ": "5|",
}

def _parse_font():
    out = {}
    for ch, spec in FONT.items():
        adv, rest = spec.split("|", 1)
        strokes = []
        if rest:
            for st in rest.split(";"):
                pts = []
                for pair in st.split(" "):
                    a, b = pair.split(",")
                    pts.append((float(a), float(b)))
                strokes.append(pts)
        out[ch] = (float(adv), strokes)
    return out

GLYPHS = _parse_font()

def text_w(s, scale, track=0.0):
    tot = 0.0
    for ch in s:
        adv = GLYPHS.get(ch, GLYPHS[" "])[0]
        tot += adv * scale + track
    return tot - track if s else 0.0

def draw_text(cv, x, y, s, scale, color, width, track=0.0, align="left"):
    """Draw text; y is the top of the cap line."""
    if align == "center":
        x -= text_w(s, scale, track) / 2
    elif align == "right":
        x -= text_w(s, scale, track)
    cx = float(x)
    for ch in s:
        adv, strokes = GLYPHS.get(ch, GLYPHS[" "])
        for st in strokes:
            for (ax, ay), (bx, by) in zip(st, st[1:]):
                cv.line(cx + ax * scale, y + ay * scale,
                        cx + bx * scale, y + by * scale, width, color)
        cx += adv * scale + track
    return cx

def wrap(s, scale, maxw, track=0.0):
    lines, cur = [], ""
    for word in s.split(" "):
        trial = (cur + " " + word).strip()
        if text_w(trial, scale, track) <= maxw or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines

def para(cv, x, y, s, scale, maxw, color, width, leading, track=0.0):
    yy = y
    for ln in wrap(s, scale, maxw, track):
        draw_text(cv, x, yy, ln, scale, color, width, track)
        yy += leading
    return yy


# ---------------------------------------------------------------- scene kit
def burst(cv, cx, cy, r, c1, c2):
    """Starburst explosion: spiky polygon in c1 with a c2 core."""
    pts = []
    import math
    for i in range(16):
        ang = i * 3.14159 / 8
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    cv.poly(pts, c1)
    cv.disc(cx, cy, r * 0.42, c2)

def flame(cv, x, y, w, h):
    """A flame tongue: orange outer, yellow inner, red base."""
    cv.poly([(x, y + h), (x + w * 0.28, y + h * 0.35), (x + w * 0.42, y + h * 0.55),
             (x + w * 0.5, y), (x + w * 0.62, y + h * 0.5), (x + w * 0.78, y + h * 0.3),
             (x + w, y + h)], ORANGE)
    cv.poly([(x + w * 0.3, y + h), (x + w * 0.42, y + h * 0.45), (x + w * 0.5, y + h * 0.18),
             (x + w * 0.6, y + h * 0.5), (x + w * 0.72, y + h)], YELLOW)

def smoke(cv, x, y, r, n=4):
    for i in range(n):
        cv.disc(x + i * r * 0.7, y - i * r * 0.9, r * (1 - i * 0.12), SMOKE)

def windows(cv, x, y, cols, rows, cw, ch, gap, lit):
    for r in range(rows):
        for c in range(cols):
            col = lit if (r * cols + c) % 3 else (90, 90, 86)
            cv.fill_rect(x + c * (cw + gap), y + r * (ch + gap), cw, ch, col)

def scene_kyiv(cv, x, y, w, h):
    # Night strike on a Kyiv apartment block.
    cv.fill_rect(x, y, w, h, NAVY)
    cv.fill_rect(x, y + h * 0.62, w, h * 0.38, (12, 20, 44))
    for sx, sy in [(0.08, 0.12), (0.22, 0.06), (0.38, 0.16), (0.55, 0.08),
                   (0.7, 0.14), (0.86, 0.05), (0.93, 0.2)]:
        cv.disc(x + w * sx, y + h * sy, 1.5, WHITE)
    # distant blocks
    cv.fill_rect(x + w * 0.02, y + h * 0.42, w * 0.16, h * 0.58, (26, 40, 74))
    cv.fill_rect(x + w * 0.80, y + h * 0.38, w * 0.18, h * 0.62, (26, 40, 74))
    windows(cv, x + w * 0.05, y + h * 0.48, 2, 4, 5, 6, 4, YELLOW)
    windows(cv, x + w * 0.83, y + h * 0.44, 2, 4, 5, 6, 4, YELLOW)
    # main block, broken top, blast on its upper floors
    bx, bw = x + w * 0.30, w * 0.40
    cv.fill_rect(bx, y + h * 0.30, bw, h * 0.70, GREY_DK)
    cv.poly([(bx, y + h * 0.30), (bx + bw * 0.25, y + h * 0.22), (bx + bw * 0.5, y + h * 0.30),
             (bx + bw * 0.75, y + h * 0.24), (bx + bw, y + h * 0.30)], GREY_DK)
    windows(cv, bx + 8, y + h * 0.38, 5, 3, 7, 8, 5, YELLOW)
    burst(cv, bx + bw * 0.62, y + h * 0.30, 26, ORANGE, YELLOW)
    flame(cv, bx + bw * 0.42, y + h * 0.10, 34, 26)
    smoke(cv, bx + bw * 0.55, y + h * 0.16, 9, 3)
    # rubble + rescue vehicle
    cv.fill_rect(x, y + h * 0.92, w, h * 0.08, (16, 16, 16))
    cv.poly([(bx - 14, y + h * 0.92), (bx + 6, y + h * 0.82), (bx + 26, y + h * 0.92)], GREY)
    cv.fill_rect(x + w * 0.06, y + h * 0.80, w * 0.16, h * 0.12, WHITE)
    cv.fill_rect(x + w * 0.06, y + h * 0.80, w * 0.16, 2, RED)
    cv.fill_rect(x + w * 0.125, y + h * 0.82, 3, h * 0.08, RED)
    cv.fill_rect(x + w * 0.105, y + h * 0.845, w * 0.045, 3, RED)

def scene_cop31(cv, x, y, w, h):
    # COP31 in Antalya: conference hall on the coast, deal dead.
    cv.fill_rect(x, y, w, h, SKY)
    cv.disc(x + w * 0.86, y + h * 0.18, 12, YELLOW)
    cv.fill_rect(x, y + h * 0.62, w, h * 0.38, SEA)
    cv.fill_rect(x, y + h * 0.62, w, 3, WHITE)
    cv.fill_rect(x, y + h * 0.70, w, h * 0.06, SAND)
    # hall: white block, blue dome, columns
    hx, hw = x + w * 0.24, w * 0.52
    cv.fill_rect(hx, y + h * 0.42, hw, h * 0.30, WHITE)
    import math as _m
    _cx, _cy, _r = hx + hw / 2, y + h * 0.42, hw * 0.16
    _pts = [(_cx + _r * _m.cos(a), _cy - _r * _m.sin(a))
            for a in [i * _m.pi / 12 for i in range(13)]]
    cv.poly(_pts + [(_cx + _r, _cy), (_cx - _r, _cy)], NAVY_LT)
    cv.fill_rect(hx + hw * 0.34, y + h * 0.42, hw * 0.32, 4, NAVY_LT)
    for i in range(5):
        cv.fill_rect(hx + 10 + i * (hw - 20) / 4, y + h * 0.48, 4, h * 0.24, NAVY_LT)
    cv.fill_rect(hx - 8, y + h * 0.70, hw + 16, 4, NAVY_LT)
    # flags row
    for i, fc in enumerate([RED, BLUE, GREEN, GOLD, TEAL]):
        fx = x + w * 0.06 + i * 14
        cv.vline(fx, y + h * 0.30, h * 0.32, INK)
        cv.fill_rect(fx, y + h * 0.30, 11, 7, fc)
    # globe
    cv.disc(x + w * 0.88, y + h * 0.50, 13, TEAL)
    cv.fill_rect(x + w * 0.88 - 13, y + h * 0.50 - 2, 26, 2, WHITE)
    cv.fill_rect(x + w * 0.88 - 2, y + h * 0.50 - 13, 2, 26, WHITE)
    # NO DEAL banner
    cv.fill_rect(x, y + h * 0.78, w, h * 0.22, RED)
    draw_text(cv, x + w / 2, y + h * 0.81, "NO DEAL", 1.05, WHITE, 2.6, track=1.0, align="center")

def scene_hormuz(cv, x, y, w, h):
    # Tankers ablaze near the Strait of Hormuz.
    cv.fill_rect(x, y, w, h, SKY)
    cv.disc(x + w * 0.12, y + h * 0.16, 11, YELLOW)
    cv.fill_rect(x, y + h * 0.55, w, h * 0.45, SEA)
    cv.fill_rect(x, y + h * 0.55, w, 2, WHITE)
    for i in range(5):
        cv.fill_rect(x + w * (0.05 + i * 0.18), y + h * (0.68 + (i % 2) * 0.12), 26, 2, (190, 220, 235))
    # tanker 1, burning
    t1x, t1w = x + w * 0.08, w * 0.44
    cv.fill_rect(t1x, y + h * 0.44, t1w, h * 0.16, (122, 30, 30))
    cv.fill_rect(t1x + 6, y + h * 0.36, t1w * 0.30, h * 0.08, WHITE)
    cv.fill_rect(t1x + t1w * 0.62, y + h * 0.32, 10, h * 0.12, INK)
    flame(cv, t1x + t1w * 0.30, y + h * 0.16, 44, 40)
    flame(cv, t1x + t1w * 0.62, y + h * 0.26, 26, 26)
    smoke(cv, t1x + t1w * 0.42, y + h * 0.14, 10, 3)
    # tanker 2, smaller, smoking
    t2x, t2w = x + w * 0.58, w * 0.36
    cv.fill_rect(t2x, y + h * 0.48, t2w, h * 0.14, (60, 60, 62))
    cv.fill_rect(t2x + 5, y + h * 0.40, t2w * 0.28, h * 0.08, WHITE)
    flame(cv, t2x + t2w * 0.45, y + h * 0.28, 24, 22)
    smoke(cv, t2x + t2w * 0.55, y + h * 0.24, 8, 2)
    # red banner
    cv.fill_rect(x, y, w * 0.52, 14, RED)
    draw_text(cv, x + 6, y + 2, "2 TANKERS HIT", 0.68, WHITE, 1.5, track=0.5)

def scene_benghazi(cv, x, y, w, h):
    # Dusk blast on a Russian ship at Benghazi port.
    cv.fill_rect(x, y, w, h, (232, 164, 96))
    cv.fill_rect(x, y + h * 0.45, w, h * 0.55, (94, 94, 90))
    cv.fill_rect(x, y + h * 0.45, w, 2, (60, 60, 58))
    cv.disc(x + w * 0.82, y + h * 0.20, 10, YELLOW)
    # ship
    sx, sw = x + w * 0.10, w * 0.72
    cv.fill_rect(sx, y + h * 0.58, sw, h * 0.16, (40, 40, 44))
    cv.fill_rect(sx + sw * 0.08, y + h * 0.48, sw * 0.24, h * 0.10, WHITE)
    cv.fill_rect(sx + sw * 0.60, y + h * 0.44, 7, h * 0.14, INK)
    cv.line(sx + sw * 0.30, y + h * 0.48, sx + sw * 0.30, y + h * 0.28, 2, INK)
    burst(cv, sx + sw * 0.55, y + h * 0.44, 18, ORANGE, YELLOW)
    flame(cv, sx + sw * 0.40, y + h * 0.24, 26, 20)
    smoke(cv, sx + sw * 0.58, y + h * 0.28, 7, 2)
    # crane
    cv.line(x + w * 0.86, y + h * 0.70, x + w * 0.86, y + h * 0.16, 3, (60, 60, 58))
    cv.line(x + w * 0.86, y + h * 0.16, x + w * 0.98, y + h * 0.30, 2, (60, 60, 58))

def scene_westbank(cv, x, y, w, h):
    # Night arson: house and car burning.
    cv.fill_rect(x, y, w, h, NAVY)
    cv.fill_rect(x, y + h * 0.72, w, h * 0.28, (14, 22, 46))
    for sx, sy in [(0.1, 0.1), (0.3, 0.06), (0.6, 0.12), (0.9, 0.08)]:
        cv.disc(x + w * sx, y + h * sy, 1.5, WHITE)
    # house
    hx, hw = x + w * 0.08, w * 0.34
    cv.fill_rect(hx, y + h * 0.40, hw, h * 0.34, (52, 44, 38))
    cv.poly([(hx - 4, y + h * 0.40), (hx + hw / 2, y + h * 0.22), (hx + hw + 4, y + h * 0.40)], (38, 32, 28))
    flame(cv, hx + hw * 0.25, y + h * 0.08, hw * 0.5, h * 0.34)
    # car
    cx, cw = x + w * 0.56, w * 0.36
    cv.fill_rect(cx, y + h * 0.56, cw, h * 0.16, (70, 70, 74))
    cv.poly([(cx + cw * 0.12, y + h * 0.56), (cx + cw * 0.28, y + h * 0.42),
             (cx + cw * 0.68, y + h * 0.42), (cx + cw * 0.84, y + h * 0.56)], (70, 70, 74))
    cv.disc(cx + cw * 0.22, y + h * 0.74, 5, BLACK)
    cv.disc(cx + cw * 0.78, y + h * 0.74, 5, BLACK)
    flame(cv, cx + cw * 0.30, y + h * 0.26, cw * 0.4, h * 0.30)
    smoke(cv, cx + cw * 0.5, y + h * 0.22, 6, 2)

def scene_china_chart(cv, x, y, w, h):
    # Margin ratio cut 100% -> 80%: two bars and a down arrow.
    cv.fill_rect(x, y, w, h, WHITE)
    cv.frame(x, y, w, h, GREY_LT, 1)
    cv.line(x + 14, y + h - 12, x + 14, y + 10, 1.5, INK)
    cv.line(x + 14, y + h - 12, x + w - 8, y + h - 12, 1.5, INK)
    b1x, b1w = x + 34, (w - 60) / 2 - 8
    b2x = b1x + b1w + 16
    cv.fill_rect(b1x, y + 22, b1w, h - 34, GREY)
    cv.fill_rect(b2x, y + 22 + (h - 34) * 0.2, b1w, (h - 34) * 0.8, RED)
    draw_text(cv, b1x + b1w / 2, y + 6, "100%", 0.62, INK_SOFT, 1.3, align="center")
    draw_text(cv, b2x + b1w / 2, y + 6, "80%", 0.62, RED, 1.3, align="center")

def scene_nvidia(cv, x, y, w, h):
    # AI chip under scrutiny: a chip on a dark board, red ring.
    cv.fill_rect(x, y, w, h, (16, 40, 32))
    cx, cy, cw = x + w * 0.30, y + h * 0.30, w * 0.40
    ch = h * 0.52
    cv.fill_rect(cx - 6, cy - 6, cw + 12, ch + 12, (8, 20, 16))
    for i in range(5):
        cv.fill_rect(cx - 12, cy + i * (ch / 4) - 1, 6, 3, GOLD)
        cv.fill_rect(cx + cw + 6, cy + i * (ch / 4) - 1, 6, 3, GOLD)
        cv.fill_rect(cx + i * (cw / 4) - 1, cy - 12, 3, 6, GOLD)
        cv.fill_rect(cx + i * (cw / 4) - 1, cy + ch + 6, 3, 6, GOLD)
    cv.fill_rect(cx, cy, cw, ch, (24, 24, 26))
    draw_text(cv, cx + cw / 2, cy + ch * 0.22, "AI", 1.5, (118, 185, 0), 2.6, align="center")
    cv.ring(x + w * 0.78, y + h * 0.62, 13, 3, RED)
    cv.line(x + w * 0.78 + 9, y + h * 0.62 + 9, x + w * 0.78 + 17, y + h * 0.62 + 17, 3, RED)

def scene_nigeria(cv, x, y, w, h):
    # Capsized boat on a river.
    cv.fill_rect(x, y, w, h, SKY)
    cv.fill_rect(x, y + h * 0.45, w, h * 0.55, SEA)
    for i in range(4):
        cv.line(x + w * (0.06 + i * 0.22), y + h * (0.58 + (i % 2) * 0.14),
                x + w * (0.06 + i * 0.22) + 22, y + h * (0.58 + (i % 2) * 0.14), 2, WHITE)
    # hull upside down, tilted
    cv.poly([(x + w * 0.22, y + h * 0.42), (x + w * 0.78, y + h * 0.34),
             (x + w * 0.72, y + h * 0.52), (x + w * 0.28, y + h * 0.58)], (122, 82, 42))
    cv.fill_rect(x + w * 0.44, y + h * 0.30, 4, h * 0.12, (122, 82, 42))
    cv.ring(x + w * 0.16, y + h * 0.66, 8, 3, ORANGE)
    cv.disc(x + w * 0.68, y + h * 0.70, 4, (40, 40, 40))


def scene_factory(cv, x, y, w, h):
    # Candy factory fire, Indonesia: sawtooth factory, smoking stack.
    cv.fill_rect(x, y, w, h, SKY)
    cv.fill_rect(x, y + h * 0.62, w, h * 0.38, (150, 150, 146))
    cv.fill_rect(x + w * 0.10, y + h * 0.42, w * 0.55, h * 0.30, GREY_DK)
    for i in range(3):
        sx = x + w * (0.10 + i * 0.19)
        cv.poly([(sx, y + h * 0.42), (sx + w * 0.095, y + h * 0.24),
                 (sx + w * 0.19, y + h * 0.42)], GREY_DK)
    cv.fill_rect(x + w * 0.72, y + h * 0.18, w * 0.08, h * 0.54, (90, 60, 50))
    smoke(cv, x + w * 0.76, y + h * 0.16, 6, 3)
    flame(cv, x + w * 0.30, y + h * 0.30, w * 0.22, h * 0.26)
    for i in range(3):
        cv.fill_rect(x + w * (0.14 + i * 0.17), y + h * 0.52, 8, 8, YELLOW)

def scene_ice(cv, x, y, w, h):
    # Jet bridge at Seattle-Tacoma: plane nose and bridge.
    cv.fill_rect(x, y, w, h, SKY)
    cv.fill_rect(x, y + h * 0.68, w, h * 0.32, GREY_LT)
    # fuselage
    cv.fill_rect(x + w * 0.06, y + h * 0.30, w * 0.62, h * 0.30, WHITE)
    cv.poly([(x + w * 0.68, y + h * 0.30), (x + w * 0.92, y + h * 0.40),
             (x + w * 0.92, y + h * 0.52), (x + w * 0.68, y + h * 0.60)], WHITE)
    for i in range(4):
        cv.fill_rect(x + w * (0.12 + i * 0.12), y + h * 0.38, 8, 7, NAVY_LT)
    cv.fill_rect(x + w * 0.06, y + h * 0.60, w * 0.62, 3, BLUE)
    # jet bridge
    cv.fill_rect(x + w * 0.70, y + h * 0.42, w * 0.26, h * 0.16, GREY_DK)
    cv.fill_rect(x + w * 0.78, y + h * 0.58, 5, h * 0.16, GREY_DK)
    cv.fill_rect(x + w * 0.90, y + h * 0.58, 5, h * 0.16, GREY_DK)

def scene_tennis(cv, x, y, w, h):
    # Alcaraz wins the ATP Finals: court, net, ball, trophy.
    cv.fill_rect(x, y, w, h, (46, 120, 66))
    cv.fill_rect(x + w * 0.08, y + h * 0.18, w * 0.84, h * 0.64, (74, 160, 92))
    cv.frame(x + w * 0.08, y + h * 0.18, w * 0.84, h * 0.64, WHITE, 2)
    cv.line(x + w * 0.08, y + h * 0.50, x + w * 0.92, y + h * 0.50, 2, WHITE)
    cv.line(x + w * 0.50, y + h * 0.18, x + w * 0.50, y + h * 0.82, 3, (30, 30, 30))
    cv.disc(x + w * 0.30, y + h * 0.34, 7, YELLOW)
    cv.poly([(x + w * 0.78, y + h * 0.14), (x + w * 0.86, y + h * 0.14),
             (x + w * 0.84, y + h * 0.30), (x + w * 0.80, y + h * 0.30)], GOLD)
    cv.fill_rect(x + w * 0.80, y + h * 0.30, 4, 6, GOLD)

def scene_golf(cv, x, y, w, h):
    # Thitikul's third straight LPGA title: green, flag, ball.
    cv.fill_rect(x, y, w, h, (74, 150, 80))
    cv.fill_rect(x, y + h * 0.30, w, h * 0.70, (46, 120, 66))
    cv.disc(x + w * 0.30, y + h * 0.55, 16, (120, 190, 110))
    cv.line(x + w * 0.68, y + h * 0.22, x + w * 0.68, y + h * 0.62, 2, WHITE)
    cv.poly([(x + w * 0.68, y + h * 0.22), (x + w * 0.88, y + h * 0.30),
             (x + w * 0.68, y + h * 0.38)], RED)
    cv.disc(x + w * 0.68, y + h * 0.62, 5, BLACK)
    cv.disc(x + w * 0.52, y + h * 0.72, 4, WHITE)
    cv.disc(x + w * 0.18, y + h * 0.78, 12, SAND)

def scene_bulgari(cv, x, y, w, h):
    # Paolo Bulgari, 89: a diamond on dark velvet.
    cv.fill_rect(x, y, w, h, NAVY)
    cx, cy = x + w * 0.50, y + h * 0.46
    cv.poly([(cx - 26, cy - 12), (cx + 26, cy - 12), (cx + 14, cy + 16),
             (cx - 14, cy + 16)], (150, 200, 230))
    cv.line(cx - 26, cy - 12, cx + 26, cy - 12, 2, WHITE)
    cv.line(cx - 13, cy - 12, cx - 7, cy + 16, 1.5, WHITE)
    cv.line(cx + 13, cy - 12, cx + 7, cy + 16, 1.5, WHITE)
    cv.line(cx, cy - 12, cx, cy + 16, 1.5, WHITE)
    cv.disc(cx - 30, cy - 18, 2, WHITE)
    cv.disc(cx + 32, cy - 8, 2, WHITE)
    cv.disc(cx + 26, cy + 20, 1.5, WHITE)

# ---------------------------------------------------------------- world map
MAP_LAND = [
    # North America, Greenland, South America, Europe, Africa, Asia, Oceania
    [(4, 12), (10, 6), (20, 4), (28, 8), (26, 14), (20, 16), (14, 20), (8, 18), (4, 16)],
    [(30, 2), (34, 2), (34, 6), (30, 6)],
    [(24, 26), (30, 24), (34, 30), (32, 40), (28, 46), (25, 36)],
    [(46, 8), (52, 4), (58, 6), (56, 12), (50, 14), (46, 12)],
    [(46, 18), (56, 16), (62, 22), (60, 32), (54, 40), (49, 32), (46, 24)],
    [(60, 4), (84, 2), (94, 8), (92, 16), (84, 20), (76, 16), (68, 18), (62, 12)],
    [(84, 38), (94, 36), (96, 42), (88, 46), (84, 42)],
]

def draw_map(cv, x, y, w, h, pins):
    cv.fill_rect(x, y, w, h, (214, 228, 236))
    sx, sy = w / 100.0, h / 50.0
    for poly in MAP_LAND:
        cv.poly([(x + px * sx, y + py * sy) for px, py in poly], SAND)
    for num, (mx, my) in pins:
        px, py = x + mx * sx, y + my * sy
        cv.disc(px, py, 8, RED)
        cv.disc(px, py, 8, RED)
        draw_text(cv, px, py - 5, str(num), 0.62, WHITE, 1.4, align="center")

# ---------------------------------------------------------------- cards
def tag_pill(cv, x, y, s, color=GREEN):
    wdt = text_w(s, 0.62, 0.4) + 10
    cv.fill_rect(x, y, wdt, 13, WHITE)
    cv.frame(x, y, wdt, 13, color, 1)
    draw_text(cv, x + 5, y + 1.5, s, 0.62, color, 1.2, track=0.4)
    return wdt

def big_card(cv, x, y, w, h, num, kicker, head, body, tag, scene):
    scene(cv, x, y, w, 118)
    cv.fill_rect(x, y + 118, w, 2, INK)
    tx, ty = x + 8, y + 126
    tag_pill(cv, x + w - 8 - (text_w(tag, 0.62, 0.4) + 10), ty, tag)
    draw_text(cv, tx, ty, str(num) + "  " + kicker, 0.82, RED, 1.8, track=0.6)
    hy = ty + 16
    hy = para(cv, tx, hy, head, 1.30, w - 16, INK, 2.4, 27)
    para(cv, tx, hy + 4, body, 0.80, w - 16, INK_SOFT, 1.4, 17)

def med_card(cv, x, y, w, h, num, kicker, head, body, tag, scene):
    scene(cv, x, y, w, 72)
    cv.fill_rect(x, y + 72, w, 2, INK)
    tx, ty = x + 7, y + 79
    tag_pill(cv, x + w - 7 - (text_w(tag, 0.60, 0.4) + 10), ty, tag)
    draw_text(cv, tx, ty + 15, str(num) + "  " + kicker, 0.78, RED, 1.7, track=0.5)
    hy = ty + 30
    hy = para(cv, tx, hy, head, 1.05, w - 14, INK, 2.0, 21)
    para(cv, tx, hy + 4, body, 0.72, w - 14, INK_SOFT, 1.2, 15)

def small_card(cv, x, y, w, h, num, kicker, head, body, scene):
    scene(cv, x, y, w, 52)
    cv.fill_rect(x, y + 52, w, 2, INK)
    tx, ty = x + 7, y + 59
    draw_text(cv, tx, ty, str(num) + "  " + kicker, 0.76, RED, 1.6, track=0.5)
    hy = ty + 14
    hy = para(cv, tx, hy, head, 1.02, w - 14, INK, 2.0, 21)
    para(cv, tx, hy + 3, body, 0.70, w - 14, INK_SOFT, 1.2, 14)

# ---------------------------------------------------------------- page
def build():
    cv = Canvas(W, H, PAPER)
    cv.frame(0, 0, W, H, INK, 3)
    cv.frame(5, 5, W - 10, H - 10, INK, 1)
    X, CW = 22, 980

    # top line
    draw_text(cv, X, 12, "ONE DAY OF WORLD NEWS, ONE PICTURE", 0.72, RED, 1.4, track=0.8)
    draw_text(cv, X + CW, 12, "25 STORIES · 5 REGIONS · 9 FIELDS · EVERY ONE FROM THIS SUNDAY",
              0.72, INK_SOFT, 1.4, track=0.6, align="right")
    cv.hline(X, 30, CW, INK)
    # masthead
    draw_text(cv, X + CW / 2, 38, "Sunday 22 November 2026", 3.05, INK, 5.2,
              track=1.2, align="center")
    cv.fill_rect(X, 96, CW, 2, INK)
    cv.fill_rect(X, 100, CW, 1, INK)

    # numbers strip
    ny = 108
    cv.fill_rect(X, ny, 118, 46, RED)
    draw_text(cv, X + 8, ny + 6, "THE DAY", 0.72, WHITE, 1.5, track=0.8)
    draw_text(cv, X + 8, ny + 18, "IN NUMBERS", 0.72, WHITE, 1.5, track=0.8)
    draw_text(cv, X + 8, ny + 30, "SUN 22 NOV", 0.62, (255, 220, 220), 1.2, track=0.6)
    nums = [
        ("3", "killed in Kyiv"),
        ("12", "vehicles torched"),
        ("14+", "Iran's tankers"),
        ("80%", "margin ratio"),
        ("24", "dead in Nigeria"),
        ("34", "workers missing"),
    ]
    cell_w = (CW - 118) / 6
    for i, (big, lab) in enumerate(nums):
        cx0 = X + 118 + i * cell_w
        if i:
            cv.vline(cx0, ny + 4, 38, GREY_LT)
        draw_text(cv, cx0 + 10, ny + 2, big, 1.45, RED_DK, 2.6)
        draw_text(cv, cx0 + 10, ny + 27, lab, 0.72, INK_SOFT, 1.3)
    cv.hline(X, ny + 50, CW, INK)

    # big cards: Kyiv, COP31, Hormuz
    by, bh = 166, 260
    bigs = [
        (X, 1, "UKRAINE · KYIV", "Russia hits a Kyiv flat, 3 killed",
         "A Russian strike on a residential building kills three and buries "
         "others; rescuers search the rubble for the missing.",
         "OFFICIAL · KYIV", scene_kyiv),
        (X + 330, 2, "TURKIYE · CLIMATE", "COP31 collapses, no deal",
         "Climate talks in Antalya end without a deal after overtime talks, "
         "deadlocked over fossil fuels.",
         "CONFIRMED · AP", scene_cop31),
        (X + 660, 3, "HORMUZ · ENERGY", "Tankers ablaze off Hormuz",
         "Tankers struck and set ablaze near the Strait; Bahrain says an "
         "Iranian attack hit a site and hurt two.",
         "CONFIRMED · UKMTO", scene_hormuz),
    ]
    for bx, n, kick, head, body, tag, sc in bigs:
        big_card(cv, bx, by, 320, bh, n, kick, head, body, tag, sc)
        cv.vline(bx + 320 + 5, by, bh, GREY_LT) if bx < X + 660 else None
    cv.hline(X, by + bh + 8, CW, INK)

    # medium cards: Benghazi, West Bank, China, Nvidia, Nigeria
    my, mh = 434, 200
    meds = [
        (X, 4, "LIBYA · BENGHAZI", "Blast hits Russian ship",
         "Blast damages a Russian ship in port; probe points to a drone.",
         "OFFICIAL", scene_benghazi),
        (X + 196, 5, "WEST BANK", "Settlers torch 12 vehicles",
         "Dozens raid villages near Ramallah; opposition calls it terrorism.",
         "REPORTED", scene_westbank),
        (X + 392, 6, "CHINA · MARKETS", "China eases margin rules",
         "Exchanges cut the margin ratio to 80% from 100%, from 30 Nov.",
         "OFFICIAL", scene_china_chart),
        (X + 588, 7, "US · TECH", "US presses Nvidia on chips",
         "Treasury's Bessent seeks answers on AI chips sold to China.",
         "REPORTED", scene_nvidia),
        (X + 784, 8, "NIGERIA", "Boat capsize kills at least 24",
         "A boat carrying people to a funeral capsizes; at least 24 dead.",
         "REPORTED", scene_nigeria),
    ]
    for bx, n, kick, head, body, tag, sc in meds:
        med_card(cv, bx, my, 188, mh, n, kick, head, body, tag, sc)
    cv.hline(X, my + mh + 8, CW, INK)

    # small cards: Indonesia, ICE, Alcaraz, Thitikul, Bulgari
    sy, sh = 642, 144
    smalls = [
        (X, 9, "INDONESIA", "Remains found after factory fire",
         "More remains of 34 missing workers found.", scene_factory),
        (X + 196, 10, "US · SEATTLE", "ICE drags two off a jet bridge",
         "Two dragged off jet bridge; LA flight delayed.", scene_ice),
        (X + 392, 11, "SPORT · TENNIS", "Alcaraz wins his first ATP Finals",
         "Alcaraz beats Zverev for the title.", scene_tennis),
        (X + 588, 12, "SPORT · GOLF", "Thitikul wins third LPGA title",
         "Thitikul wins a third straight LPGA title.", scene_golf),
        (X + 784, 13, "OBITUARY", "Paolo Bulgari, jeweller, dies at 89",
         "Paolo Bulgari, the Italian jeweller, dies at 89.",
         scene_bulgari),
    ]
    for bx, n, kick, head, body, sc in smalls:
        small_card(cv, bx, sy, 188, sh, n, kick, head, body, sc)
    cv.hline(X, sy + sh + 8, CW, INK)

    # map + also list
    ay = 802
    draw_text(cv, X, ay, "WHERE IT HAPPENED", 0.85, RED, 1.7, track=0.8)
    draw_map(cv, X, ay + 16, 330, 120,
             [(1, (52, 9)), (2, (56, 12)), (3, (66, 18)), (4, (52, 20)),
              (5, (56, 16)), (6, (84, 10)), (7, (10, 10)), (8, (50, 26)),
              (9, (86, 28)), (10, (80, 20)), (11, (50, 12)), (12, (80, 22)),
              (13, (50, 13))])
    draw_text(cv, X, ay + 140, "Europe 4 · Middle East 2 · Asia 4 · Africa 2 · N. America 1",
              0.66, INK_SOFT, 1.2, track=0.3)

    ax = X + 352
    draw_text(cv, ax, ay, "ALSO ON SUNDAY 22 NOVEMBER", 0.85, RED, 1.7, track=0.8)
    also = [
        (14, "Bahrain site hit, two hurt"),
        (15, "Iran readies 14+ tanker convoy"),
        (16, "Bessent presses Nvidia on chips"),
        (17, "CXMT and YMTC gain amid curbs"),
        (18, "Opposition calls attacks terrorism"),
        (19, "COP31 deadlocked over fossil fuels"),
        (20, "Rescuers search Kyiv rubble"),
        (21, "Libya probe points to drone attack"),
        (22, "Poland: Russia 'tried to kill' rapper"),
        (23, "Indian Youth Congress protests at Meta"),
        (24, "Liverpool beat ten-man Man Utd"),
        (25, "Thai court cuts defamation sentence"),
    ]
    col_w = (CW - 352) / 2
    for i, (n, txt) in enumerate(also):
        col = i // 6
        row = i % 6
        ix = ax + col * col_w
        iy = ay + 18 + row * 22
        draw_text(cv, ix, iy, str(n), 0.78, RED, 1.6)
        draw_text(cv, ix + 22, iy, txt, 0.70, INK, 1.3)
    cv.hline(X, ay + 156, CW, INK)

    # date check + footer
    dy = 964
    cv.fill_rect(X, dy, CW, 22, PAPER2)
    cv.frame(X, dy, CW, 22, GREY_LT, 1)
    cv.fill_rect(X + 8, dy + 4, text_w("DATE CHECK", 0.72, 0.6) + 8, 13, RED)
    draw_text(cv, X + 8, dy + 4, "DATE CHECK", 0.72, WHITE, 1.4, track=0.6)
    draw_text(cv, X + 8 + text_w("DATE CHECK", 0.72, 0.6) + 16, dy + 4,
              "Left out, first reported before Sunday: ICJ Rohingya ruling, Mexico cartel "
              "capture, Kryvyi Rih strike, Mlambo-Ngcuka death.",
              0.66, INK_SOFT, 1.2)
    draw_text(cv, X, 992,
              "Every story happened or was first reported on Sun 22 Nov 2026 · Sources: AP, "
              "Standard Topic, KIRO, Russell Record · Original drawings",
              0.62, INK_SOFT, 1.2, track=0.3)
    return cv

def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    cv = build()
    n = write_png(cv, os.path.join(out, "entry.png"))
    print("wrote", os.path.join(out, "entry.png"), n, "bytes")

if __name__ == "__main__":
    main()
