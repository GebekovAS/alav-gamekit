"""Platformer example: side-scrolling tile level, jumping, stomping enemies, gems, exit.

D-pad - run, A - jump (hold for a higher jump), B - run faster.
Pattern to copy: the level is text (LEVEL), one character = one 32 px tile.
"""
import r36t as g

T = 32          # tile size in pixels
TOP = 24        # the level is drawn below the HUD line
LEVEL = [
    "................................................................................",
    "................................................................................",
    "................................................................................",
    "........................................o.o.o...................................",
    ".......................................=====...............ooo..................",
    "...............o.o........................................=====.................",
    "..............====.........o..................o.........................o.......",
    "..........................===........==......===.....................====.......",
    ".........o..........=...........==..................=====.......==..............",
    "........===.........==....................................................F.....",
    "..P............s....===...s.........^^.....s......s...........==.....s....F.....",
    "####################===#########...######################...####################",
    "####################===#########...######################...####################",
]
COLS, ROWS = len(LEVEL[0]), len(LEVEL)
assert all(len(row) == COLS for row in LEVEL), "every LEVEL row must have the same length"

HERO = g.sprite([
    "..gggg..",
    ".gggggg.",
    ".gwkgwk.",
    ".gggggg.",
    "..gyyg..",
    ".gggggg.",
    ".gg..gg.",
], {"g": (90, 200, 110), "w": (255, 255, 255), "k": (20, 30, 20), "y": (240, 220, 120)})
SLIME = g.sprite([
    "..pppp..",
    ".pppppp.",
    "pwkppwkp",
    "pppppppp",
    "pppppppp",
], {"p": (190, 90, 210), "w": (255, 255, 255), "k": (30, 10, 40)})
GEM = g.sprite([
    ".ccc.",
    "ccwcc",
    "ccccc",
    ".ccc.",
    "..c..",
], {"c": (80, 220, 240), "w": (255, 255, 255)})

state = "title"  # title, play, dead, win
hero = {}
slimes, gems = [], []
score = lives = 0
cam = 0.0


def solid(cx, cy):
    if cx < 0 or cx >= COLS:
        return True          # invisible walls at both ends of the level
    if cy < 0 or cy >= ROWS:
        return False         # below the level is a pit
    return LEVEL[cy][cx] in "#="


