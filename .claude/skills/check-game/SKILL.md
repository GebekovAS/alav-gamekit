---
name: check-game
description: Test an R36T game automatically and fix what fails. Use after every change to a game and before saying it works.
---

1. Run `python tool.py check <slug>` (network games: add `--net`).
   It plays the game for 30 seconds with random buttons, without a window.
2. If it prints `FAIL`: every line under it is one problem with the fix. Fix `games/<slug>/main.py`
   and run the check again. A Python traceback names the file and line to fix.
3. If it prints `PASS`: open the PNG screenshots in `out/check/<slug>/` and look at them. If you cannot
   view images, read the `.txt` file next to each PNG (the same screen as text).
   Check: the title screen says which button starts the game; nothing is cut off at the
   edges (screen is 600 x 440); the player and enemies are visible.
4. Common fixes are in the "Common mistakes" table of `AGENTS.md`.
5. To play by hand on the PC: `python tool.py run <slug>` (arrows, X = A, Z = B, Enter = START, Esc = quit).
6. Report to the user: the check result, and what you saw on the screenshots.
