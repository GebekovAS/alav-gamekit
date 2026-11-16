# Медный дозор 1.3.0 — late-wave performance

Measured 2026-11-16 on this Windows PC with the real SDL renderer. **The draw-call
budget passes; the requested +10% historical timing bound is NOT met.** Historical
measurements below are retained unchanged. No console performance claim is made.

## Version 1.3.0 workload and results

Run sequentially, for map IDs 0 through 3:
`python -B games/coop-defense/probe_perf.py after 0 20` and the same with `30`.
Each fixture has four actual players, eight final towers with two mastery stars,
60 road enemies from the actual four-player wave plus four jammers (two landed,
two initially airborne), and four workers holding A at four different towers.
The probe asserts four independent active overcharges after the hold threshold,
the 64 combined alive limit and the requested wave throughout 640 frames at 80Hz.
Flight, shooting, landing and subsequent pending releases use the real rules.
Landed drones stay present throughout. The previous fixture had 64 road enemies;
this one reserves four slots for drones rather than exceeding the cap.

Transport, input, persistence and sound use the same explicit substitutions as the
older probe. Rules, main.update/draw, snapshots and SDL are real. Network masks go
through real host input handling. Wire deepcopy is included; JSON encoding, actual
TCP/UDP/Wi-Fi and audio synthesis are excluded from these timings. Texture/font
caches are warmed; screenshot writes are outside measured frames. Times are wall
work times, not FPS. No best-of-repeat timing selection is used in this table.

| Map | Wave | Mean host / join, ms | p95 host / join, ms | Peak calls host / join | Mean host update, ms |
|---|---|---|---|---|---|
| 1 | 20 | 0.3866 / 0.2752 | 0.7032 / 0.5381 | 86 / 86 | 0.1264 |
| 1 | 30 | 0.4209 / 0.2919 | 0.7934 / 0.6002 | 94 / 93 | 0.1494 |
| 2 | 20 | 0.3605 / 0.2536 | 0.6876 / 0.4828 | 86 / 85 | 0.1202 |
| 2 | 30 | 0.3915 / 0.2670 | 0.6333 / 0.4214 | 88 / 88 | 0.1415 |
| 3 | 20 | 0.3688 / 0.2612 | 0.6526 / 0.4739 | 91 / 90 | 0.1208 |
| 3 | 30 | 0.4204 / 0.2840 | 0.8016 / 0.5598 | 88 / 88 | 0.1496 |
| 4 | 20 | 0.3807 / 0.2701 | 0.7002 / 0.5405 | 86 / 85 | 0.1241 |
| 4 | 30 | 0.3863 / 0.2600 | 0.6179 / 0.3311 | 89 / 89 | 0.1391 |

Against each corresponding 1.2.0 map row below (wave 20 reference for both new
waves), the worst mean increase is **19.53% host / 26.05% join**.
p95 and individual maxima also exceed +10%; they are not claimed to pass.
Peak calls are **94 or fewer** on every map and role. Raw per-map/wave JSON files
`perf-1.3-map-*-wave-*.json` include maxima and hashes for the actual game sources,
metadata and new runtime assets. Timing variability does not establish its cause
or excuse the unmet threshold. This remains the outstanding acceptance criterion.

Performance work in 1.3.0: worker number badges and active bolt are baked into one
sprite copy per worker; up to five mastery pips are baked into tower variants;
higher levels use a baked star plus one number draw. Large enemy sprites include
their exact integer-width HP bar and existing status tint in the same copy;
Health values stay exact; every original integer bar width is preserved. One transparent, pulsing
outline per overcharged tower; one crackle copy per jammed tower or flying drone
with shadow. Active attack effects select a brighter atlas without extra copies.
Persistent signals consume part of the existing bounded decorative-effect budget.
No simulation enemy is hidden/merged. Interaction targets are cached only while
map, position, facing and full-wall eligibility are unchanged. Empty status sets
skip redundant per-enemy max() work. Tower base stats and combat cadence are kept.
New preloaded RGBA pixel buffers add 11,994,944 bytes (~11.44 MiB) for the bright
512x3072 atlas, 336x112 signals, 224x136 workers, 576x336 tower variants and
1980x588 enemy/HP variants;
this is a calculated texture payload, excluding SDL bookkeeping and caches.

