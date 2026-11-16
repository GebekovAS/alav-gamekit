"""Deterministic full-match balance probe. No renderer and no external services.
A scripted strategy buys using the same authoritative menus and economy. It moves
workers instantly between service positions, so this is not a human playthrough.
"""
from rules import *
import time


def probe(n):
    m=Match()
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
                p=m.players['0'];p['x'],p['y']=PADS[pad][0]-36,PADS[pad][1];p['target']=pad
                m.buy('0',index)
                if m.towers[pad] and m.towers[pad][0]==index:order+=1
        # Ready the untimed first preparation; later breaks expire without early bonuses.
        m.tick(.1,{str(i):(0,START) for i in range(n)} if m.phase=='prep' else {})
        steps+=1;maximum=max(maximum,len(m.enemies))
        if last!=m.phase:
            if m.phase=='wave':begin=m.elapsed
            elif last=='wave':wave_times.append(round(m.elapsed-begin,1))
            last=m.phase
    elapsed=time.perf_counter()-stamp
    print('%dp: %s wave=%d, %.1fs, core=%d cash=%d purchases=%d max_alive=%d sim=%.3f ms/tick; wave times=%s'%
          (n,m.phase,m.wave,m.elapsed,m.core,m.bank['cash'],order,maximum,1000*elapsed/steps,wave_times))
    assert maximum<=64
    return m.phase

def maxed(n,build):
    """Upper-bound fixture: all eight final towers before wave 1, no free repair.

    Uses actual combat, walls, core and spawn limits; no worker teleport repairs.
    Starting fully built deliberately removes the economy bottleneck.
    """
    m=Match()
    for pid in range(n):m.add_player(str(pid))
    m.start()
    m.towers=[[index,sum(TOWERS[k][0] for k in (index//4*4,index//4*4+1,index)),0.] for index in build]
    maximum=0
    while m.phase!='defeat' and m.wave<61:
        if m.phase in ('prep','break'):m.start_wave()
        m.tick(.1,{})
        maximum=max(maximum,len(m.enemies))
    assert maximum<=64 and m.phase=='defeat'
    return m.wave


if __name__=='__main__':
    for n in (1,2,4):probe(n)
    # Plausible mixes: AoE at the bend, ice control, armor-piercing and core cover.
    builds=[(2,3,7,3,7,7,10,11),(3,3,7,7,10,7,7,11),
            (7,3,7,7,10,7,10,11),(7,3,7,7,11,7,10,11)]
    for n in (1,2,4):
        results=[maxed(n,build) for build in builds]
        best=max(range(len(results)),key=results.__getitem__)
        print('MAXED %dp: defeat wave=%d build=%s candidates=%s'%(n,results[best],builds[best],results))
