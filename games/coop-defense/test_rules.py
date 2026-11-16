"""Run with Python 3.11; no ALAV or third-party imports."""
import json
import math
from rules import *

checks=0

def test(name,fn):
    global checks
    fn();checks+=1
    print('PASS',name)


def economy():
    b=bank_new()
    assert transaction(b,'1',4,8,0,True)==''
    assert b['cash']==240 and free_cash(b)==170
    assert transaction(b,'0',0,0,0)=='' and b['cash']==190 and free_cash(b)==120
    before=json.dumps(b,sort_keys=True)
    assert '2' in transaction(b,'0',4,0,0)
    assert json.dumps(b,sort_keys=True)==before
    assert transaction(b,'0',0,3,0)=='Нужно ещё 20'
    assert json.dumps(b,sort_keys=True)==before
    assert transaction(b,'1',4,8,14,True)=='' and b['r']['1'][3]==15
    assert transaction(b,'1',4,8,14)==''
    assert b['cash']==120 and not b['r']
    assert refund(165)==115 and refund(250)==175


def replacement():
    b=bank_new();b['cash']=100
    transaction(b,'0',0,0,0,True)
    transaction(b,'1',1,0,0,True)
    before=json.dumps(b,sort_keys=True)
    assert transaction(b,'0',2,8,1,True)=='Нужно ещё 20'
    assert json.dumps(b,sort_keys=True)==before
    assert transaction(b,'0',2,0,2,True)==''
    assert b['r']['0'][0]==2 and b['r']['0'][3]==17
    expire(b,15,{'0','1'});assert list(b['r'])==['0']
    expire(b,15,{'1'});assert not b['r'] and b['cash']==100
    # Two competing requests in one host tick have exactly one winner.
    assert transaction(b,'0',2,0,20,True)==''
    assert transaction(b,'1',2,0,20,True).startswith('Занято')


def scales():
    for n,f in enumerate((.75,1,1.25,1.5),1):
        for wave in range(1,11):
            counts,bonus=scaled_wave(wave,n)
            assert counts==[math.ceil(v*f) if k!=5 else v for k,v in enumerate(WAVES[wave-1][:6])]
            assert bonus==math.ceil(WAVES[wave-1][6]*f)
    assert scaled_wave(10,4)[0][5]==1
    assert upgrade_options(None)==[0,4,8]
    assert upgrade_options(1)==[2,3] and upgrade_options(3)==[]


def combat():
    assert damage(10,6)==4 and damage(4,8)==1
    assert damage(10,6,True)==6 and damage(50,8,True,True)==75
    assert slow_speed(40,.5)==20 and slow_speed(40,.5,True)==30
    assert slow_speed(40,0,False,True)==0
    assert slow_speed(40,0,True,True)==0
    assert repair_quote(150)==(0,0) and repair_quote(149)==(1,1)
    assert repair_quote(124)==(25,5) and repair_quote(127)==(23,5)


def queues():
    es=[[8,299],[16,280],[24,266],[32,752]]
    positions,attackers=wall_queue(es,{8:302,16:290,24:285,32:760},[150,150])
    assert positions=={8:300,16:286,24:272,32:760}
    assert attackers==[8,None]
    positions,attackers=wall_queue(es,{8:302,16:290,24:285,32:760},[0,150])
    assert positions[8]==302 and attackers==[None,None]
    positions,attackers=wall_queue([[8,749],[16,730]],{8:751,16:740},[0,150])
    assert positions=={8:750,16:736} and attackers==[None,8]


