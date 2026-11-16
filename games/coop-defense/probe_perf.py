"""PC SDL benchmark: python games/coop-defense/probe_perf.py after MAP_ID WAVE.

Real update/draw/rules/SDL, deterministic in-memory network (no Wi-Fi/JSON cost).
60 road enemies plus four jammers, four real overcharge holds, eight final towers
with mastery. Runs 8 seconds at 80Hz, including snapshots. --late with wave 25
also captures the late-game scene and real mastery menus, without editing main.py.
--tag NAME preserves historical artifacts; --profile profiles only host update
(its instrumented timings must not be compared with ordinary benchmark times).
"""
import ast
import copy
import cProfile
import hashlib
import importlib.util
import json
import os
import pstats
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
g.load=lambda:{};g.save=lambda data:None

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
    map_id=int(sys.argv[2]) if len(sys.argv)>2 else None
    wave=int(sys.argv[3]) if len(sys.argv)>3 else 20
    suffix='1.3-map-%d-wave-%d'%(1 if map_id is None else map_id+1,wave)
    if '--tag' in sys.argv:suffix+='-'+sys.argv[sys.argv.index('--tag')+1]
    profile=cProfile.Profile() if '--profile' in sys.argv else None
    destination=GAME/'design'/('perf-%s.json'%suffix)
    if label=='before' and destination.exists():
        raise SystemExit('Baseline already captured before optimization; keep it. Use after for current code.')
    for key in ('COOP_DEBUG_WAVE','COOP_DEBUG_CASH','COOP_DEBUG_TOWERS'):os.environ.pop(key,None)
    begin_load=time.perf_counter();host=load();host_load_ms=1000*(time.perf_counter()-begin_load)
    begin_load=time.perf_counter();client=load();client_load_ms=1000*(time.perf_counter()-begin_load)
    m=host['Match'](g.hit,map_id or 0)
    for pid in range(4):m.add_player(str(pid))
    m.start();m.wave=wave-1;m.start_wave()
    build=(2,3,7,3,7,6,10,11)
    m.towers=[[k,300,0.,2] for k in build]
    m.jammer_pending=0
    for pad in (4,5,6,7):
        m.serial+=1;x,y=m.map['pads'][pad]
        m.jammers.append([m.serial*8+6,x if pad<6 else 590.,y if pad<6 else 400.,pad,host['enemy_hp'](1,wave),pad<6])
    for pid in range(4):
        p=m.players[str(pid)];x,y=m.map['pads'][pid]
        p['x'],p['y'],p['target']=x-36,min(387,y),pid
    for i in range(60):
        kind,_=m.pending.pop(0);m.spawn(kind,60+(i//8)*16+(i%8)*2)
    host.update(net=Wire(True),match=m,view=m.snapshot(),known=set(m.players))
    client.update(net=Wire(False),view=copy.deepcopy(host['view']),my_id='1')
    if map_id is not None:
        host['draw']();g._screenshot(str(GAME/'design'/('perf-%s-start.png'%suffix)))
    times={'host':[],'join':[],'simulation':[]};calls={'host':[],'join':[]};peaks={}
    # Warm texture/font caches without advancing the fixture.
    host['draw']();client['draw']()
    for frame in range(640):
        g.down=lambda key:key=='A'
        g.pressed=lambda key:key=='A' and frame==0
        host['net'].inbox=[(pid,[frame,16,16 if frame==0 else 0]) for pid in (1,2,3)]
        for role,ns in [('host',host),('join',client)]:
            if profile and role=='host':profile.enable()
            start=time.perf_counter_ns();ns['update'](.0125)
            mid=time.perf_counter_ns()
            if profile and role=='host':profile.disable()
            g._draws=0;g._said.clear();ns['draw']()
            end=time.perf_counter_ns()
            times[role].append((end-start)/1e6);calls[role].append(g._draws)
            if role=='host':times['simulation'].append((mid-start)/1e6)
            if g._draws>peaks.get(role,0):
                peaks[role]=g._draws;g._screenshot(str(GAME/'design'/('perf-%s-%s.png'%(suffix,role))))
        assert m.wave==wave and m.phase=='wave'
        assert len(m.enemies)+len(m.jammers)<=64
        if frame>25:assert len(m.over)==4
    result={role:dict(stats(times[role]),max_draw_calls=max(calls[role]),mean_draw_calls=round(statistics.mean(calls[role]),1)) for role in calls}
    result['host_update']=stats(times['simulation'])
    result['profiled']=profile is not None
    if profile:
        profile.dump_stats(str(GAME/'design'/('profile-%s.pstats'%suffix)))
        with (GAME/'design'/('profile-%s.txt'%suffix)).open('w',encoding='utf-8') as output:
            pstats.Stats(profile,stream=output).strip_dirs().sort_stats('cumulative').print_stats(15)
    result['map']=m.map_id
    result['asset_init_ms']={'host':round(host_load_ms,2),'join':round(client_load_ms,2)}
    result['map_texture_rgba_bytes']=4*600*408*4+480*82*4
    result['fixture']='wave%d/4p/60 ground + 4 jammers/8 final towers with 2 stars/4 overcharging/640 frames at 80Hz'%wave
    result['source_sha256']={name:hashlib.sha256((GAME/name).read_bytes()).hexdigest() for name in ('main.py','rules.py','maps.py','game.json','assets/enemies.png','assets/lategame.png','assets/mastery-towers.png','assets/workers.png','assets/effects-bright.png','assets/enemy-health.png')}
    destination.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    if '--late' in sys.argv:
        assert wave==25
        for i,t in enumerate(m.towers):
            t[3]=7 if i==7 else i%5+1
            base=sum(host['TOWER_DATA'][k][0] for k in (t[0]//4*4,t[0]//4*4+1,t[0]))
            t[1]=base+sum(host['star_price'](t[0],s) for s in range(t[3]))
        # Worker four fits between pads 3 and 4: boosts 3, can see B on jammed 4.
        p=m.players['3'];p['x'],p['y'],p['target']=350,223,4
        host.update(my_id='3',view=m.snapshot())
        host['draw']();g._screenshot(str(GAME/'design/lategame.png'))
        p=m.players['0'];p['menu']='build';p['target']=0
        host.update(my_id='0',view=m.snapshot())
        host['draw']();g._screenshot(str(GAME/'design/mastery-menu.png'))
        p['menu']='';m.bank['cash']=10000;m.buy('0',12+m.towers[0][3],True)
        p['menu']='plan';host.update(view=m.snapshot())
        host['draw']();g._screenshot(str(GAME/'design/mastery-plan.png'))
