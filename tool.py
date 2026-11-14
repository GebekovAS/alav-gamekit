#!/usr/bin/env python3
"""R36T game kit - one tool for everything.

  python tool.py new <slug> [--from <example>] [--title "My Game"]   create games/<slug>
  python tool.py run <slug> [--net]        play in a PC window (--net: two windows, host + join)
  python tool.py check <slug> [--net]      automatic test: prints PASS or FAIL with reasons
  python tool.py pack <slug>               build dist/<slug>-<version>.zip and dist/<Title>.sh
  python tool.py deploy <slug>             send to the console over Wi-Fi and start it
  python tool.py deploy <slug> --check     self-test on the console's CPU (screen not used)
  python tool.py deploy <slug> --bot       start it with random button presses
  python tool.py deploy <slug> --logs      the game's output on the console
  python tool.py deploy <slug> --shot      picture of the console screen -> out/<slug>-console.png
  python tool.py deploy --stop             stop the game

deploy needs developer mode: R36T Store -> Settings on the console, then on the PC set
R36T_HOST to the address shown there. The first time the console asks to trust this PC.
<slug> is a folder name in games/ or examples/. Keys on a PC: arrows, X=A, Z=B, S=X, A=Y,
Q/W=L1/R1, Enter=START, Backspace=SELECT, Esc=quit.
"""
import ast
import base64
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import tokenize
import urllib.error
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.join(ROOT, "kit")
DIST = os.path.join(ROOT, "dist")
CHECK_FRAMES = 1800  # 30 seconds of play
# Measured: the console runs Python ~30x slower than a desktop PC (1M loop steps: 1.65 s vs 0.05 s).
MAX_PC_MS = 0.4      # average update+draw time per frame on the PC
MAX_DRAWS = 400      # draw calls in one frame
SKIP = ("__pycache__", "save.json", "save.json.tmp", "screenshot.png")


def game_dir(slug):
    for base in ("games", "examples"):
        path = os.path.join(ROOT, base, slug)
        if os.path.isfile(os.path.join(path, "main.py")):
            return path
    if os.path.isfile(os.path.join(slug, "main.py")):
        return os.path.abspath(slug)
    sys.exit("no game '%s': expected games/%s/main.py (create it: python tool.py new %s)" % (slug, slug, slug))


def meta(path):
    try:
        with open(os.path.join(path, "game.json"), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit("bad game.json in %s: %s" % (path, e))
    if not str(data.get("title", "")).strip() or not re.fullmatch(r"\d+\.\d+\.\d+", str(data.get("version", ""))):
        sys.exit('game.json needs "title" and "version" like "1.0.0"')
    return data


def play_env(**extra):
    env = dict(os.environ, PYTHONPATH=KIT, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    env.update(extra)
    return env


# ------------------------------------------------------------------ new / run

def cmd_new(args):
    slug = args[0]
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,30}", slug):
        sys.exit("slug must be lowercase letters, digits and '-', e.g. space-miner")
    src = game_dir(args[args.index("--from") + 1]) if "--from" in args else os.path.join(ROOT, "examples", "minimal")
    dst = os.path.join(ROOT, "games", slug)
    if os.path.exists(dst):
        sys.exit(dst + " already exists")
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*SKIP, ".*"))
    title = args[args.index("--title") + 1] if "--title" in args else slug.replace("-", " ").title()
    with open(os.path.join(dst, "game.json"), "w", encoding="utf-8") as f:
        json.dump({"title": title, "version": "1.0.0"}, f, ensure_ascii=False, indent=2)
    print("created games/%s  -> edit games/%s/main.py, then: python tool.py check %s" % (slug, slug, slug))


def cmd_run(args):
    path = game_dir(args[0])
    main = os.path.join(path, "main.py")
    if "--net" not in args:
        return subprocess.call([sys.executable, main], env=play_env())
    procs = [subprocess.Popen([sys.executable, main], env=play_env(R36T_ROLE="host"))]
    time.sleep(1)
    procs.append(subprocess.Popen([sys.executable, main], env=play_env(R36T_ROLE="join")))
    return max(p.wait() for p in procs)


# ------------------------------------------------------------------ check