def menus():
    m=Match();m.add_player('0');m.add_player('1')
    m.tick(.01,{'0':(0,A)});assert m.phase=='room'
    m.tick(.01,{'1':(0,A)});assert m.phase=='prep' and m.timer==0
    p=m.players['0'];p['menu']='';p['x'],p['y']=104,138;p['target']=0
    m.tick(.01,{'0':(0,A)});assert p['menu']=='build'
    m.tick(.01,{'0':(0,Y)});assert m.bank['r']['0'][2]==50
    m.tick(.01,{'0':(0,A)});assert m.towers[0][:2]==[0,50] and m.bank['cash']==190
    # Upgrade to II, then a final branch, through the real authoritative menu.
    m.tick(.01,{'0':(0,A)});m.tick(.01,{'0':(0,A)})
    assert m.towers[0][:2]==[1,110] and m.bank['cash']==130
    m.tick(.01,{'0':(0,A)});m.tick(.01,{'0':(0,A)})
    assert m.towers[0][:2]==[2,240] and m.bank['cash']==0
    m.tick(.01,{'0':(0,Y)});assert p['menu']=='plan'
    m.tick(.01,{'0':(0,A)});assert m.bank['r']['0'][4] and m.towers[0]
    # Any other player is blocked while the sale request owns the pad.
    q=m.players['1'];q['x'],q['y']=104,138;q['menu']='plan';q['sel']=0
    m.tick(.01,{'1':(0,A)});assert m.towers[0] and m.bank['cash']==0
    m.tick(.01,{'0':(0,A)});assert m.towers[0] is None and m.bank['cash']==168
    m.bank['cash']=240;m.buy('0',0,True);m.remove_player('0')
    assert not m.bank['r'] and len(m.players)==1


def repair_and_markers():
    m=Match();m.add_player('0');m.add_player('1');m.start()
    p=m.players['0'];q=m.players['1']
    for t in (p,q):t['menu']='';t['x'],t['y']=284,170;t['target']=8
    m.walls[0]=120
    for _ in range(11):m.tick(.1,{'0':(B,0),'1':(B,0)})
    assert m.walls[0]==145 and m.bank['cash']==235
    assert m.repairs[0][0]=='0' and '1' in q['msg']
    m.tick(.1,{});assert not m.repairs
    m.walls[0]=0
    for _ in range(21):m.tick(.1,{'0':(B,0)})
    assert m.walls[0]==25 and m.bank['cash']==225
    m.tick(.1,{'0':(0,X)});assert m.markers['0'][0]==8
    expiry=m.markers['0'][1]
    m.tick(.1,{'0':(0,X)});assert m.markers['0'][1]==expiry
    for _ in range(61):m.tick(.1,{})
    assert not m.markers


def waves_and_outcomes():
    m=Match();m.add_player('0');m.start()
    m.players['0']['x'],m.players['0']['y']=550,380
    m.tick(.1,{'0':(0,START)});assert m.phase=='wave' and m.wave==1 and m.bank['cash']==240
    # Fixture kills use the actual reward, cleanup and phase transitions.
    for wave in range(1,11):
        if m.phase!='wave':m.start_wave()
        assert m.wave==wave
        for _ in range(4000):
            for e in m.enemies:e[2]=0
            m.tick(.1,{})
            assert len(m.enemies)<=64
            if m.phase!='wave':break
        assert m.phase=='break'
    m=Match();m.add_player('0');m.start();m.start_wave();m.pending=[]
    m.walls=[0,0];m.core=1;m.spawn(0,869.9);m.enemies[0][2]=0
    m.tick(.1,{});assert m.phase=='defeat' and m.core==0
    # Carrier spawns exactly six, retaining its point on the route.
    m=Match();m.add_player('0');m.start();m.start_wave();m.pending=[]
    m.spawn(4,400);m.enemies[0][2]=0;m.tick(.1,{})
    assert len(m.enemies)==6 and all(enemy_kind(e[0])==0 for e in m.enemies)
    assert m.bank['cash']==250


def targeting_and_limits():
    m=Match();m.add_player('0');m.start();m.start_wave();m.pending=[]
    m.towers[0]=[3,250,0]
    m.spawn(3,90);m.spawn(3,110)
    m.tick(.1,{})
    assert m.enemies[0][2]==180 and m.enemies[1][2]==130
    for i in range(80):m.effect(0,(0,0),(1,1))
    assert len(m.effects)==16 and m.effects[0][0]==m.event-15
    m=Match();m.add_player('0');m.start();m.start_wave()
    for _ in range(64):m.spawn(0,0)
    m.tick(.1,{})
    assert len(m.enemies)==64 and m.pending
    # Building beneath a worker cannot trap them inside a tower.
    b=Match();b.add_player('0');b.start()
    p=b.players['0'];p['x'],p['y']=PADS[0];p['target']=0
    b.buy('0',0)
    assert not rect_hit((p['x']-9,p['y']-10,18,20),(89,85,30,30))
    # Weaker slow refreshes do not extend an expired stronger slow.
    m.enemies[0][8]={.55:m.time+.05,.35:m.time+1}
    m.tick(.1,{})
    assert m.enemies[0][4]==.35
    packet=json.dumps(m.snapshot(),ensure_ascii=False,separators=(',',':')).encode()
    assert len(packet)<4096