`python -B games/coop-defense/probe_perf.py after 0 25 --late` renders
`lategame.png` plus mastery-menu/plan shots using real game drawing and assets.
The late capture changes displayed stars to 1-5 and 7 and moves worker four to a
legal service position between pads 3 and 4: boosting 3 while targeting jammed 4
exposes the B prompt. It does not change normal startup. All three captures were
opened: pips, drawn star+7, worker bolts, pulsing outlines, red crackles, attack
brightness, B prompt, next-star cost and team reservation are readable at 600x440.

## Historical results (1.1.1 and 1.2.0)

# Медный дозор 1.1.1 — wave 20 performance

Measured 2026-11-16, Windows PC, Python 3.11, existing SDL2 software/headless
renderer. These are **PC work times, not console times or FPS**. No deploy,
publication or packaging was performed. Only the coop-defense directory was written.

## Reproducible workload and results

`python games/coop-defense/probe_perf.py after`

The baseline was run with the same probe **before editing main.py/rules.py**
(version 1.1.0). `perf-before.json` preserves that measurement; the probe refuses
to overwrite it accidentally. To repeat the baseline one needs the original
1.1.0 source; the original game directory was untracked in Git.

Wave 20, four actual Match players (scaled_wave(20,4)), eight final towers
`(2,3,7,3,7,6,10,11)`, 64 live enemies taken in order from that wave's real pending
release. Initial progress is `60 + (i//8)*16 + (i%8)*2`; the remaining release,
HP, damage, walls, economy and cleanup use the real rules. All towers start ready.
This is a deliberately preloaded crowd stress fixture, **not a claim that an
ordinary full-tree playthrough reaches 64 alive**. It runs 640 frames at dt=1/80
(8 simulated seconds), stays on wave 20, and exercises the actual host/join
update and draw functions. SDL textures/fonts are warmed before measurement.

Only the network transport, buttons and sound are replaced: in-memory snapshots
at the game's normal cadence, three remote neutral input streams each frame,
one measured joiner. JSON encoding, Wi-Fi latency and sound synthesis are excluded.
Rendering uses the actual kit functions, textures and SDL, with no fake draw counter.
Screenshots and disk writes are outside the timed frame. The host-update column
includes rules, input handling, snapshot construction and transport deep-copy to
the measured client; it is an upper bound on pure rules time within this probe.

| PC work, ms/frame | Before mean | After mean | Before p95 | After p95 | Before max | After max |
|---|---:|---:|---:|---:|---:|---:|
| Host update + draw | 1.0456 | 0.3655 | 1.5240 | 0.5092 | 6.4753 | 0.6592 |
| Join update + draw | 0.7589 | 0.2392 | 1.0556 | 0.3006 | 2.9716 | 0.5195 |
| Host update only | 0.3016 | 0.1331 | 0.5982 | 0.2658 | 2.6699 | 0.3547 |

| SDL draw calls | Before peak | After peak | Before mean | After mean |
|---|---:|---:|---:|---:|
| Host | 179 | **92** | 139.5 | 82.9 |
| Join | 177 | **89** | 136.8 | 80.1 |

Raw results: `perf-before.json`, `perf-after.json`. Timing varies with OS scheduling;
the maxima include OS pauses. The table is the final rendered-art measurement,
before adding source-hash metadata to the probe; game sources/art did not change
after that run. Draw-call peaks are deterministic in this fixture.

The supplied real R36T baseline remains: host/join 19/13 ms worst, 185/173 calls,
two players and partial I–II defense. It is **a different workload** and must not
be used as a before/after console comparison with the PC four-player fixture.
The <=100-call target is met in the tested stress fixture. **<12 ms console work,
ideally <=9 ms, and <=4 ms console simulation remain unverified.** No PC multiplier
can prove them. Dispersed small enemies or different tower mixes can have different
call counts; batching preserves locality rather than hiding distant enemies.

