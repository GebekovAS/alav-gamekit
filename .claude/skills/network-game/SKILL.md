---
name: network-game
description: Make or fix an R36T multiplayer game played over Wi-Fi between consoles. Use when the user mentions network, online, multiplayer, co-op or versus on two consoles.
---

1. Read the "Network games" section of `AGENTS.md` and all of `examples/netduel/main.py`.
2. Start from it: `python tool.py new <slug> --from netduel --title "<Title>"`.
3. Keep this structure - it is what makes the game work:
   - the host runs the rules (`simulate`) and sends the full state about 30 times per second;
   - a joined player sends only its buttons every frame and replaces its state with what arrives;
   - `net.recv()` is called every frame on both sides;
   - player ids are strings; `if g.ROLE: begin(g.ROLE)` stays in the menu code.
4. Put everything a client must draw into the state message (positions, scores, whose turn).
   Keep it small: numbers and short lists, not long texts.
5. Test: `python tool.py check <slug> --net` (starts a host and a join copy; both must connect).
   By hand: `python tool.py run <slug> --net` opens two windows.
6. Limits to tell the user: both consoles must be on the same Wi-Fi network; one presses
   "host", the others "join". On a PC the firewall may ask to allow Python - allow it.
