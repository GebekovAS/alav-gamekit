"""Render all eleven states through the real ALAV headless renderer.
Run from kit root after `python tool.py check coop-defense` prepares .sdl:
    python games/coop-defense/design/render.py
ALAV_SDL_DIR can override the existing SDL directory; no installation here.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import struct

DESIGN = Path(__file__).resolve().parent
GAME = DESIGN.parent
ROOT = GAME.parent.parent
spec = importlib.util.spec_from_file_location("alav_tool", ROOT / "tool.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
sdl = Path(os.environ.get("ALAV_SDL_DIR", ROOT / ".sdl")).resolve()
assert sdl.is_dir() and (sdl / "SDL2.dll").is_file(), "Point ALAV_SDL_DIR at existing SDL2 libraries"
# Reuse installed DLLs and keep generated check files within the requested boundary.
tool.SDL_DIR = str(sdl)
tool.WORK = str(DESIGN)
NAMES = ["01-title", "02-play", "03-build", "04-coordination", "05-wave-break", "06-victory", "07-defeat", "08-lobby", "09-branch", "10-tree", "11-attacks"]
# The preserved viewer runs in an isolated folder with the original assets.
VIEW = DESIGN / 'mockup-game'
VIEW.mkdir(exist_ok=True)
shutil.copyfile(DESIGN / 'mockup.py', VIEW / 'main.py')
shutil.copyfile(GAME / 'game.json', VIEW / 'game.json')
shutil.copytree(GAME / 'assets', VIEW / 'assets', dirs_exist_ok=True)
report = io.StringIO()
with contextlib.redirect_stdout(report):
    for index, name in enumerate(NAMES):
        shots, process = tool.headless(str(VIEW), 600, "-screen%d" % index, COOP_SCREEN=str(index), COOP_TIME="0.48", COOP_POSE="1")
        problems, stats = tool.judge(name, process, shots, False)
        assert not problems, problems
        source = Path(shots) / "frame00600.png"
        data = source.read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", data[16:24]) == (600, 440)
        shutil.copyfile(source, DESIGN / (name + ".png"))
        shutil.copyfile(source.with_suffix(".txt"), DESIGN / (name + ".txt"))
        # These are this script's own temporary captures, under DESIGN only.
        capture = Path(shots).resolve()
        assert capture.is_relative_to(DESIGN) and capture.name == "mockup-game-screen%d" % index
        shutil.rmtree(capture)
(DESIGN / "check.log").write_text(report.getvalue(), encoding="utf-8")
print(report.getvalue())

assert VIEW.resolve().is_relative_to(DESIGN)
shutil.rmtree(VIEW)
