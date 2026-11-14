"""Puzzle example: turn-based grid game (push crates onto targets), levels, undo.

D-pad - step, B - undo, X - restart the level.
Pattern to copy: nothing moves by itself, so update() only reacts to g.pressed().
"""
import r36t as g

T = 40
LEVELS = [
    ["#######",
     "#.....#",
     "#.c.x.#",
     "#..P..#",
     "#######"],
    ["########",
     "#..x...#",
     "#.cc.#.#",
     "#.P..x.#",
     "########"],
    ["#########",
     "#...#...#",
     "#.c.x.c.#",
     "#.#.P.#.#",
     "#.x.c.x.#",
     "#########"],
]
MOVES = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}

level = 0
walls, targets, crates = set(), set(), set()
player = (0, 0)
history = []
steps = 0
done = False


def load(n):
    global level, walls, targets, crates, player, history, steps
    level, walls, targets, crates, history, steps = n, set(), set(), set(), [], 0
    for y, row in enumerate(LEVELS[n]):
        for x, ch in enumerate(row):
            if ch == "#":
                walls.add((x, y))
            elif ch == "x":
                targets.add((x, y))
            elif ch == "c":
                crates.add((x, y))
            elif ch == "P":
                player = (x, y)


def update(dt):
    global player, crates, steps, done
    if done:
        if g.pressed("A") or g.pressed("START"):
            done = False
            load(0)
        return
    if g.pressed("X"):
        load(level)
    if g.pressed("B") and history:
        player, crates = history.pop()
        steps -= 1
    for name, (dx, dy) in MOVES.items():
        if g.pressed(name):
            to = (player[0] + dx, player[1] + dy)
            beyond = (to[0] + dx, to[1] + dy)
            if to in walls or (to in crates and (beyond in walls or beyond in crates)):
                g.tone(120, 60)
                break
            history.append((player, set(crates)))
            if to in crates:
                crates.remove(to)
                crates.add(beyond)
                g.tone(300, 60, 200)
            player = to
            steps += 1
            break
    if crates == targets:
        g.tone(500, 300, 1000, wave="sine")
        if level + 1 < len(LEVELS):
            load(level + 1)
        else:
            done = True


def draw():
    g.clear((35, 40, 60))
    rows = LEVELS[level]
    ox = (g.W - len(rows[0]) * T) / 2
    oy = (g.H - len(rows) * T) / 2 + 10
    for (x, y) in walls:
        g.rect(ox + x * T, oy + y * T, T - 1, T - 1, (90, 100, 130))
    for (x, y) in targets:
        g.rect(ox + x * T + 12, oy + y * T + 12, 16, 16, g.YELLOW, fill=False)
    for (x, y) in crates:
        g.rect(ox + x * T + 4, oy + y * T + 4, T - 8, T - 8, g.GREEN if (x, y) in targets else (200, 140, 70))
    g.circle(ox + player[0] * T + T / 2, oy + player[1] * T + T / 2, 14, (90, 170, 255))
    g.text("level %d/%d" % (level + 1, len(LEVELS)), 10, 8)
    g.text("steps %d" % steps, g.W - 10, 8, g.GRAY, 20, "right")
    g.text("B undo   X restart", g.W / 2, g.H - 28, g.GRAY, 16, "center")
    if done:
        g.rect(0, 150, g.W, 120, g.BLACK, 190)
        g.text("ALL LEVELS SOLVED!", g.W / 2, 165, g.YELLOW, 36, "center")
        g.text("A - play again", g.W / 2, 225, g.WHITE, 22, "center")


load(0)
g.run(update, draw, "Crate Keeper")
