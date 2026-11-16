---
name: ship-game
description: Package an ALAV Store game for the console (SD card file, store zip) or send it to the console over Wi-Fi. Use when the user wants to install, try on the console, or publish a game.
---

1. The check must pass first: `python tool.py check <slug>`.
2. Set the version in `games/<slug>/game.json` (`"version": "1.0.1"`; raise it for every release,
   otherwise the console keeps the old copy).
3. `python tool.py pack <slug>` creates:
   - `dist/<Title>.sh` - one file. The user copies it to `ports_scripts` on the SD card and starts
     it from the **Ports** menu; it installs itself to `/storage/apps/<slug>` on first start.
   - `dist/ALAV-<slug>-<version>-linux-arm64.zip` - the format of the ALAV Store (`main.py` in the root).
4. Only if the user gave the console address (developer mode in ALAV Store -> Settings),
   set `ALAV_HOST` (the first time the user confirms this PC on the console with A) and use the `deploy` commands from the section
   "Trying the game on the real console" of `AGENTS.md` (`deploy`, `--check`, `--bot`, `--shot`, `--logs`).
5. Only if the user asked to put the game in the ALAV Store: `games/<slug>/icon.png` must exist (square,
   not a placeholder letter, PNG, at most 128x128 px and 64 KiB), so should `games/<slug>/cover.png`
   (the Ports-list poster: square 512x512 PNG, at most 300 KiB), and the user must have set `ALAV_KEY`
   (a developer key from https://alav.online/developers; never ask for it in the chat). Then
   `python tool.py publish <slug>` uploads a **draft** that only the developer sees.
   `python tool.py publish <slug> --release` sends it for release - **use `--release` only when
   the user asked to publish for everyone**. The developer account must be approved by the store
   administrator first, and every release is reviewed: the command ends with `sent for review`, and the
   game appears in the store only after approval (a rejection reason is printed by the next run). Details: section "Publishing in the ALAV Store" of `AGENTS.md`.
6. Tell the user which files were created and how to install them. Quit a game with SELECT+START.
