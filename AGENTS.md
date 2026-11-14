# ALAV Gamekit - instructions for AI agents

You make games for **handheld consoles running ALAV Store**. Follow this file exactly. It is complete:
you do not need to search the web or read the kit's source.

## If you were asked to download, install or prepare this kit

This kit usually sits inside a user's project folder (for example `my-project/alav-gamekit/`).
Agent sessions start in the project folder, where these instructions would not be seen. So finish
the preparation with one command, run inside the kit folder:

`python tool.py setup`

It writes the agent instructions into the project folder and creates `games/` there for the user's
games. Then tell the user: start a new session in the project folder and ask for a game.

## The 5 steps (always in this order)

1. **Create** the game from the closest example (see the table below):
   `python tool.py new my-game --from platformer --title "My Game"`
2. **Edit** only `games/my-game/main.py` (and `games/my-game/assets/` if you add files).
3. **Check**: `python tool.py check my-game`
   - `FAIL` -> read the reasons, fix, run the check again. Repeat until `PASS`.
   - Network game: `python tool.py check my-game --net`
4. **Look** at the screenshots the check saved in `out/check/my-game/`. Open the PNG files; if you
   cannot view images, read the `.txt` file next to each PNG: it is the same screen drawn with
   characters, plus every text on it with its position. If something looks wrong (nothing
   visible, text off screen), fix it and go to step 3.
   The check presses random buttons, so it rarely gets past the first minute of the game. To see a
   later screen (level 2, game over), temporarily start the game in that state, run the check,
   read the screenshot, then **put the normal start back**.
5. **Pack**: `python tool.py pack my-game` -> files in `dist/`. Tell the user: copy
   `dist/<Title>.sh` to the `ports_scripts` folder of the SD card and start it from **Ports**.

Never say the game is done before step 3 prints `PASS` and you have looked at the screenshots.

No setup is needed: `tool.py` downloads SDL2 by itself the first time. Do not install anything
and do not add `sys.path` tricks to the game.

| Example (`--from`) | Use it for |
| --- | --- |
| `minimal` | anything simple: dodge, catch, shoot; the default |
| `platformer` | side view, jumping, tile levels written as text, scrolling camera |
| `fighter` | one-on-one fighting, health bars, rounds, a CPU opponent |
| `tanks` | top-down grid map with destructible walls, enemies, bullets |
| `puzzle` | turn-based grid puzzles, levels, undo |
| `netduel` | multiplayer over Wi-Fi (host + join) |

## Hard rules

- The game is **one process, pure Python 3.11, standard library + `import alav as g` only**.
  No pygame, numpy, pip packages, no `input()`, no threads, no web requests.
- **Never write your own main loop** and never call `time.sleep`. Define `update(dt)` and
  `draw()` and call `g.run(update, draw, "Title")` as the last line of `main.py`.
- The screen is always **600 x 440** pixels: `g.W`, `g.H`. (0, 0) is the top-left corner.
  Consoles differ; the kit stretches this picture to the real screen, keeping its shape.
- **Multiply every movement by `dt`** (seconds since the last frame): `x += speed * dt`.
- The console is slow (about 30x slower than a PC). Keep it light:
  at most ~100 moving objects, at most 400 draw calls per frame, no loops over every pixel,
  no "every object against every object" loops over long lists. `check` measures this.
- Create sprites **once at the top of the file**, never inside `update()` or `draw()`.
- Python 3.11 syntax only. Inside an f-string use the other quote: `f"{d['key']}"`.
  When unsure, use `"score %d" % score`.
- Every screen must tell the player which button to press. The player has no keyboard.
- **SELECT+START quits** the game. The kit does it for you: do not use that combination.
- Do not edit `kit/`, `tool.py` or `examples/`. Your game lives in `games/<slug>/`.
- Make **original** games. Do not copy the names, characters, graphics, music or levels of
  existing games. "A platformer" is fine; a copy of a famous platformer is not.
- Text: the font has Latin and Cyrillic letters. No emoji.

## Game skeleton

```python
import alav as g

state = "title"          # "title" -> "play" -> "over"
x, score = 300.0, 0

def update(dt):          # game rules: runs every frame
    global state, x, score
    if state != "play":
        if g.pressed("A"):
            state, x, score = "play", 300.0, 0
        return
    x += (g.down("RIGHT") - g.down("LEFT")) * 200 * dt

def draw():              # only drawing: never change the game here
    g.clear((20, 20, 40))
    if state == "title":
        g.text("MY GAME", g.W / 2, 150, g.YELLOW, 40, "center")
        g.text("A - start", g.W / 2, 230, g.WHITE, 22, "center")
        return
    g.rect(x, 380, 40, 20, g.GREEN)
    g.text("score %d" % score, 10, 8)

g.run(update, draw, "My Game")
```

