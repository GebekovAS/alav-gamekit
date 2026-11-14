---
name: ship-game
description: Package an R36T game for the console (SD card file, store zip) or send it to the console over Wi-Fi. Use when the user wants to install, try on the console, or publish a game.
---

1. The check must pass first: `python tool.py check <slug>`.
2. Set the version in `games/<slug>/game.json` (`"version": "1.0.1"`; raise it for every release,
   otherwise the console keeps the old copy).
3. `python tool.py pack <slug>` creates:
   - `dist/<Title>.sh` - one file. The user copies it to `ports_scripts` on the SD card and starts
     it from the **Ports** menu; it installs itself to `/storage/apps/<slug>` on first start.
   - `dist/<slug>-<version>.zip` - the format of the R36T Store (`main.py` in the root).
4. Only if the user gave the console address (developer mode in R36T Store -> Settings),
   set `R36T_HOST` (the first time the user confirms this PC on the console with A) and use the `deploy` commands from the section
   "Trying the game on the real console" of `AGENTS.md` (`deploy`, `--check`, `--bot`, `--shot`, `--logs`).
5. For the store an `icon.png` (square, not a placeholder letter) is needed in `games/<slug>/`.
6. Tell the user which files were created and how to install them. Quit a game with SELECT+START.
