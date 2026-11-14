"""Minimal - the starting point for a new game: title, play, game over, score, sound, save.

Catch the stars, avoid the red blocks. D-pad moves, A starts.
"""
import random

import r36t as g

SHIP = g.sprite([
    "...ww...",
    "..wbbw..",
    "..wbbw..",
    ".wwwwww.",
    "wwwwwwww",
    "w.wyyw.w",
    "..y..y..",
], {"w": (230, 235, 245), "b": (80, 160, 255), "y": (250, 200, 60)})
STAR = g.sprite([
    "..y..",
    ".yyy.",
    "yyyyy",
    ".yyy.",
    "..y..",
], {"y": (250, 215, 70)})

best = g.load().get("best", 0)
state = "title"  # "title" -> "play" -> "over" -> "title"
x = y = score = timer = 0
stars, blocks = [], []


def start():
    global state, x, y, score, timer, stars, blocks
    state, x, y, score, timer = "play", g.W / 2, g.H - 60, 0, 0
    stars, blocks = [], []


def update(dt):
    global state, x, y, score, timer, best
    if state != "play":
        if g.pressed("A") or g.pressed("START"):
            start()
        return
    speed = 220  # pixels per second: always multiply movement by dt
    x += (g.down("RIGHT") - g.down("LEFT")) * speed * dt
    y += (g.down("DOWN") - g.down("UP")) * speed * dt
    x = max(0, min(g.W - 32, x))
    y = max(40, min(g.H - 28, y))

    timer -= dt
    if timer <= 0:
        timer = 0.5
        kind = stars if random.random() < 0.6 else blocks
        kind.append([random.randint(0, g.W - 24), -24])
    fall = (120 + score * 4) * dt
    me = (x, y, 32, 28)
    for s in stars[:]:
        s[1] += fall
        if g.hit(me, (s[0], s[1], 20, 20)):
            stars.remove(s)
            score += 1
            g.tone(700, 80, 1100)
        elif s[1] > g.H:
            stars.remove(s)
    for b in blocks[:]:
        b[1] += fall
        if g.hit(me, (b[0], b[1], 24, 24)):
            g.tone(300, 400, 80, wave="noise")
            state = "over"
            if score > best:
                best = score
                g.save({"best": best})
        elif b[1] > g.H:
            blocks.remove(b)


def draw():
    g.clear((16, 20, 40))
    if state == "title":
        g.text("STAR CATCHER", g.W / 2, 120, g.YELLOW, 44, "center")
        g.text("A - start", g.W / 2, 230, g.WHITE, 24, "center")
        g.text("SELECT+START - quit", g.W / 2, 270, g.GRAY, 18, "center")
        g.text("best: %d" % best, g.W / 2, 330, g.GRAY, 20, "center")
        return
    for s in stars:
        g.draw(STAR, s[0], s[1], 4)
    for b in blocks:
        g.rect(b[0], b[1], 24, 24, g.RED)
    g.draw(SHIP, x, y, 4)
    g.text("score %d" % score, 10, 8)
    g.text("best %d" % best, g.W - 10, 8, g.GRAY, 20, "right")
    if state == "over":
        g.rect(0, 150, g.W, 130, g.BLACK, 180)
        g.text("GAME OVER", g.W / 2, 165, g.RED, 40, "center")
        g.text("A - again", g.W / 2, 230, g.WHITE, 22, "center")


g.run(update, draw, "Star Catcher")
