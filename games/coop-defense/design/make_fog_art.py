"""Overcharge fog atlas: assets/fog.png, 4 player rows x 4 columns of 300x220 (drawn at scale 2).

Column 0 is a half-strength fade-in frame; columns 1-3 loop as swirling mist with sparks.
Run: python games/coop-defense/design/make_fog_art.py
"""
import math
import os
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

W, H = 300, 220
COLORS = [(64, 185, 167), (101, 169, 224), (220, 153, 88), (223, 113, 145)]  # main.py COLORS
COPPER = (241, 173, 91)
OUT = os.path.join(os.path.dirname(__file__), '..', 'assets', 'fog.png')


def edge_mask():
    """Alpha 0 in the middle, rising to the edges and corners; weak under the HUD bar on top."""
    m = Image.new('L', (W, H))
    px = m.load()
    for y in range(H):
        for x in range(W):
            dx, dy = abs(x - W / 2) / (W / 2), abs(y - H / 2) / (H / 2)
            d = max(0.0, math.hypot(dx * 0.95, dy) - 0.42) / 0.55
            v = min(1.0, d) ** 1.3
            if y < 18 or y > H - 16:  # keep the HUD bar and the bottom prompt readable
                v *= 0.45
            px[x, y] = int(255 * v)
    return m


def noise(seed, scale):
    rnd = random.Random(seed)
    small = Image.new('L', (W // scale + 2, H // scale + 2))
    small.putdata([rnd.randint(0, 255) for _ in range(small.width * small.height)])
    return small.resize((W + scale * 2, H + scale * 2), Image.BICUBIC).filter(ImageFilter.GaussianBlur(scale / 2))


def frame(color, phase, strength, seed):
    mask = edge_mask()
    big, fine = noise(seed, 22), noise(seed + 7, 9)
    shift = int(phase * 22)  # the mist drifts between loop frames
    wisps = ImageChops.multiply(big.crop((shift, 0, shift + W, H)), fine.crop((0, shift // 2, W, H + shift // 2)))
    wisps = wisps.point(lambda v: min(255, int(v * 2.2)))
    body = wisps.point(lambda v: 110 + v * 145 // 255)  # a steady glow plus drifting wisps on top
    alpha = ImageChops.multiply(mask, body).point(lambda v: int(min(215, v * 1.1) * strength))
    tint = tuple(int(c * 0.75 + k * 0.25) for c, k in zip(color, COPPER))
    img = Image.new('RGBA', (W, H), tint + (0,))
    img.putalpha(alpha)
    rnd = random.Random(seed * 31 + int(phase * 10))
    draw = ImageDraw.Draw(img)
    for _ in range(int(14 * strength)):  # sparks only in the misty rim
        x, y = rnd.randrange(W), rnd.randrange(H)
        if mask.getpixel((x, y)) < 120:
            continue
        light = tuple(min(255, c + 90) for c in color)
        draw.point((x, y), fill=light + (230,))
        draw.point((x + 1, y), fill=light + (150,))
        draw.point((x, y + 1), fill=light + (150,))
    return img


def main():
    atlas = Image.new('RGBA', (W * 4, H * 4))
    for row, color in enumerate(COLORS):
        atlas.paste(frame(color, 0.0, 0.5, row * 100), (0, row * H))
        for col in range(1, 4):
            atlas.paste(frame(color, col / 3, 1.0, row * 100 + col), (col * W, row * H))
    atlas.save(OUT, optimize=True)
    print(OUT, atlas.size, os.path.getsize(OUT), 'bytes')


if __name__ == '__main__':
    main()
