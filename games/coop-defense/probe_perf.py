"""PC SDL work benchmark; run from kit root: python games/coop-defense/probe_perf.py before|after.

Real update/draw/rules/SDL, deterministic in-memory network (no Wi-Fi/JSON cost).
64 live enemies preloaded from the actual wave-20 four-player release, clustered
on the first straight. This deliberately stresses a full tree without waiting for
the towers to kill the release. Then run 8 seconds at 80Hz, including snapshots.
"""
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import time

GAME=Path(__file__).resolve().parent
ROOT=GAME.parent.parent
sys.dont_write_bytecode=True  # The read-only kit must not receive import caches.
os.environ['ALAV_CHECK']='1'
os.environ.setdefault('ALAV_SDL_DIR',str(ROOT/'.sdl'))
os.environ.pop('ALAV_ROLE',None)
for name,path in [('alav',ROOT/'kit/alav.py')]:
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
g=module;g.GAME_DIR=str(GAME)
g.down=lambda key:False;g.pressed=lambda key:False;g.tone=lambda *a,**kw:None

class Wire:
    def __init__(self,host):self.is_host=host;self.peers={1:{},2:{},3:{}} if host else {};self.inbox=[]
    def recv(self):
        result=self.inbox;self.inbox=[];return result
    def send(self,msg,to=None):
        if to==1:client['net'].inbox.append((0,copy.deepcopy(msg)))

def load():
    tree=ast.parse((GAME/'main.py').read_text(encoding='utf-8'))
    tree.body.pop()  # g.run only; initialize all real game assets/functions.
    ns={};exec(compile(tree,'main.py','exec'),ns);return ns

def stats(values):
    values=sorted(values)
    return {'mean_ms':round(statistics.mean(values),4),'p95_ms':round(values[int(len(values)*.95)],4),'max_ms':round(max(values),4)}

if __name__=='__main__':
    label=sys.argv[1] if len(sys.argv)>1 else 'after'
    assert label in ('before','after')
    destination=GAME/'design'/('perf-%s.json'%label)
    if label=='before' and destination.exists():
        raise SystemExit('Baseline already captured before optimization; keep it. Use after for current code.')
    for key in ('COOP_DEBUG_WAVE','COOP_DEBUG_CASH','COOP_DEBUG_TOWERS'):os.environ.pop(key,None)
    host=load();client=load()
    m=host['Match'](g.hit)
    for pid in range(4):m.add_player(str(pid))
    m.start();m.wave=19;m.start_wave()
    build=(2,3,7,3,7,6,10,11)
    m.towers=[[k,0,0.] for k in build]
    for i in range(64):
        kind,_=m.pending.pop(0);m.spawn(kind,60+(i//8)*16+(i%8)*2)
    host.update(net=Wire(True),match=m,view=m.snapshot(),known=set(m.players))
    client.update(net=Wire(False),view=copy.deepcopy(host['view']),my_id='1')
    times={'host':[],'join':[],'simulation':[]};calls={'host':[],'join':[]};peaks={}
    # Warm texture/font caches without advancing the fixture.
    host['draw']();client['draw']()
    for frame in range(640):
        host['net'].inbox=[(pid,[frame,0,0]) for pid in (1,2,3)]
        for role,ns in [('host',host),('join',client)]:
            start=time.perf_counter_ns();ns['update'](.0125)
            mid=time.perf_counter_ns();g._draws=0;g._said.clear();ns['draw']()
            end=time.perf_counter_ns()
            times[role].append((end-start)/1e6);calls[role].append(g._draws)
            if role=='host':times['simulation'].append((mid-start)/1e6)
            if g._draws>peaks.get(role,0):
                peaks[role]=g._draws;g._screenshot(str(GAME/'design'/('perf-%s-%s.png'%(label,role))))
        assert m.wave==20 and m.phase=='wave'
    result={role:dict(stats(times[role]),max_draw_calls=max(calls[role]),mean_draw_calls=round(statistics.mean(calls[role]),1)) for role in calls}
    result['host_update']=stats(times['simulation'])
    result['fixture']='wave20/4p/64 preload/8 final towers/640 frames at 80Hz'
    result['source_sha256']={name:hashlib.sha256((GAME/name).read_bytes()).hexdigest() for name in ('main.py','rules.py','assets/enemies.png')}
    destination.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
