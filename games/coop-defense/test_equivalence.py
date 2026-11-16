"""Exact replay hashes recorded from pre-round-2 rules; no renderer/transport."""
import hashlib
import json
from pathlib import Path
import sys
import rules

GOLDEN=Path(__file__).with_name('design')/'round2-equivalence.json'
FIELDS=('phase','time','timer','wave','bank','core','walls','players','towers',
        'enemies','pending','markers','repairs','effects','event','spawned','serial',
        'spawn_clock','bonus','elapsed','kills','spent','wave_players','banner_until',
        'scan_due','over','jammers','jammer_pending','jammer_clock')


def replay(module,map_id,wave,dt):
    m=module.Match(map_id=map_id)
    for pid in range(4):m.add_player(str(pid))
    m.start();m.wave=wave-1;m.start_wave()
    m.towers=[[k,300,0.,2] for k in (2,3,7,3,7,6,10,11)]
    m.jammer_pending=0
    for pad in (4,5,6,7):
        m.serial+=1;x,y=m.map['pads'][pad]
        m.jammers.append([m.serial*8+6,x if pad<6 else 590.,y if pad<6 else 400.,pad,module.enemy_hp(1,wave),pad<6])
    for i in range(60):
        kind,_=m.pending.pop(0);m.spawn(kind,60+(i//8)*16+(i%8)*2)
    digest=hashlib.sha256()
    for frame in range(1600):
        inputs={}
        for pid,p in m.players.items():
            # Hold, release, move to a jammed pad, remove, buy, sell and rebuild.
            pad=int(pid) if frame<650 else int(pid)+4
            x,y=m.map['pads'][pad]
            p['x'],p['y'],p['target']=x-36,min(387,y),pad
            button=module.A if frame<600 or frame>=900 else module.B if frame>=650 else 0
            inputs[pid]=(button,module.A if frame in (0,900) else 0)
        if frame==1000:
            m.bank['cash']+=10000;m.buy('0',12+module.stars(m.towers[4]))
        if frame==1100:
            p=m.players['0'];p['menu']='plan';p['sel']=4
            m.sell_request('0');m.sell_request('0');p['menu']=''
        if frame==1150:m.buy('0',4)
        if frame==1200:m.remove_player('3')
        if frame==1300:m.add_player('3')
        m.tick(dt,inputs)
        # Exclude only private interaction caches; include unrounded combat state.
        state={k:getattr(m,k) for k in FIELDS}
        state['players']={pid:{k:v for k,v in p.items() if not k.startswith('_')} for pid,p in m.players.items()}
        state['snapshot']=m.snapshot()
        digest.update(json.dumps(state,sort_keys=True,separators=(',',':')).encode())
    return digest.hexdigest()


if __name__=='__main__':
    module=rules
    if '--record-baseline' in sys.argv:
        import subprocess,types
        source=subprocess.check_output(['git','show','062135790aa2dfbbf3b659de0a2097eadb167ec9:games/coop-defense/rules.py'])
        module=types.ModuleType('baseline');exec(compile(source,'baseline_rules.py','exec'),module.__dict__)
    actual={f'{map_id}/{wave}/{dt}':replay(module,map_id,wave,dt)
            for map_id in range(4) for wave in (25,30) for dt in (.0125,.1)}
    if module is not rules:
        GOLDEN.write_text(json.dumps(actual,indent=2)+'\n',encoding='utf-8')
        print('Recorded 16 baseline replays, 25,600 frames')
    else:
        expected=json.loads(GOLDEN.read_text(encoding='utf-8'))
        assert actual==expected,[(k,actual[k],expected[k]) for k in actual if actual[k]!=expected[k]]
        print('PASS exact pre-round-2 combat state and snapshots: 16 replays / 25,600 frames')
        from unittest.mock import patch
        m=rules.Match();m.add_player('0');m.start();m.start_wave();m.pending=[]
        m.towers=[[3,250,10.,0] for _ in range(8)]
        m.towers[0][2]=0.;m.jammers=[[8006,104.,100.,0,100.,True]]
        for i in range(60):m.spawn(i%6,100+i)
        with patch.object(rules,'enemy_xy',wraps=rules.enemy_xy) as xy:
            m.tick(.0125,{})
            assert xy.call_count==0  # Cooldowns and jams must not build scan points.
            m.towers[1][2]=0.;m.scan_due[1]=0.
            m.tick(.0125,{})
            assert 0<xy.call_count<=60
        print('PASS cooled/jammed towers skip coordinate scans; ready tower scans')
