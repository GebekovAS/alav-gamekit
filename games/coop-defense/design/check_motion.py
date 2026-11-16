"""Verify live animation through the real ALAV renderer, retaining three captures."""
import importlib.util
import os
from pathlib import Path
import shutil
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('alav_tool',D.parents[2]/'tool.py')
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
tool.SDL_DIR=str(D.parents[2]/'.sdl');tool.WORK=str(D)
view=D/'mockup-motion'
view.mkdir(exist_ok=True)
shutil.copyfile(D/'mockup.py',view/'main.py')
shutil.copyfile(D.parent/'game.json',view/'game.json')
shutil.copytree(D.parent/'assets',view/'assets',dirs_exist_ok=True)
shots,process=tool.headless(str(view),600,'-motion',COOP_SCREEN='10')
problems,stats=tool.judge('11-attacks-live',process,shots,False)
assert not problems,problems
captures=sorted(Path(shots).glob('*.png'))
assert len(captures)==3
assert len({p.read_bytes() for p in captures})==3,'animation must change on screen'
(D/'motion-check.log').write_text(str(stats)+'\nThree distinct live frames: PASS\n',encoding='utf-8')
print('Three distinct live frames: PASS')

assert view.resolve().is_relative_to(D)
shutil.rmtree(view)