def endless_and_ready():
    for n,template in ((11,6),(15,10),(30,10)):
        assert wave_template(n)==template
        hp,armor,reward=wave_stats(n)
        assert math.isclose(hp,1.16**(n-10)) and armor==(n-10)//5
        assert math.isclose(reward,1.05**(n-10))
        for players in range(1,5):
            counts,bonus=scaled_wave(n,players)
            assert sum(counts)<=130 and counts[5]==WAVES[template-1][5]
            assert bonus==60+5*(n-10)
        assert scaled_wave(n,2)[0]==list(WAVES[template-1][:6])
        m=Match();m.add_player('0');m.wave=n;m.phase='wave'
        m.spawn(3,0);assert math.isclose(m.enemies[0][2],180*hp)
        assert bounty(3,n)==max(1,round(6*reward))
    m=Match();m.add_player('0');m.add_player('1');m.start()
    assert all(not p['menu'] for p in m.players.values())
    m.tick(100,{})
    assert m.phase=='prep' and m.timer==0
    m.tick(.1,{'0':(SELECT,START)})
    assert not m.players['0']['ready']
    m.tick(.1,{'0':(0,START)})
    assert m.players['0']['ready'] and m.phase=='prep'
    m.tick(.1,{'0':(0,START)})
    assert not m.players['0']['ready']
    m.tick(.1,{'0':(0,START),'1':(0,START)})
    assert m.phase=='wave' and m.bank['cash']==240
    m.enemies=[];m.pending=[];m.wave=10;m.tick(.1,{})
    assert m.phase=='break' and m.timer==40 and m.snapshot()['banner']==10
    m.tick(2.1,{})
    assert not m.snapshot()['banner']
    m.tick(.1,{'0':(0,START),'1':(0,START)})
    assert m.wave==11 and m.phase=='wave' and m.bank['cash']>240
    m=Match();m.add_player('0');m.start();p=m.players['0']
    p['x'],p['y']=284,170;p['target']=8
    m.tick(2,{'0':(B,A)})
    assert not m.repairs and m.bank['cash']==240 and not p['ready']
    assert p['msg']=='держи B — ремонт'
    m.walls[0]=149;m.tick(.1,{'0':(B,0)})
    assert m.repairs
    m.tick(1,{'0':(B,0)});m.tick(.1,{'0':(B,0)})
    assert m.walls[0]==150 and not m.repairs and m.bank['cash']==239
    # Late-wave cap also applies while carriers release offspring, including pending.
    m.start_wave();m.wave=30
    m.pending=[(0,0)]*128;m.spawn(4,400);m.enemies[0][2]=0
    m.tick(.1,{})
    assert m.spawned+len(m.pending)==130
    for _ in range(64-len(m.enemies)):m.spawn(0,0)
    m.tick(.1,{})
    assert len(m.enemies)==64



for name,fn in [('endless formulas/ready/full walls',endless_and_ready),('atomic economy',economy),('reservation replacement/expiry/drop',replacement),
                ('all 10 waves x 1/2/3/4 players',scales),('damage/armor/freeze/repair costs',combat),
                ('wall queue and single attacker',queues),('build/branch/reserve/sale menus',menus),
                ('exclusive repair/rebuild/markers',repair_and_markers),('endless phases/defeat/carrier',waves_and_outcomes),
                ('targeting/caps/snapshot size',targeting_and_limits)]:test(name,fn)
print('%d rule groups: PASS'%checks)