## API (everything there is)

Colors are `(r, g, b)` with values 0-255. Ready ones: `g.WHITE g.BLACK g.GRAY g.RED g.GREEN
g.BLUE g.YELLOW`.

**Drawing** (call only inside `draw()`; later calls are drawn on top)

| Call | What it does |
| --- | --- |
| `g.clear(color)` | fill the screen; first line of `draw()` |
| `g.rect(x, y, w, h, color, alpha=255, fill=True)` | rectangle from its top-left corner; `alpha` 0-255 for see-through; `fill=False` = outline |
| `g.circle(x, y, r, color)` | filled circle from its centre (costs `2*r` draw calls) |
| `g.line(x1, y1, x2, y2, color)` | 1 px line |
| `g.text(s, x, y, color=g.WHITE, size=20, align="left")` | text; `align` = `"left"`, `"center"`, `"right"`; returns width |
| `g.draw(spr, x, y, scale=1, flip=False, angle=0, src=None)` | draw a sprite; `flip` mirrors left-right; `angle` in degrees; `src=(x, y, w, h)` = part of a sheet |

**Sprites** (create once at the top of the file; a sprite has `.w` and `.h`)

```python
HERO = g.sprite([        # pixel art as text: one character = one pixel
    ".rr.",              # "." or " " = transparent
    "rwwr",              # every row must have the same length
    "rrrr",
], {"r": (220, 60, 60), "w": (255, 255, 255)})
g.draw(HERO, x, y, 6)    # scale 6 -> 24 x 18 pixels on screen
PIC = g.image("hero.png")   # or a PNG file from games/<slug>/assets/
```

**Buttons**: `UP DOWN LEFT RIGHT A B X Y L1 R1 L2 R2 START SELECT`
(the left stick also counts as the d-pad)

- `g.down("A")` - True while the button is held (movement, auto-fire).
- `g.pressed("A")` - True only on the frame it goes down (jump, menu, one shot).
- `g.down("RIGHT") - g.down("LEFT")` gives -1, 0 or 1: handy for movement.

**Sound**

- `g.tone(freq, ms=100, freq2=None, volume=0.4, wave="square")` - a beep made in code.
  `freq2` slides the pitch. `wave`: `"square"`, `"sine"`, `"noise"`.
  Jump `g.tone(300, 90, 600)`; coin `g.tone(900, 60, 1300)`; hit `g.tone(200, 150, 60, wave="noise")`.
- `g.sound("boom.wav")` / `g.music("song.ogg")` - files from `assets/` (music loops).

**Helpers**

- `g.hit(a, b)` - True if rectangles `(x, y, w, h)` overlap. Use it for all collisions.
- `g.save({"best": 10})` and `g.load()` (returns `{}` the first time) - keep high scores.
- `g.quit()` - leave the game.

## Network games (several consoles on the same Wi-Fi)

Copy the `netduel` example. The pattern, which works for any game:

- One console is the **host**: it runs all the game rules and sends the whole state to the others.
- The others **join**: each sends only its buttons and draws the state it receives.

```python
net = g.host("my-game")        # on the host (the name must be the same on both sides)
net = g.join("my-game")        # on the others: finds the host on the Wi-Fi by itself

# every frame, on both sides:
for player_id, msg in net.recv():   # messages that arrived; ALWAYS call recv() every frame
    ...
net.send({"x": 10})                 # to everyone; net.send(msg, to=player_id) to one player
net.connected                       # True when somebody is linked
net.is_host                         # True on the host
net.peers                           # a dict keyed by player id: use `for pid in net.peers`, never net.peers[0]
                                    # on the host the joined players have ids 1, 2, 3...; a client sees only the host, id 0
```

- Messages are dicts/lists/numbers/strings. Dict keys become **strings** on the other side:
  use string ids (`"0"`, `"1"`) for players.
- In the menu: `A - host`, `B - join`. Also start directly, without the menu, when the game was
  started for one role: `if g.ROLE: begin(g.ROLE)` (`g.ROLE` is `"host"`, `"join"` or `None`).
  It is `"join"` when the player picked a running match in the ALAV Store lobby; `g.join(name)`
  then connects to that match by itself. Without this line the lobby cannot bring a player in and
  `python tool.py check my-game --net` fails.
- A hosting game is listed in the ALAV Store lobby automatically (folder name, title from
  `game.json`, number of players), also while it is paused. The name must not start with `*`.
  If the game has a player limit, say so: `g.host("my-game", max_players=2)` (you included). The
  lobby then shows the match as full and the kit lets nobody above the limit in.
- A player can leave at any moment: use `.get()` for ids, never assume a player exists.
- Try it on one PC: `python tool.py run my-game --net` opens two windows (click one to control it).

