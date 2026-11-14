"""Network example: 2-4 consoles on the same Wi-Fi, top-down arena, shoot the others.

Menu: A - host a game, B - join. D-pad - move, A - fire.
Pattern to copy (works for any network game):
  * the HOST runs the whole game and sends the full state to everyone;
  * every other player only sends its buttons and draws the state it receives.
"""
import random

import r36t as g

NAME = "netduel"          # must be the same on both sides, unique for your game
COLORS = [g.BLUE, g.RED, g.GREEN, g.YELLOW]
state = "menu"            # menu, play
net = None
my_id = "0"               # the host is "0"; the host tells each joined player its id
players = {}              # id -> {"x", "y", "fx", "fy", "cool", "score"}
bullets = []              # [x, y, dx, dy, owner id]
inputs = {}               # host only: id -> [dx, dy, fire]
frame = 0


def begin(role):
    global net, state
    net = g.host(NAME) if role == "host" else g.join(NAME)
    state = "play"


def spawn(p):
    p["x"], p["y"] = random.randint(40, g.W - 60), random.randint(60, g.H - 60)


def simulate(dt):
    """Host only: the real game rules."""
    ids = ["0"] + [str(pid) for pid in net.peers]
    for i in ids:
        if i not in players:
            players[i] = {"fx": 1, "fy": 0, "cool": 0, "score": 0}
            spawn(players[i])
    for i in list(players):
        if i not in ids:
            del players[i]            # that player left
    for i, p in players.items():
        dx, dy, fire = inputs.get(i, [0, 0, 0])
        p["x"] = max(0, min(g.W - 20, p["x"] + dx * 160 * dt))
        p["y"] = max(30, min(g.H - 20, p["y"] + dy * 160 * dt))
        if dx or dy:
            p["fx"], p["fy"] = dx, dy
        p["cool"] -= dt
        if fire and p["cool"] <= 0:
            p["cool"] = 0.4
            bullets.append([p["x"] + 8, p["y"] + 8, p["fx"], p["fy"], i])
            g.tone(600, 50, 300)
    for b in bullets[:]:
        b[0] += b[2] * 320 * dt
        b[1] += b[3] * 320 * dt
        if not (0 < b[0] < g.W and 30 < b[1] < g.H):
            bullets.remove(b)
            continue
        for i, p in players.items():
            if i != b[4] and g.hit((b[0], b[1], 4, 4), (p["x"], p["y"], 20, 20)):
                bullets.remove(b)
                if b[4] in players:
                    players[b[4]]["score"] += 1
                spawn(p)
                g.tone(200, 150, 60, wave="noise")
                break


def update(dt):
    global players, bullets, my_id, frame
    if state == "menu":
        if g.ROLE:                    # set by "python tool.py run/check --net": skip the menu
            begin(g.ROLE)
        elif g.pressed("A"):
            begin("host")
        elif g.pressed("B"):
            begin("join")
        return
    frame += 1
    mine = [g.down("RIGHT") - g.down("LEFT"), g.down("DOWN") - g.down("UP"), int(g.down("A"))]
    messages = net.recv()             # call it every frame, on the host and on clients
    if net.is_host:
        for pid, msg in messages:
            inputs[str(pid)] = msg
        inputs["0"] = mine
        simulate(dt)
        if frame % 2 == 0:            # 30 state updates per second are enough
            for pid in list(net.peers):
                net.send({"you": str(pid), "p": players, "b": bullets}, to=pid)
    else:
        for _, msg in messages:
            my_id, players, bullets = msg["you"], msg["p"], msg["b"]
        net.send(mine)


def draw():
    g.clear((24, 28, 44))
    if state == "menu":
        g.text("NET DUEL", g.W / 2, 100, g.YELLOW, 46, "center")
        g.text("A - host a game", g.W / 2, 200, g.WHITE, 24, "center")
        g.text("B - join a game", g.W / 2, 240, g.WHITE, 24, "center")
        g.text("both consoles on the same Wi-Fi", g.W / 2, 300, g.GRAY, 18, "center")
        return
    for b in bullets:
        g.rect(b[0], b[1], 4, 4, g.WHITE)
    for n, (i, p) in enumerate(sorted(players.items())):
        color = COLORS[int(i) % 4]
        g.rect(p["x"], p["y"], 20, 20, color)
        if i == my_id:
            g.rect(p["x"] - 3, p["y"] - 3, 26, 26, g.WHITE, fill=False)
        g.text(p["score"], 20 + n * 60, 2, color, 22)
    if not net.connected:
        g.text("waiting for players..." if net.is_host else "searching for a host...",
               g.W / 2, g.H - 30, g.GRAY, 18, "center")


g.run(update, draw, "Net Duel")