def static_problems(path):
    """Things that work on the PC but break on the console (Python 3.11, no pip packages)."""
    problems = []
    local = {os.path.splitext(f)[0] for f in os.listdir(path)} | {"r36t"}
    for name in sorted(os.listdir(path)):
        if not name.endswith(".py"):
            continue
        file = os.path.join(path, name)
        with open(file, encoding="utf-8") as f:
            src = f.read()
        try:
            tree = ast.parse(src, name, feature_version=(3, 11))
            compile(src, name, "exec")
        except (SyntaxError, ValueError) as e:
            problems.append("%s: syntax error (the console has Python 3.11): %s" % (name, e))
            continue
        for node in ast.walk(tree):
            mods = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module or ""] if isinstance(node, ast.ImportFrom) and not node.level else []
            for mod in mods:
                top = mod.split(".")[0]
                if top not in sys.stdlib_module_names and top not in local:
                    problems.append("%s:%d: import %s - not available on the console; use only the "
                                    "standard library and r36t" % (name, node.lineno, top))
        if sys.version_info >= (3, 12):  # f"{d["k"]}" is valid from 3.12 only
            open_quotes = []
            for tok in tokenize.generate_tokens(io.StringIO(src).readline):
                kind = tokenize.tok_name[tok.type]
                quote = tok.string.lstrip("rRbBfFuU")[:1]
                if kind in ("STRING", "FSTRING_START") and quote in open_quotes:
                    problems.append("%s:%d: the same quote character inside an f-string breaks on "
                                    "Python 3.11; use the other quote inside" % (name, tok.start[0]))
                if kind == "FSTRING_START":
                    open_quotes.append(quote)
                elif kind == "FSTRING_END":
                    open_quotes.pop()
    return problems


def headless(path, frames, **extra):
    shots = os.path.join(ROOT, "out", "check", os.path.basename(path) + ("-" + extra["R36T_ROLE"] if "R36T_ROLE" in extra else ""))
    shutil.rmtree(shots, ignore_errors=True)
    os.makedirs(shots)
    return shots, subprocess.Popen([sys.executable, os.path.join(path, "main.py")], stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                                   env=play_env(R36T_CHECK=str(frames), R36T_SHOTS=shots, **extra))


def judge(name, proc, shots, net):
    problems = []
    try:
        out = proc.communicate(timeout=180)[0]
    except subprocess.TimeoutExpired:
        proc.kill()
        return ["%s: did not finish in 180 s - an endless loop inside update() or draw()?" % name], None
    found = re.search(r"^R36T_CHECK (\{.*\})$", out, re.M)
    stats = json.loads(found.group(1)) if found else None
    if proc.returncode != 0 or not stats:
        tail = "\n".join(out.strip().splitlines()[-25:])
        return ["%s: the game crashed (exit code %s):\n%s" % (name, proc.returncode, tail)], None
    if stats["avg_ms"] > MAX_PC_MS and not net:
        problems.append("%s: too slow for the console: %.2f ms per frame here (limit %.1f). Do less work "
                        "per frame: fewer objects, no nested loops over all objects" % (name, stats["avg_ms"], MAX_PC_MS))
    if stats["draws"] > MAX_DRAWS:
        problems.append("%s: %d draw calls in one frame (limit %d). Draw only what is on screen; "
                        "use bigger tiles or fewer circles" % (name, stats["draws"], MAX_DRAWS))
    if stats["colors"] < 3:
        problems.append("%s: the screen is blank (one flat colour) - draw() shows nothing" % name)
    if net and not stats["net_peers"]:
        problems.append("%s: host and join never connected. Use g.ROLE to pick host/join without a menu "
                        "(see AGENTS.md, Network games)" % name)
    print("  %s: %d frames, %.2f ms/frame (worst %.1f), %d draw calls, screenshots: %s" % (
        name, stats["frames"], stats["avg_ms"], stats["max_ms"], stats["draws"], os.path.relpath(shots, ROOT)))
    return problems, stats


def cmd_check(args):
    path = game_dir(args[0])
    meta(path)
    problems = static_problems(path)
    if not problems:
        if "--net" in args:
            runs = [("host", *headless(path, 480, R36T_ROLE="host", R36T_PACE="1"))]
            time.sleep(1)
            runs.append(("join", *headless(path, 420, R36T_ROLE="join", R36T_PACE="1")))
        else:
            runs = [("game", *headless(path, CHECK_FRAMES))]
        for name, shots, proc in runs:
            problems += judge(name, proc, shots, "--net" in args)[0]
    if not os.path.isfile(os.path.join(path, "icon.png")):
        print("  note: no icon.png yet (needed only for publishing in the R36T Store)")
    if problems:
        print("FAIL")
        for p in problems:
            print(" - " + p)
        return 1
    print("PASS - now open the screenshots above and make sure the game looks right")
    return 0


# ------------------------------------------------------------------ pack / deploy

def stage(slug):
    """dist/<slug>/: the game plus the kit, exactly what ends up in /storage/apps/<slug>."""
    path = game_dir(slug)
    info = meta(path)
    out = os.path.join(DIST, os.path.basename(path))
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(path, out, ignore=shutil.ignore_patterns(*SKIP, ".*", "*.pyc", "test_*"))
    for name in ("r36t.py", "font.ttf"):
        shutil.copy(os.path.join(KIT, name), out)
    with open(os.path.join(out, "version.txt"), "w", newline="\n") as f:
        f.write(info["version"] + "\n")
    return out, info


def tar_bytes(folder):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(folder, arcname=".")
    return buf.getvalue()


