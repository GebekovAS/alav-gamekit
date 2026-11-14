---
name: network-game
description: Make or fix an ALAV Store multiplayer game played over Wi-Fi between consoles. Use when the user mentions network, online, multiplayer, co-op or versus on two consoles.
---

1. Read the "Network games" section of `AGENTS.md` and all of `examples/netduel/main.py`.
2. Start from it: `python tool.py new <slug> --from netduel --title "<Title>"`.
3. Keep this structure - it is what makes the game work:
   - the host runs the rules (`simulate`) and sends the full state about 30 times per second;
   - a joined player sends only its buttons every frame and replaces its state with what arrives;
   - `net.recv()` is called every frame on both sides;
   - player ids are strings; `if g.ROLE: begin(g.ROLE)` stays in the menu code: it is how the
     ALAV Store lobby ("playing nearby") and the check start the game straight as host or join.
     A hosting game appears in that lobby by itself; `g.join(NAME)` goes to the picked match.
   - a game for a fixed number of players hosts with `g.host(NAME, max_players=N)`: the lobby shows
     "full" and the kit refuses extra players.
4. Put everything a client must draw into the state message (positions, scores, whose turn).
   Keep it small: numbers and short lists, not long texts.
5. Test: `python tool.py check <slug> --net` (starts a host, a join copy and a copy joined the way
   the store lobby does it; all must connect, and the host must answer the lobby).
   By hand: `python tool.py run <slug> --net` opens two windows.
6. Limits to tell the user: both consoles must be on the same Wi-Fi network; one presses
   "host", the others "join" (or pick the match in the ALAV Store lobby). On a PC the firewall may ask to allow Python - allow it.