## Changes

- Measurement mode: `COOP_DEBUG_WAVE=20`, optional `COOP_DEBUG_CASH=5000`,
  `COOP_DEBUG_TOWERS=full`. Players still ready in the room and preparation using
  A / START. Preparation holds wave 19; its first release is 20. Cash is set when
  the room starts the match. Escapes still disappear, but cannot damage the debug
  core. Unset all three variables for normal play; cash/towers alone do not enable
  the fixture. No extra debug players or immortal core in normal play.
- Same-kind packs for the three small enemy silhouettes: 3/5/8 members, three
  deterministic clumps, plus the original hit/fire/slow tint variants in
  `enemies.png`. Membership persists across frames. New packs require a shared
  road segment and <=36px progress span; existing packs release at corners or
  >56px span. Deaths reduce membership; leftover members draw individually. No
  enemy, health or hit test is merged in simulation. Pack position and tint follow
  the surviving group's center and representative member; individual lateral
  placement/status of packed small enemies is visually approximated.
- Only wounded large enemies have HP bars, one foreground rect per bar. Effects
  cap is 20 above 40 live enemies, otherwise 37 (the previous limit). Lightning
  and ice beams are single sprites; redundant endpoint sparks/frost are removed.
- Each pad has its own 10Hz scan phase, spaced by 12.5ms. Damage, range, cooldown,
  armor, slow, spawn counts, caps, cash and reward tables are unchanged. Scan
  phase changes exact hit timestamps/order (up to 87.5ms initial phase shift);
  bit-identical combat trajectories are not promised by staggered scheduling.
- Reuse progress order with insertion repair and stable spawn-ID ties; no full
  sort of simulation enemies each frame. Reuse proposed positions, wall results
  and XY maps. Compute XY once for live enemies in a scan frame and reuse death
  positions. Cache the wave spawn interval. Expire effects in place.
- Build snapshots only at 10Hz, including on the host (apart from initial room
  snapshot). Host enemies, workers and effects draw from live authoritative state;
  copied HUD/menu values may lag by up to one snapshot interval.

`design/make_perf_art.py` is an offline Pillow tool, using the existing individual
enemy/effect pixels; run it after regenerating base art with make_art.py. Pillow
is already installed in the Codex runtime; the game adds no dependencies.

## What was deliberately retained / unavailable

Read-only inspection of `kit/alav.py`: `text()` already caches textures by
`(string,size,color)` (cache clears above 200 entries). Another text cache would
duplicate it. The three HUD numeric text calls retain their colors and positions;
there is no additional text rasterization for unchanged strings. `draw()` does
one SDL copy per sprite, and `rect()` one SDL call per rectangle. There is no
public render-target/offscreen-sprite API, so tower/wall/pad layers were not cached.
The kit and tool were not changed or accessed through private APIs by game code.

## Verification and evidence

- `python games/coop-defense/test_rules.py`: **10 rule groups PASS**, unchanged tests.
- `python games/coop-defense/test_network.py`: **PASS**, real main.update with an
  explicitly substituted in-memory transport.
- `python games/coop-defense/test_perf.py`: **PASS**, debug room/cash/full-tree
  path, debug immortality and ordinary defeat, incremental order vs stable sort
  through overtakes/spawns/deaths, 10Hz snapshot count, scan phases, pack membership,
  same-kind grouping, death and corner splitting.
- Stock `tool.cmd_check(['coop-defense'])`: **PASS**, including real local TCP
  host/join, store-address join and UDP lobby probe. Final output: host 480 frames,
  0.23 ms/frame, worst 3.4, 66 calls; join 420 frames, 0.19 ms/frame, worst 4.2,
  69 calls; lobby join 420 frames, 0.20 ms/frame, worst 4.2, 69 calls. The stock
  check reports median work as its `avg_ms`, whereas this probe reports means.
  Two sandbox runs had inconsistent socket failures (first UDP discovery, then
  TCP connections); the unchanged check passed outside the sandbox.
