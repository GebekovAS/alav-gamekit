"""Tank arena example: top-down grid map, destructible walls, enemy waves, a core to defend.

D-pad - drive, A - fire. Destroy all 12 drones; do not let them shoot the core.
Pattern to copy: the map is text (MAP) turned into a list of lists, so tiles can be destroyed.

Rules and the whole API: AGENTS.md in the repository root.
"""
import random

import r36t as g

T = 32               # tile size
OX, OY = 20, 12      # where the 13x13 field starts on screen
SIZE = 28            # tank size (2 px smaller than a tile on each side)
MAP = [
    "....#...#....",
    ".##.#.@.#.##.",
    ".#.....~...#.",
    "...##.~~.##..",
    ".#..#...#..#.",
    ".#.@..#..@.#.",
    "....#####....",
    "##.........##",
    "...#.~~~.#...",
    ".#.#.....#.#.",
    ".#.........#.",
    ".....###.....",
    "...#.#C#.#...",
]
N = len(MAP)
assert all(len(row) == N for row in MAP), "MAP must be square"
DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]   # up, right, down, left
SPAWNS = [(0, 0), (6, 0), (12, 0)]

ART = [
    "...b...",
    "...b...",
    "tbbbbbt",
    "tbdddbt",
    "tbdddbt",
    "tbbbbbt",
    "t.....t",
]
PLAYER = g.sprite(ART, {"t": (60, 60, 60), "b": (240, 200, 70), "d": (180, 140, 40)})
DRONE = g.sprite(ART, {"t": (60, 60, 60), "b": (200, 210, 220), "d": (220, 70, 70)})

state = "title"   # title, play, lost, won
grid = []
me = None
drones, shots = [], []
reserve = lives = score = 0
spawn_timer = 0.0


def tank(cx, cy, d, enemy):
    return {"x": cx * T + 2, "y": cy * T + 2, "d": d, "cool": 0.0, "enemy": enemy, "think": 0.0}


def start():
    global state, grid, me, drones, shots, reserve, lives, score, spawn_timer
    grid = [list(row) for row in MAP]
    me = tank(4, 12, 0, False)
    drones, shots = [], []
    state, reserve, lives, score, spawn_timer = "play", 12, 3, 0, 0.5