## Common mistakes

| Symptom | Cause and fix |
| --- | --- |
| `UnboundLocalError` in `update` | add `global name1, name2` as the first line of the function |
| Things move too fast or at different speeds | you forgot `* dt` |
| `check`: screen is blank | `draw()` draws nothing, or everything is off screen (x 0-600, y 0-440) |
| `check`: too slow / too many draw calls | draw only visible tiles; use bigger tiles; fewer circles |
| One press does many things | use `g.pressed()`, not `g.down()` |
| `ValueError: sprite rows...` | all rows of a sprite must have the same length |
| Removing from a list while looping | loop over a copy: `for b in bullets[:]:` |

## Facts about the consoles

- Games draw on a 600 x 440 screen; on a console with another screen the picture is scaled to fit,
  with bars at the sides if the shape differs.
- Measured on the reference console, the R36T: CPU RK3326 (4 slow cores), about 30x slower than
  a PC, Python 3.11, EmuELEC, SDL2. Other consoles are similar; write for this one.
- Buttons: d-pad, A (right), B (bottom), X (top), Y (left), L1/R1/L2/R2, START, SELECT, left stick.
- PC keys for testing: arrows, X = A, Z = B, S = X, A = Y, Q/W = L1/R1, Enter = START,
  Backspace = SELECT, Esc = quit.
- A game is installed to `/storage/apps/<slug>`; its log is `/storage/apps/<slug>.log`.

## Trying the game on the real console (developer mode)

Only when the user gives you the console address. The user switches it on in
**ALAV Store -> Settings -> developer mode**; the screen then shows the address.
Set it on the PC as the environment variable `ALAV_HOST`, then use the commands below.
The first command from a new PC waits: the console asks "trust this device?" and the user must
press A in the ALAV Store. Tell the user to do that. After it nothing is asked again.
(Alternative without the question: also set `ALAV_CODE` to the code shown in Settings.)

| Command | What it does |
| --- | --- |
| `python tool.py deploy my-game` | copy the game to the console and start it on its screen |
| `python tool.py deploy my-game --check` | self-test on the console CPU; `avg_ms` must be below 12 |
| `python tool.py deploy my-game --bot` | start it with random button presses (nobody has to hold the console) |
| `python tool.py deploy my-game --shot` | save the console screen to `out/my-game-console.png` - open it and look (the game freezes for a few seconds) |
| `python tool.py deploy my-game --logs` | the game's output: errors and `fps ...` lines |
| `python tool.py deploy --stop` | stop the game, back to the console menu |

Debug loop: `deploy --bot` -> wait 10 seconds -> `--shot` and `--logs` -> fix -> repeat.
If deploy says it cannot reach the console, ask the user to wake it; do not retry more than twice.

## Publishing in the ALAV Store

Only when the user asks to put the game in the store. The user registers as a developer at
https://alav.online/developers, waits until the store administrator approves the account (before
that no key can be created and the store answers 403), creates a key there and sets it on the PC as
the environment variable `ALAV_KEY`. Never ask the user to paste the key into the chat and never write it to a file.

| Command | What it does |
| --- | --- |
| `python tool.py publish my-game` | upload the game as a **draft**: only the developer sees it |
| `python tool.py publish my-game --release` | upload and send for release; if this version is already a draft, send that draft |

- **Every release is reviewed by the store administrator**, the first one and every update. `--release`
  ends with `sent for review`: tell the user the game will appear in the store after approval, not that
  it is published. Until then the previous version stays in the store. Running the command again prints
  `waiting for review` and uploads nothing. If the review rejected the version, the command prints the
  reason: show it to the user, fix the game, run `publish` again (it uploads the new build).

- **Never use `--release` unless the user asked to publish the game for everyone.** "Upload",
  "send to the store", "try it in the store" mean a draft: run the command without `--release`.
- Before it: `check` prints `PASS`, and `games/my-game/icon.png` exists - a real picture of the game,
  PNG, at most 128 x 128 pixels and 64 KiB (the command refuses a bigger one).
- `game.json` fields the store uses: `"title"`, `"version"`, and optional `"description"` (one or two
  sentences), `"genre"` and `"kind"` (`"game"`, the default, or `"app"`). Genres of a game: Шутеры,
  Спорт, Гонки, Файтинги, Платформеры, Аркады, Головоломки, RPG, Стратегии; of an app: ИИ,
  Инструменты, Мультимедиа, Система. Without `"genre"` the store shows «Другое».
- A published version cannot be replaced: raise `"version"` for the next one. A draft can: running
  the command again replaces the draft of the same version.
- If the command prints an error from the store, show it to the user; do not retry more than twice.
