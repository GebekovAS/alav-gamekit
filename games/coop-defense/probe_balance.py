"""Deterministic full-match balance probe. No renderer and no external services.
A scripted strategy buys using the same authoritative menus and economy. It moves
workers instantly between service positions, so this is not a human playthrough.
"""
from rules import *
import time


def probe(n,map_id=0):
    m=Match(map_id=map_id)
    for pid in range(n):m.add_player(str(pid))
    m.start()
    # Build the lane first, then add armor counters and complementary control.
    orders=[(0,0),(2,0),(5,4),(6,8),(4,4),(3,0),(1,0),(7,8),
            (2,1),(2,3),(0,1),(0,2),(5,5),(5,6),(6,9),(6,10),
            (4,5),(4,7),(3,1),(3,3),(7,9),(7,11),(1,1),(1,2)]
    order=0;maximum=0;wave_times=[];last=m.phase;begin=0;stamp=time.perf_counter();steps=0
    while m.phase!='defeat' and m.elapsed<7200:
        if order<len(orders):
            pad,index=orders[order]
            if free_cash(m.bank)>=TOWERS[index][0]:
                p=m.players['0'];p['x'],p['y']=m.map['pads'][pad][0]-36,m.map['pads'][pad][1];p['target']=pad
                m.buy('0',index)
                if m.towers[pad] and m.towers[pad][0]==index:order+=1
        # Ready the untimed first preparation; later breaks expire without early bonuses.
        inputs=service(m,n,True) if order==len(orders) else {}
        m.tick(.1,{str(i):(0,START) for i in range(n)} if m.phase=='prep' else inputs)
        steps+=1;maximum=max(maximum,len(m.enemies)+len(m.jammers))
        if last!=m.phase:
            if m.phase=='wave':begin=m.elapsed
            elif last=='wave':wave_times.append(round(m.elapsed-begin,1))
            last=m.phase
    elapsed=time.perf_counter()-stamp
    print('%dp: %s wave=%d, %.1fs, core=%d cash=%d purchases=%d max_alive=%d sim=%.3f ms/tick; wave times=%s'%
          (n,m.phase,m.wave,m.elapsed,m.core,m.bank['cash'],order,maximum,1000*elapsed/steps,wave_times))
    assert maximum<=64
    return m.phase

def service(m,n,active):
    """Instant worker travel is an optimistic bound; holds use real action timers."""
    p=m.players['0'];saved=(p['x'],p['y'],p['target'])
    while True:
        options=[(star_price(t[0],stars(t)),pad) for pad,t in enumerate(m.towers) if t and t[0]%4>=2]
        affordable=[(cost,pad) for cost,pad in options if cost<=free_cash(m.bank)]
        if not affordable:break
        cost,pad=min(affordable)
        p['x'],p['y']=m.map['pads'][pad][0]-36,min(387,m.map['pads'][pad][1]);p['target']=pad
        m.buy('0',12+stars(m.towers[pad]))
    p['x'],p['y'],p['target']=saved
    if not active:return {}
    jobs=[(j[3],B) for j in m.jammers if j[5]]
    # Boost the high-impact damage towers first; one independent tower per worker.
    ranking=sorted((i for i,t in enumerate(m.towers) if t),
                   key=lambda i:tower_damage(m.towers[i]) / TOWERS[m.towers[i][0]][2] * (4 if m.towers[i][0] in (6,7) else 1),reverse=True)
    used={pad for pad,_ in jobs}
    jobs.extend((pad,A) for pad in ranking if pad not in used)
    inputs={}
    for pid,(pad,button) in zip(sorted(m.players,key=int),jobs):
        p=m.players[pid];p['menu']=''
        p['x'],p['y']=m.map['pads'][pad][0]-36,min(387,m.map['pads'][pad][1]);p['target']=pad
        inputs[pid]=(button,A if button==A and p['a_pad']!=pad else 0)
    return inputs


def maxed(n,build,map_id=0,active=True):
    """Upper-bound fixture: all eight final towers before wave 1, no free repair.

    Uses actual combat, walls, core and spawn limits; no worker teleport repairs.
    Starting fully built deliberately removes the economy bottleneck. Both modes
    buy mastery with real spare cash; only active workers boost/remove jammers.
    """
    m=Match(map_id=map_id)
    for pid in range(n):m.add_player(str(pid))
    m.start()
    m.towers=[[index,sum(TOWERS[k][0] for k in (index//4*4,index//4*4+1,index)),0.] for index in build]
    maximum=0
    while m.phase!='defeat' and m.wave<61:
        if m.phase in ('prep','break'):m.start_wave()
        inputs=service(m,n,active)
        m.tick(.1,inputs)
        maximum=max(maximum,len(m.enemies)+len(m.jammers))
    assert maximum<=64 and m.phase=='defeat'
    return m.wave


if __name__=='__main__':
    import sys
    map_id=int(sys.argv[1]) if len(sys.argv)>1 else 0
    print(MAPS[map_id]['name'],MAPS[map_id]['length'])
    if '--economy' in sys.argv:
        for n in (1,2,3,4):probe(n,map_id)
    # Plausible mixes: AoE at the bend, ice control, armor-piercing and core cover.
    builds=[(2,3,7,3,7,7,10,11),(3,3,7,7,10,7,7,11),
            (7,3,7,7,10,7,10,11),(7,3,7,7,11,7,10,11)]
    for n in (1,2,3,4):
        for active in (True,False):
            results=[maxed(n,build,map_id,active) for build in builds]
            best=max(range(len(results)),key=results.__getitem__)
            print('MAXED %dp %s: defeat wave=%d build=%s candidates=%s'%(n,'ACTIVE' if active else 'PASSIVE',results[best],builds[best],results),flush=True)
