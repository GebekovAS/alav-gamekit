"""Focused regression checks for load mode, order repair and renderer batching."""
import os
from unittest.mock import patch
from rules import Match,enemy_kind,START
from test_network import load

with patch.dict(os.environ,{'COOP_DEBUG_WAVE':'20','COOP_DEBUG_CASH':'12345','COOP_DEBUG_TOWERS':'full'}):
    m=Match();m.add_player('0');m.add_player('1')
    m.tick(.01,{'0':(0,16),'1':(0,16)})
    assert m.phase=='prep' and m.wave==19 and m.bank['cash']==12345
    assert all(t and t[0]%4 in (2,3) for t in m.towers)
    m.tick(.01,{'0':(0,START),'1':(0,START)})
    assert m.wave==20 and m.wave_players==2 and m.phase=='wave'
    m.pending=[];m.spawn(5,869.99);m.core=1;m.tick(.1,{})
    assert m.core==1 and m.phase!='defeat'
with patch.dict(os.environ,{},clear=True):
    m=Match();m.add_player('0');m.start();m.start_wave();m.pending=[]
    m.spawn(5,869.99);m.core=1;m.tick(.1,{})
    assert m.core==0 and m.phase=='defeat' and m.bank['cash']==240

m=Match();m.add_player('0');m.start();m.start_wave();m.pending=[]
for i in range(64):m.spawn(i%6,(i*53)%700)
for frame in range(50):
    for i,e in enumerate(m.enemies):e[1]+=(i%7)*.3
    if frame%7==0:m.spawn(0,frame*13)
    if frame%5==0:m.enemies.pop(frame%len(m.enemies));m.order_dirty=True
    ordered=m.progress_order()
    assert ordered==sorted(m.enemies,key=lambda e:e[1],reverse=True)
    assert len({id(e) for e in ordered})==len(m.enemies)

ns,kit=load();ns['begin']('host')
m=ns['match'];m.start();m.start_wave()
count=[0];snapshot=m.snapshot
def counted():count[0]+=1;return snapshot()
m.snapshot=counted
for frame in range(80):ns['update'](.0125)
assert 9<=count[0]<=10,count
assert len(set(round(v,5) for v in m.scan_due))==8

es=[[i*8+k,100+i*.8] for k in range(3) for i in range(1,17)]
small,used=ns['crowd_groups'](es)
groups=ns['packs'][:]
assert groups and len(used)==sum(len(group) for group in groups)
for group in groups:
    assert len({enemy_kind(i) for i in group})==1
    assert len(group) in (3,5,8)
for e in es:e[1]+=.1
ns['crowd_groups'](es)
assert ns['packs']==groups
es=[e for e in es if e[0]!=groups[0][0]]
small,used=ns['crowd_groups'](es)
assert all(i in small for group in ns['packs'] for i in group)
for e in es:e[1]=239 if e[0]%16==0 else 241
small,used=ns['crowd_groups'](es)
for group in ns['packs']:
    assert len({ns['road_segment'](small[i][1]) for i in group})==1
print('PASS load mode/core, incremental stable order, 10Hz snapshots, stagger phases, persistent same-kind packs/corners/deaths')
