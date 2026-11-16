"""Capture real later states through ALAV; always restore the normal source."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys

DESIGN=Path(__file__).resolve().parent
GAME=DESIGN.parent
ROOT=GAME.parent.parent
spec=importlib.util.spec_from_file_location('alav_tool',ROOT/'tool.py')
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
tool.SDL_DIR=str(ROOT/'.sdl');tool.WORK=str(DESIGN/'runtime-check')
Path(tool.WORK).mkdir(exist_ok=True)
source=GAME/'main.py';normal=source.read_text(encoding='utf-8')
fixtures={
 'title':'',
 'prep':"begin('host',True)\nview=match.snapshot()",
 'lobby':"begin('host')\nmatch.add_player('1')\nmatch.add_player('2')\nmatch.players['1']['ready']=True\nview=match.snapshot()",
 'build':"begin('host',True)\np=match.players['0'];p['x'],p['y']=224,135;p['target']=1;p['menu']='build'\nview=match.snapshot()",
 'branch':"begin('host',True)\nmatch.towers[0]=[1,110,0.]\np=match.players['0'];p['x'],p['y']=104,135;p['target']=0;p['menu']='build'\nview=match.snapshot()",
 'plan':"begin('host',True)\nfrom rules import transaction\nfor i in range(1,4):match.add_player(str(i))\ntransaction(match.bank,'1',4,8,0,True)\nmatch.players['0']['menu']='plan'\nview=match.snapshot()",
 'wave20':"""begin('host',True)
for i in range(1,4):match.add_player(str(i))
match.wave=19;match.start_wave()
for i,index in enumerate([2,3,7,6,5,10,11,9]):match.towers[i]=[index,300,0.]
match.pending=[]
for i in range(58):match.spawn(0,20+i*12)
for k,p in [(1,100),(2,200),(3,300),(3,500),(4,600),(5,320)]:match.spawn(k,p)
view=match.snapshot()""",
 'wall':"begin('host',True)\nmatch.walls[0]=121\np=match.players['0'];p['x'],p['y']=284,174;p['target']=8\nview=match.snapshot()",
 'message':"begin('host',True)\nmatch.say('0','Построено')\nview=match.snapshot()",
 'milestone':"begin('host',True)\nmatch.wave=20;match.phase='break';match.timer=40;match.banner_until=match.time+2\nview=match.snapshot()",
 'defeat':"begin('host',True)\nmatch.phase='defeat';match.wave=7;match.core=0;match.elapsed=524\nview=match.snapshot()",
}
report=io.StringIO()
try:
    for name,fixture in fixtures.items():
        requested=[a for a in sys.argv[1:] if not a.startswith('--')]
        if requested and name not in requested:continue
        # Fixed controls isolate the screen under review; combat still runs normally.
        injected=fixture+"\nmasks=lambda:(0,0)\n"
        if fixture:
            injected+="""
def capture_update(dt):
    global view,clock
    clock+=dt
    net.recv()
    match.tick(dt,{})
    view=match.snapshot()
update=capture_update
"""
        if '--profile' in sys.argv:
            injected+="\nimport cProfile,atexit\nprofile=cProfile.Profile();profile.enable()\natexit.register(profile.dump_stats,'games/coop-defense/design/profile.stats')\n"
        injected+="g.run(update,draw,'Медный дозор')"
        source.write_text(normal.replace("g.run(update,draw,'Медный дозор')",injected),encoding='utf-8')
        with contextlib.redirect_stdout(report):
            shots,process=tool.headless(str(GAME),120 if name=='wave20' else 60,'-'+name)
        with contextlib.redirect_stdout(report):
            problems,stats=tool.judge(name,process,shots,False)
        for file in Path(shots).glob('*'):
            if file.name in (('frame00120.png','frame00120.txt') if name=='wave20' else ('frame00060.png','frame00060.txt')):
                shutil.copyfile(file,DESIGN/('runtime-'+name+file.suffix))
        capture=Path(shots).resolve()
        assert capture.is_relative_to(DESIGN)
        shutil.rmtree(capture)
        print(name,stats,problems)
finally:
    source.write_text(normal,encoding='utf-8')
(DESIGN/('runtime-'+('-'.join(requested) if requested else 'all')+'-check.log')).write_text(report.getvalue(),encoding='utf-8')
print(report.getvalue())