INSTALLER = r"""#!/bin/bash
# %(title)s %(version)s - a game for the R36T, made with r36t-gamekit.
# Copy this single file to the ports_scripts folder of the SD card, then start it from Ports.
APP=/storage/apps/%(slug)s
if [ "$(cat "$APP/version.txt" 2>/dev/null)" != "%(version)s" ]; then
  rm -rf "$APP.new"
  python3 - "$0" "$APP.new" <<'PY' || exit 1
import base64, io, sys, tarfile
payload = open(sys.argv[1], "rb").read().rsplit(b"\n__PAYLOAD__\n", 1)[1]
tarfile.open(fileobj=io.BytesIO(base64.b64decode(payload))).extractall(sys.argv[2])
PY
  [ -f "$APP/save.json" ] && cp "$APP/save.json" "$APP.new/"
  rm -rf "$APP" && mv "$APP.new" "$APP"
fi
cd "$APP" || exit 1
python3 -u main.py > "$APP.log" 2>&1
exit $?
__PAYLOAD__
"""


def cmd_pack(args):
    folder, info = stage(args[0])
    slug = os.path.basename(folder)
    zip_path = os.path.join(DIST, "%s-%s.zip" % (slug, info["version"]))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:  # main.py in the root: R36T Store format
        for base, _, files in os.walk(folder):
            for name in sorted(files):
                full = os.path.join(base, name)
                z.write(full, os.path.relpath(full, folder).replace(os.sep, "/"))
    sh_path = os.path.join(DIST, re.sub(r'[\\/:*?"<>|]', "", info["title"]).strip() + ".sh")
    head = INSTALLER % {"title": info["title"], "version": info["version"], "slug": slug}
    with open(sh_path, "wb") as f:
        f.write(head.encode() + base64.b64encode(tar_bytes(folder)) + b"\n")
    print("%s\n%s\n  -> copy the .sh to ports_scripts on the SD card and start it from Ports" % (zip_path, sh_path))


def console(method, path, data=None):
    """One request to the console's developer mode (R36T Store -> Settings)."""
    host = os.environ.get("R36T_HOST")
    if not host:
        sys.exit("deploy needs developer mode on the console: R36T Store -> Settings -> switch it on, then set "
                 "R36T_HOST=<address shown there>. Without it use: python tool.py pack <slug>")
    id_file = os.path.expanduser("~/.r36t-gamekit-device")  # this PC's id; the console remembers it once trusted
    if not os.path.isfile(id_file):
        with open(id_file, "w") as f:
            f.write(os.urandom(16).hex())
    with open(id_file) as f:
        headers = {"X-R36T-Device": f.read().strip(), "X-R36T-Name": re.sub(r"[^A-Za-z0-9 .-]", "", socket.gethostname())}
    if os.environ.get("R36T_CODE"):  # optional: the code from Settings skips the question on the console
        headers["X-R36T-Code"] = os.environ["R36T_CODE"]
    url = "http://%s%s" % (host if ":" in host else host + ":3636", path)
    for attempt in range(40):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, method=method, headers=headers),
                                        timeout=240) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            if e.code != 401:
                sys.exit("console refused: " + e.read().decode("utf-8", "replace"))
            if attempt == 0:
                print("First time from this PC (id %s): open R36T Store on the console and press A to trust "
                      "it (waiting up to 2 minutes)..." % headers["X-R36T-Device"][:4], flush=True)
            time.sleep(2)
        except OSError as e:
            sys.exit("cannot reach the console at %s (is it on, on the same Wi-Fi, developer mode on?): %s" % (host, e))
    sys.exit("nobody confirmed this PC on the console. Ask the user to open R36T Store and press A, then retry")


def cmd_deploy(args):
    if args[0] == "--stop":
        console("POST", "/stop")
        return 0
    flag = args[0] if args[0].startswith("--") else next((a for a in args[1:] if a.startswith("--")), "")
    slug = os.path.basename(game_dir(next(a for a in args if not a.startswith("--"))))
    app = "/apps/" + slug
    if flag == "--logs":
        print(console("GET", app + "/log").decode("utf-8", "replace"))
    elif flag == "--shot":
        os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
        path = os.path.join(ROOT, "out", slug + "-console.png")
        picture = console("GET", app + "/screenshot")
        with open(path, "wb") as f:
            f.write(picture)
        print("screenshot of the console screen: " + os.path.relpath(path, ROOT))
    else:
        folder, _ = stage(slug)
        console("PUT", app, tar_bytes(folder))
        if flag == "--check":  # headless self-test on the real CPU; the screen is not touched
            print(console("POST", app + "/check").decode("utf-8", "replace"))
        else:
            console("POST", app + "/run" + ("?bot=1" if flag == "--bot" else ""))
            print("started on the console. Quit: SELECT+START. Log: python tool.py deploy %s --logs" % slug)
    return 0


if __name__ == "__main__":
    commands = {"new": cmd_new, "run": cmd_run, "check": cmd_check, "pack": cmd_pack, "deploy": cmd_deploy}
    if len(sys.argv) < 3 and sys.argv[1:] != ["deploy", "--stop"] or sys.argv[1] not in commands:
        sys.exit(__doc__)
    sys.exit(commands[sys.argv[1]](sys.argv[2:]))