def blocked(x, y, w, h):
    for cy in range(int(y // T), int((y + h - 1) // T) + 1):
        for cx in range(int(x // T), int((x + w - 1) // T) + 1):
            if solid(cx, cy):
                return True
    return False


def move(e, dx, dy):
    """Move a thing {x, y, w, h, vx, vy} and stop at solid tiles. Sets e["ground"]."""
    e["x"] += dx
    if blocked(e["x"], e["y"], e["w"], e["h"]):
        if dx > 0:
            e["x"] = (e["x"] + e["w"]) // T * T - e["w"]
        else:
            e["x"] = (e["x"] // T + 1) * T
        e["vx"] = 0
    e["y"] += dy
    e["ground"] = False
    if blocked(e["x"], e["y"], e["w"], e["h"]):
        if dy > 0:
            e["y"] = (e["y"] + e["h"]) // T * T - e["h"]
            e["ground"] = True
        else:
            e["y"] = (e["y"] // T + 1) * T
        e["vy"] = 0


def load_level():
    global hero, slimes, gems, cam
    slimes, gems, cam = [], [], 0.0
    for cy, row in enumerate(LEVEL):
        for cx, ch in enumerate(row):
            if ch == "P":
                hero = {"x": cx * T, "y": cy * T, "w": 24, "h": 28, "vx": 0, "vy": 0, "ground": False, "left": False}
            elif ch == "s":
                slimes.append({"x": cx * T, "y": cy * T + 12, "w": 32, "h": 20, "vx": -50, "vy": 0, "ground": False})
            elif ch == "o":
                gems.append((cx * T + 6, cy * T + 6))


def start():
    global state, score, lives
    state, score, lives = "play", 0, 3
    load_level()


def lose_life():
    global state, lives
    lives -= 1
    g.tone(400, 350, 90)
    if lives <= 0:
        state = "dead"
    else:
        load_level()


def update(dt):
    global state, score, cam
    if state != "play":
        if g.pressed("A") or g.pressed("START"):
            start()
        return
    h = hero
    run = 260 if g.down("B") else 190
    h["vx"] = (g.down("RIGHT") - g.down("LEFT")) * run
    if h["vx"]:
        h["left"] = h["vx"] < 0
    if g.pressed("A") and h["ground"]:
        h["vy"] = -560
        g.tone(300, 90, 600)
    if not g.down("A") and h["vy"] < -200:
        h["vy"] = -200                       # released early: short hop
    h["vy"] = min(h["vy"] + 1500 * dt, 600)  # gravity, with a top falling speed
    move(h, h["vx"] * dt, h["vy"] * dt)
    box = (h["x"], h["y"], h["w"], h["h"])

    if h["y"] > ROWS * T:
        return lose_life()
    cx, cy = int((h["x"] + 12) // T), int((h["y"] + 14) // T)
    here = LEVEL[cy][cx] if 0 <= cy < ROWS and 0 <= cx < COLS else "."
    if here == "^":
        return lose_life()
    if here == "F":
        state = "win"
        g.tone(500, 500, 1000, wave="sine")
        return

    for gem in gems[:]:
        if g.hit(box, (gem[0], gem[1], 20, 20)):
            gems.remove(gem)
            score += 10
            g.tone(900, 60, 1300)

    for s in slimes[:]:
        if abs(s["x"] - h["x"]) > g.W:
            continue                         # far away things sleep: saves CPU
        speed = s["vx"]
        s["vy"] = min(s["vy"] + 1500 * dt, 600)
        move(s, speed * dt, s["vy"] * dt)
        ahead = s["x"] + (s["w"] + 2 if speed > 0 else -2)
        if s["vx"] == 0 or (s["ground"] and not solid(int(ahead // T), int((s["y"] + s["h"] + 2) // T))):
            s["vx"] = -speed                 # turn around at walls and ledges
        if g.hit(box, (s["x"], s["y"], s["w"], s["h"])):
            if h["vy"] > 0 and h["y"] + h["h"] - s["y"] < 16:
                slimes.remove(s)             # landed on top: stomp
                h["vy"] = -350
                score += 50
                g.tone(200, 100, 500)
            else:
                return lose_life()

    cam = max(0, min(h["x"] - g.W / 2, COLS * T - g.W))


def draw():
    g.clear((120, 190, 240))
    if state == "title":
        g.text("GEM HOPPER", g.W / 2, 110, g.WHITE, 46, "center")
        g.text("A - start", g.W / 2, 220, g.WHITE, 24, "center")
        g.text("D-pad run   A jump   B faster", g.W / 2, 270, (40, 70, 110), 18, "center")
        g.draw(HERO, g.W / 2 - 28, 320, 7)
        return
    first = int(cam // T)
    for cy, row in enumerate(LEVEL):
        y = TOP + cy * T
        for cx in range(first, min(first + g.W // T + 2, COLS)):   # only the visible columns
            ch = row[cx]
            x = cx * T - cam
            if ch == "#":
                g.rect(x, y, T, T, (120, 80, 50))
                if not solid(cx, cy - 1):
                    g.rect(x, y, T, 8, (80, 180, 80))
            elif ch == "=":
                g.rect(x, y, T, T, (200, 120, 70))
                g.rect(x, y, T, T, (140, 70, 40), fill=False)
            elif ch == "^":
                g.rect(x + 4, y + 16, 24, 16, (90, 90, 100))
                g.rect(x + 12, y + 6, 8, 10, (200, 200, 210))
            elif ch == "F":
                g.rect(x + 4, y, 24, T, (250, 220, 90), 200)
    for gem in gems:
        if -T < gem[0] - cam < g.W:
            g.draw(GEM, gem[0] - cam, TOP + gem[1], 4)
    for s in slimes:
        if -T < s["x"] - cam < g.W:
            g.draw(SLIME, s["x"] - cam, TOP + s["y"], 4, flip=s["vx"] > 0)
    g.draw(HERO, hero["x"] - cam - 4, TOP + hero["y"], 4, flip=hero["left"])
    g.rect(0, 0, g.W, TOP, g.BLACK)
    g.text("score %d" % score, 8, 1, g.WHITE, 18)
    g.text("lives %d" % lives, g.W - 8, 1, g.WHITE, 18, "right")
    if state in ("dead", "win"):
        g.rect(0, 150, g.W, 130, g.BLACK, 180)
        g.text("YOU WIN!" if state == "win" else "GAME OVER", g.W / 2, 165, g.YELLOW, 40, "center")
        g.text("score %d    A - again" % score, g.W / 2, 230, g.WHITE, 22, "center")


g.run(update, draw, "Gem Hopper")