- To keep all generated files inside the allowed game directory, the equivalent
  stock check entry point was called without editing tool.py:

  ```powershell
  python -B -c "import tool; tool.WORK=r'F:\Projects\OTHER\r36t-gamekit\games\coop-defense\design'; raise SystemExit(tool.cmd_check(['coop-defense']))"
  ```

- Visually opened before/after wave-20 host screenshots, after join screenshot,
  and final stock-check host/join/lobby screenshots. The crowd still has many
  distinct small bodies and separate large silhouettes; HUD text is on screen.
  `perf-after-host.png` / `perf-after-join.png` show each role's draw-call peak,
  which can occur at different times. Stock-check shots are under
  `design/out/check/coop-defense-{host,join,lobby}/`.
- Metadata version: **1.1.1**. No deploy, publication, container or installation.

## Version 1.2.0 — four maps (2026-11-16)

The same `probe_perf.py after 0` … `after 3` workload, run sequentially.
Each process loads all four backgrounds at startup. Only the fixture map varies.
Network, sound and persistence are substituted by the probe; real rules, update,
draw and SDL remain. Source hashes are in `perf-map-1.json` … `perf-map-4.json`.

| Map | Mean host / join, ms | p95 host / join, ms | Peak calls host / join | Mean host update, ms |
|---|---:|---:|---:|---:|
| 1 | 0.3616 / 0.2463 | 0.5074 / 0.2936 | 90 / 89 | 0.1389 |
| 2 | 0.3776 / 0.2434 | 0.5418 / 0.3078 | 94 / 94 | 0.1465 |
| 3 | 0.3517 / 0.2253 | 0.5108 / 0.2750 | 91 / 90 | 0.1354 |
| 4 | 0.3687 / 0.2370 | 0.5205 / 0.3108 | 95 / 94 | 0.1415 |

Against the original 1.1.1 table above: worst total-frame mean is +3.31% host,
+2.97% join; worst p95 is +6.40% host, +3.39% join; peak calls +3.26% host,
+5.62% join. Thus total-frame means, p95 and draw counts meet the requested +10%.
Host-update mean alone reaches 0.1465 ms (+10.07% against 0.1331 ms), just outside
that bound. Individual maximum timings do NOT meet the +10% bound: raw files
retain them (including one 10.03 ms client OS/runtime pause; cause not established).
No claim is made that every historical timing statistic passes +10%.

Earlier runs ranged around 0.75–0.98 ms host. A repeat of unchanged pre-task Git
sources with the same current assets also measured 0.8191 / 0.5691 ms;
`perf-reference-1.1.1.json` preserves its results and source hashes. The last full
sequential four-map run above returned to the historical timing range. This is
observed timing variability, not proof of its cause; absolute maximums are noisy.

`capture_game.py map-1 map-2 map-3 map-4` uses a DIFFERENT fixture: 62 enemies
spread over the entire route, eight final towers, wave 20. Its pictures are for
visual/geometry review, not the compact-crowd performance comparison above.
Its last stock judge reported 0.448 / 0.453 / 0.445 / 0.436 ms, 113 / 111 / 113 /
111 calls, and warned about exceeding the 0.4 ms PC proxy on all four maps.
Those warnings remain in `runtime-map-1-map-2-map-3-map-4-check.log`.

Four 600×408 RGBA backgrounds plus the 480×82 thumbnail atlas need 4,074,240 bytes
of pixel storage (~3.89 MiB; ~3.74 MiB for backgrounds only). This excludes SDL
bookkeeping. Asset initialization for the second loaded game namespace took
9–10.2 ms on PC. First initialization took 4–8.3 s and includes lazy kit/SDL/audio
startup; it is not an isolated PNG decode measurement. No runtime map loads.
Console startup, memory, CPU timings and real Wi-Fi remain unverified; no deploy.
