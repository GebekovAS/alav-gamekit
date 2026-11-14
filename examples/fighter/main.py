"""Fighting example: one-on-one, punches, kicks, block, jump, health bars, rounds, CPU opponent.

LEFT/RIGHT - walk, UP - jump, A - punch, B - kick, X (hold) - block.
Pattern to copy: both fighters are driven by the same step() with a "controls" dict,
so the opponent can be a CPU (here), a second pad, or a network player.
"""
import random

import r36t as g

FLOOR = 360
BODY = [
    "....hhhh....",
    "...hhhhhh...",
    "...hssssh...",
    "...sksskss..",
    "...ssssss...",
    "....ssss....",
    "..cccccccc..",
    ".cccccccccc.",
    ".ccbbbbbbcc.",
    ".cccccccccc.",
    "..cccccccc..",
    "..bbbbbbbb..",
    "..ccc..ccc..",
    "..ccc..ccc..",
    "..ccc..ccc..",
    ".kkkk..kkkk.",
]
SKIN = {"s": (240, 200, 160), "k": (30, 30, 40), "b": (30, 30, 40)}
HERO = g.sprite(BODY, dict(SKIN, h=(60, 40, 30), c=(70, 130, 255)))
RIVAL = g.sprite(BODY, dict(SKIN, h=(230, 230, 230), c=(220, 70, 70)))
SCALE, FW, FH = 5, 60, 80   # the sprite is 12x16 pixels, drawn 5x bigger

# attack name -> (total time, hit starts, hit ends, reach in px, damage, height of the blow)
MOVES = {"punch": (0.28, 0.08, 0.16, 46, 8, 28), "kick": (0.45, 0.15, 0.28, 62, 14, 56)}

state = "title"   # title, fight, pause (between rounds), over
p1, p2 = {}, {}
wins = [0, 0]
clock = pause = 0.0
banner = ""


def fighter(x, facing, spr):
    return {"x": x, "y": FLOOR - FH, "vy": 0, "face": facing, "hp": 100, "spr": spr,
            "act": "idle", "t": 0.0, "landed": False}


def new_round():
    global p1, p2, clock, state
    p1, p2 = fighter(150, 1, HERO), fighter(g.W - 150 - FW, -1, RIVAL)
    clock, state = 60.0, "fight"


def step(f, foe, c, dt):
    """Advance one fighter. c = {"move": -1/0/1, "jump", "punch", "kick", "block": True/False}."""
    f["face"] = 1 if foe["x"] > f["x"] else -1
    on_floor = f["y"] >= FLOOR - FH
    if f["act"] in MOVES or f["act"] == "hurt":
        f["t"] -= dt
        if f["t"] <= 0:
            f["act"] = "idle"
    if f["act"] in ("idle", "block"):
        f["act"] = "block" if c["block"] and on_floor else "idle"
        if f["act"] == "idle":
            f["x"] += c["move"] * 170 * dt
            if c["jump"] and on_floor:
                f["vy"] = -620
            for name in MOVES:
                if c[name]:
                    f["act"], f["t"], f["landed"] = name, MOVES[name][0], False
                    g.tone(180, 50, 120, wave="noise")
    f["vy"] += 1700 * dt
    f["y"] = min(f["y"] + f["vy"] * dt, FLOOR - FH)
    f["x"] = max(10, min(g.W - FW - 10, f["x"]))

    if f["act"] in MOVES and not f["landed"]:
        total, t0, t1, reach, damage, height = MOVES[f["act"]]
        if t0 <= total - f["t"] <= t1:
            blow = (f["x"] + FW / 2 + (0 if f["face"] > 0 else -reach), f["y"] + height, reach, 12)
            if g.hit(blow, (foe["x"] + 10, foe["y"], FW - 20, FH)):
                f["landed"] = True
                if foe["act"] == "block":
                    damage = damage // 4
                    g.tone(900, 40)
                else:
                    foe["act"], foe["t"] = "hurt", 0.25
                    g.tone(140, 120, 60)
                foe["hp"] = max(0, foe["hp"] - damage)
                foe["x"] += f["face"] * 14


