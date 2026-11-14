---
name: new-game
description: Create a new R36T game from an idea. Use when the user asks to make, build or start a game for the R36T console.
---

1. Read `AGENTS.md` in the repository root (rules and the whole API). Do not skip this.
2. Pick the closest example: `minimal`, `platformer`, `fighter`, `tanks`, `puzzle`, `netduel`.
   Read its `examples/<name>/main.py` fully before writing code.
3. `python tool.py new <slug> --from <example> --title "<Title>"`
   (`<slug>`: lowercase letters, digits, `-`).
4. Edit only `games/<slug>/main.py`. Change the example step by step into the requested game:
   first the rules in `update(dt)`, then the pictures in `draw()`, then the title screen text.
   Keep the `state` variable pattern (title -> play -> over) and keep `g.run(...)` as the last line.
5. Make an original game: own name, own characters, own levels.
6. Continue with the `check-game` skill. The game is not done until the check prints `PASS`.
