"""Overcharge energy frame: assets/energy.png, 4 player rows x 4 columns of 300x220 (drawn at scale 2).

Column 0 is the charge-up frame (glow only); columns 1-3 loop: a pulsing energy rim with lightning
arcs running along the screen edges. Run: python games/coop-defense/design/make_energy_art.py
"""
import os
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

W, H = 300, 220
COLORS = [(64, 185, 167), (101, 169, 224), (220, 153, 88), (223, 113, 145)]  # main.py COLORS
OUT = os.path.join(os.path.dirname(__file__), '..', 'assets', 'energy.png')
HUD, PROMPT = 16, 14  # top bar and bottom prompt rows (in 300x220 pixels): arcs stay off them


def rim(strength):
    """Glow that hugs the screen border and fades within ~14 px."""
    m = Image.new('L', (W, H))
    px = m.load()
    for y in range(H):
        for x in range(W):
            d = min(x, y - HUD if y >= HUD else 99, W - 1 - x, H - 1 - y)
            v = max(0.0, 1 - d / 14) ** 2 if d >= 0 else 0
            px[x, y] = int(150 * v * strength)
    return m


def bolt(draw, rnd, a, b, color, inward):
    """Jagged arc from a to b, bulging inward by up to `inward` px."""
    (x0, y0), (x1, y1) = a, b
    steps = rnd.randint(7, 11)
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        j = 0 if i in (0, steps) else rnd.uniform(1, inward)
        nx, ny = inward_normal(x, y)
        pts.append((x + nx * j + rnd.uniform(-1.5, 1.5), y + ny * j + rnd.uniform(-1.5, 1.5)))
    draw.line(pts, fill=color + (170,), width=3)
    draw.line(pts, fill=(255, 255, 255, 255), width=1)


def inward_normal(x, y):
    d = {(1, 0): x, (0, 1): y - HUD, (-1, 0): W - 1 - x, (0, -1): H - 1 - y}
    return min(d, key=d.get)


def edge_points(rnd):
    """Two points on one screen edge, 30-70 px apart."""
    side = rnd.randrange(4)
    span = rnd.randint(30, 70)
    if side in (0, 1):  # top (under the HUD) / bottom (above the prompt)
        x = rnd.randint(4, W - span - 4)
        y = HUD + 1 if side == 0 else H - PROMPT - 2
        return (x, y), (x + span, y)
    y = rnd.randint(HUD + 4, H - PROMPT - span - 4) if H - PROMPT - span - 4 > HUD + 4 else HUD + 4
    x = 1 if side == 2 else W - 2
    return (x, y), (x, y + span)


def frame(color, col, seed):
    rnd = random.Random(seed)
    strength = 0.55 if col == 0 else (1.0, 0.75, 0.9)[col - 1]  # the rim pulses between loop frames
    glow = Image.new('RGBA', (W, H), color + (0,))
    glow.putalpha(rim(strength))
    if col == 0:
        return glow
    arcs = Image.new('RGBA', (W, H))
    draw = ImageDraw.Draw(arcs)
    for _ in range(5):
        a, b = edge_points(rnd)
        bolt(draw, rnd, a, b, color, 9)
    halo = arcs.filter(ImageFilter.GaussianBlur(3))  # soft light around each arc
    halo.putalpha(halo.getchannel('A').point(lambda v: v * 3 // 4))
    for _ in range(10):  # loose sparks along the rim
        x, y = rnd.choice([(rnd.randrange(W), HUD + rnd.randrange(6)), (rnd.randrange(W), H - PROMPT - rnd.randrange(6)),
                           (rnd.randrange(6), rnd.randrange(HUD, H - PROMPT)), (W - 1 - rnd.randrange(6), rnd.randrange(HUD, H - PROMPT))])
        draw.point((x, y), fill=(255, 255, 255, 230))
    out = Image.alpha_composite(glow, halo)
    return Image.alpha_composite(out, arcs)


def main():
    atlas = Image.new('RGBA', (W * 4, H * 4))
    for row, color in enumerate(COLORS):
        for col in range(4):
            atlas.paste(frame(color, col, row * 100 + col), (col * W, row * H))
    atlas.save(OUT, optimize=True)
    print(OUT, atlas.size, os.path.getsize(OUT), 'bytes')


if __name__ == '__main__':
    main()