def cpu(f, foe):
    """A simple opponent: walk in, attack when close, sometimes block."""
    gap = abs(foe["x"] - f["x"])
    c = {"move": 0, "jump": False, "punch": False, "kick": False, "block": False}
    if gap > 70:
        c["move"] = f["face"]
    elif foe["act"] in MOVES and random.random() < 0.5:
        c["block"] = True
    elif random.random() < 0.06:
        c[random.choice(["punch", "kick"])] = True
    if random.random() < 0.004:
        c["jump"] = True
    return c


def update(dt):
    global state, clock, pause, banner, wins
    if state in ("title", "over"):
        if g.pressed("A") or g.pressed("START"):
            wins = [0, 0]
            new_round()
        return
    if state == "pause":
        pause -= dt
        if pause <= 0:
            if max(wins) >= 2:
                state = "over"
            else:
                new_round()
        return
    me = {"move": g.down("RIGHT") - g.down("LEFT"), "jump": g.pressed("UP"),
          "punch": g.pressed("A"), "kick": g.pressed("B"), "block": g.down("X")}
    step(p1, p2, me, dt)
    step(p2, p1, cpu(p2, p1), dt)
    clock -= dt
    if p1["hp"] <= 0 or p2["hp"] <= 0 or clock <= 0:
        winner = 0 if p1["hp"] > p2["hp"] else 1
        wins[winner] += 1
        banner = "YOU WIN THE ROUND" if winner == 0 else "RIVAL WINS THE ROUND"
        state, pause = "pause", 2.0
        g.tone(400, 300, 800 if winner == 0 else 150)


def draw_fighter(f):
    x, y = f["x"], f["y"]
    if f["act"] == "hurt":
        x -= f["face"] * 6
    g.draw(f["spr"], x, y, SCALE, flip=f["face"] < 0)
    hand = x + FW / 2
    if f["act"] in MOVES:
        reach, height = MOVES[f["act"]][3], MOVES[f["act"]][5]
        g.rect(hand if f["face"] > 0 else hand - reach, y + height, reach, 12,
               (240, 200, 160) if f["act"] == "punch" else (30, 30, 40))
    elif f["act"] == "block":
        g.rect(x + (FW - 8 if f["face"] > 0 else 0), y + 22, 8, 34, (240, 200, 160))


def draw():
    g.clear((40, 30, 60))
    g.rect(0, 250, g.W, 110, (70, 50, 90))
    g.rect(0, FLOOR, g.W, g.H - FLOOR, (110, 80, 60))
    if state == "title":
        g.text("DOJO DUEL", g.W / 2, 90, g.YELLOW, 48, "center")
        g.text("A - fight", g.W / 2, 180, g.WHITE, 24, "center")
        g.text("A punch   B kick   X block   UP jump", g.W / 2, 215, g.GRAY, 18, "center")
        g.draw(HERO, 170, FLOOR - FH, SCALE)
        g.draw(RIVAL, 370, FLOOR - FH, SCALE, flip=True)
        return
    for f in (p1, p2):
        draw_fighter(f)
    for i, f in enumerate((p1, p2)):
        x = 20 if i == 0 else g.W - 260
        g.rect(x, 20, 240, 18, (90, 20, 20))
        width = 240 * f["hp"] / 100
        g.rect(x if i == 0 else x + 240 - width, 20, width, 18, g.YELLOW)
        for w in range(wins[i]):
            g.rect(x + (w * 16 if i == 0 else 228 - w * 16), 44, 12, 12, g.GREEN)
    g.text("%d" % max(0, clock), g.W / 2, 12, g.WHITE, 28, "center")
    if state == "pause":
        g.text(banner, g.W / 2, 120, g.WHITE, 30, "center")
    if state == "over":
        g.rect(0, 100, g.W, 120, g.BLACK, 180)
        g.text("VICTORY!" if wins[0] > wins[1] else "DEFEAT", g.W / 2, 115, g.YELLOW, 42, "center")
        g.text("A - rematch", g.W / 2, 180, g.WHITE, 22, "center")


g.run(update, draw, "Dojo Duel")