def tile(px, py):
    """Tile character at a pixel of the field; outside the field counts as steel."""
    if px < 0 or py < 0 or px >= N * T or py >= N * T:
        return "@"
    return grid[int(py // T)][int(px // T)]


def free(t, x, y):
    for px, py in ((x, y), (x + SIZE - 1, y), (x, y + SIZE - 1), (x + SIZE - 1, y + SIZE - 1)):
        if tile(px, py) != ".":
            return False
    for other in drones + [me]:
        if other is not t and g.hit((x, y, SIZE, SIZE), (other["x"], other["y"], SIZE, SIZE)):
            return False
    return True


def drive(t, d, dist):
    """Turn to direction d and move; returns False when the way is blocked."""
    if d != t["d"]:
        t["d"] = d
        # line up with the half-tile grid on turns, so tanks fit between walls
        t["x"] = round((t["x"] - 2) / 16) * 16 + 2
        t["y"] = round((t["y"] - 2) / 16) * 16 + 2
    x, y = t["x"] + DIRS[d][0] * dist, t["y"] + DIRS[d][1] * dist
    if not free(t, x, y):
        return False
    t["x"], t["y"] = x, y
    return True


def fire(t):
    if t["cool"] > 0:
        return
    t["cool"] = 0.6 if not t["enemy"] else 1.2
    dx, dy = DIRS[t["d"]]
    shots.append({"x": t["x"] + 11 + dx * 14, "y": t["y"] + 11 + dy * 14, "dx": dx, "dy": dy, "enemy": t["enemy"]})
    if not t["enemy"]:
        g.tone(500, 60, 200)


def update(dt):
    global state, reserve, lives, score, spawn_timer, me
    if state != "play":
        if g.pressed("A") or g.pressed("START"):
            start()
        return
    for d, name in enumerate(("UP", "RIGHT", "DOWN", "LEFT")):
        if g.down(name):
            drive(me, d, 110 * dt)
            break
    me["cool"] -= dt
    if g.down("A"):
        fire(me)

    spawn_timer -= dt
    if spawn_timer <= 0 and reserve > 0 and len(drones) < 4:
        spawn_timer = 2.5
        cx, cy = random.choice(SPAWNS)
        new = tank(cx, cy, 2, True)
        if free(new, new["x"], new["y"]):
            drones.append(new)
            reserve -= 1
    for t in drones:
        t["cool"] -= dt
        t["think"] -= dt
        if t["think"] <= 0 or not drive(t, t["d"], 70 * dt):
            t["think"] = random.uniform(0.5, 2.0)
            drive(t, random.choice([0, 1, 1, 2, 2, 2, 2, 3, 3]), 0)   # mostly down, towards the core
        if random.random() < 1.2 * dt:
            fire(t)

    for s in shots[:]:
        s["x"] += s["dx"] * 300 * dt
        s["y"] += s["dy"] * 300 * dt
        ch = tile(s["x"] + 3, s["y"] + 3)
        box = (s["x"], s["y"], 6, 6)
        gone = ch in "#@C"
        if ch == "#":
            grid[int((s["y"] + 3) // T)][int((s["x"] + 3) // T)] = "."
            g.tone(160, 50, wave="noise")
        elif ch == "C":
            state = "lost"
            g.tone(300, 600, 60, wave="noise")
        if s["enemy"] and g.hit(box, (me["x"], me["y"], SIZE, SIZE)):
            gone = True
            lives -= 1
            g.tone(250, 300, 80)
            me = tank(4, 12, 0, False)
            if lives <= 0:
                state = "lost"
        if not s["enemy"]:
            for t in drones[:]:
                if g.hit(box, (t["x"], t["y"], SIZE, SIZE)):
                    drones.remove(t)
                    gone = True
                    score += 100
                    g.tone(120, 200, 40, wave="noise")
                    break
        if gone:
            shots.remove(s)
    if reserve == 0 and not drones:
        state = "won"
        g.tone(500, 500, 1000, wave="sine")


COLORS = {"#": (190, 100, 60), "@": (170, 175, 185), "~": (50, 110, 220), "C": (120, 240, 220)}


def draw():
    g.clear((30, 32, 40))
    if state == "title":
        g.text("CORE GUARD", g.W / 2, 110, g.YELLOW, 46, "center")
        g.text("A - start", g.W / 2, 210, g.WHITE, 24, "center")
        g.text("D-pad drive   A fire   protect the core", g.W / 2, 260, g.GRAY, 18, "center")
        g.draw(PLAYER, g.W / 2 - 28, 310, 8)
        return
    g.rect(OX, OY, N * T, N * T, g.BLACK)
    for cy, row in enumerate(grid):
        for cx, ch in enumerate(row):
            if ch != ".":
                x, y = OX + cx * T, OY + cy * T
                g.rect(x, y, T, T, COLORS[ch])
                if ch == "#":
                    g.rect(x, y + 14, T, 3, (110, 55, 35))
                elif ch == "C":
                    g.rect(x + 8, y + 8, 16, 16, g.WHITE)
    for t in drones + [me]:
        g.draw(DRONE if t["enemy"] else PLAYER, OX + t["x"], OY + t["y"], 4, angle=t["d"] * 90)
    for s in shots:
        g.rect(OX + s["x"], OY + s["y"], 6, 6, g.RED if s["enemy"] else g.WHITE)
    x = OX + N * T + 20
    g.text("SCORE", x, 30, g.GRAY, 18)
    g.text(score, x, 52, g.WHITE, 26)
    g.text("LIVES", x, 110, g.GRAY, 18)
    g.text(lives, x, 132, g.WHITE, 26)
    g.text("DRONES", x, 190, g.GRAY, 18)
    g.text(reserve + len(drones), x, 212, g.WHITE, 26)
    if state in ("lost", "won"):
        g.rect(0, 150, g.W, 130, g.BLACK, 190)
        g.text("CORE SAVED!" if state == "won" else "CORE LOST", g.W / 2, 165, g.YELLOW, 40, "center")
        g.text("score %d    A - again" % score, g.W / 2, 230, g.WHITE, 22, "center")


g.run(update, draw, "Core Guard")
