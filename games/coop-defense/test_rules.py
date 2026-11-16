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
    assert 8 not in m.targets(p) and not p['msg']
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



def map_geometry():
    from maps import MAPS,lane
    import itertools
    for ident,m in enumerate(MAPS):
        assert len(m['pads'])==8 and len(m['walls'])==2 and len(m['spawns'])==4
        roads=[]
        for a,b in zip(m['route'],m['route'][1:]):
            assert (a[0]==b[0]) != (a[1]==b[1])
            roads.append((min(a[0],b[0])-25,min(a[1],b[1])-25,abs(a[0]-b[0])+50,abs(a[1]-b[1])+50))
        objects=[]
        for coords,w,h in ((m['pads'],48,36),(m['spawns'],18,20)):
            for x,y in coords:
                box=(x-w/2,y-h/2,w,h)
                assert not any(rect_hit(box,r) for r in roads),(ident,(x,y),'road')
                assert 0<=box[0] and box[0]+w<=600 and 32<=box[1] and box[1]+h<=440
                objects.append(box)
        cx,cy=m['core'];objects.append((cx-15,cy-15,30,30))
        for gate,(x,y) in zip(m['gates'],m['walls']):
            assert 0<gate<m['length']
            assert lane(gate,map_id=ident)==(x,y)
            segment=next(s for s,end in zip(m['segments'],m['ends']) if gate<=end)
            w,h=(12,48) if segment[2] else (48,12)
            objects.append((x-w/2,y-h/2,w,h))
        assert not any(rect_hit(a,b) for a,b in itertools.combinations(objects,2)),ident
        assert all(lane(end,map_id=ident)==point for end,point in zip(m['ends'],m['route'][1:]))
        assert all(42<=x<=568 and 67<=y<=387 for x,y in m['spawns'])
        for end in m['ends'][:-1]:
            assert math.dist(lane(end-.001,map_id=ident),lane(end+.001,map_id=ident))<.003
        assert lane(m['length'],map_id=ident)==m['core']
        match=Match(map_id=ident)
        for i in range(4):match.add_player(str(i))
        snap=json.loads(json.dumps(match.snapshot()))
        assert snap['map']==ident and len({tuple(p[:2]) for p in snap['p'].values()})==4
        p=match.players['0'];p['x'],p['y']=m['walls'][0]
        assert 8 not in match.targets(p)
        match.walls[0]=149
        assert 8 in match.targets(p)
    match=Match();match.add_player('0');match.add_player('1')
    match.tick(.01,{'1':(0,RIGHT)})
    assert match.map_id==0
    match.tick(.01,{'0':(0,LEFT)})
    assert match.map_id==3 and all(not p['ready'] for p in match.players.values())


def late_fixture(n=1):
    m=Match()
    for i in range(n):
        m.add_player(str(i));p=m.players[str(i)]
        p['x'],p['y']=104,138;p['target']=0
    m.start();m.start_wave();m.pending=[]
    m.towers[0]=[3,250,0.,0]
    m.spawn(5,500);m.enemies[0][5]=1000;m.enemies[0][2]=1e9
    return m


def overcharge():
    m=late_fixture();p=m.players['0']
    m.tick(.1,{'0':(A,A)});assert not p['menu'] and not m.over
    m.tick(.1,{'0':(0,0)});assert p['menu']=='build' and not m.over
    m=late_fixture(2)
    # Keep a healthy target in range for ten seconds; no stacks from two workers.
    def shots(players):
        m=late_fixture(players);m.spawn(5,80);m.enemies[-1][2]=1e9;m.enemies[-1][5]=100
        for i in range(100):m.tick(.1,{str(pid):(A,A if i==0 else 0) for pid in range(players)})
        return m.event,m
    count,m=shots(1);double,d=shots(2)
    assert count==double and 14<=count<=16,(count,double)
    assert m.over=={0:'0'} and not m.players['0']['menu']
    # Releasing, menu entry, leaving range and disconnect stop it on that tick.
    m.tick(.01,{});assert not m.over and not m.players['0']['menu']
    d.players['0']['x']=550;d.players['1']['x']=550
    d.tick(.01,{'0':(A,0),'1':(A,0)});assert not d.over
    d.remove_player('1');d.tick(.01,{});assert not d.over
    m=late_fixture();m.towers[0][2]=100
    for i in range(4):m.tick(.1,{'0':(A,A if i==0 else 0)})
    assert m.over
    m.tick(.01,{'0':(A,Y)});assert m.players['0']['menu']=='plan' and not m.over
    # Cooldown advances exactly 1.5x, independently of the scan cadence.
    m=late_fixture();m.towers[0][2]=10
    m.spawn(5,80);m.enemies[0][5]=100
    for i in range(3):m.tick(.1,{'0':(A,A if i==0 else 0)})
    before=m.towers[0][2];m.tick(.1,{'0':(A,0)})
    assert math.isclose(before-m.towers[0][2],.15)
    before=m.towers[0][2];m.tick(.1,{})
    assert math.isclose(before-m.towers[0][2],.1)


def jammers():
    for n in range(1,5):
        assert all(jammer_count(w,n)==0 for w in range(1,12))
        assert jammer_count(12,n)==(1,1,2,2)[n-1]
        assert jammer_count(25,n)==(3,4,5,6)[n-1]
        assert all(jammer_count(w,n)<=jammer_count(w+1,n) for w in range(12,40))
    m=late_fixture();m.wave=12
    assert m.spawn_jammer() and not m.spawn_jammer()
    assert m.jammers[0][3]==0
    # Flight follows the direct segment, independent of route/walls.
    j=m.jammers[0];j[1:3]=[0.,100.]
    m.towers[0][2]=100
    m.tick(.1,{});assert math.isclose(j[1],10) and j[2]==100
    for _ in range(11):m.tick(.1,{})
    assert j[5] and not m.spawn_jammer()
    m.phase='wave';m.towers[0][2]=0;m.spawn(5,90);hp_before=m.enemies[0][2]
    m.tick(.1,{});assert m.enemies[0][2]==hp_before and not m.effects
    cash=m.bank['cash']
    for _ in range(5):m.tick(.1,{'0':(B,0)})
    assert m.jammers
    m.tick(.1,{})
    for _ in range(9):m.tick(.1,{'0':(B,0)})
    assert m.jammers and m.bank['cash']==cash
    m.tick(.1,{'0':(B,0)});assert not m.jammers and m.bank['cash']==cash+JAMMER_BOUNTY
    m.tick(.1,{});assert m.effects
    # Airborne is targetable; landing keeps it immune even to area attacks.
    m=late_fixture();m.wave=12;m.spawn_jammer();j=m.jammers[0]
    j[1:3]=[0.,100.];j[4]=1
    m.tick(.1,{});assert not m.jammers and m.bank['cash']==240+JAMMER_BOUNTY
    # Spawn budget and offspring share the 64 alive slots.
    for _ in range(64):m.spawn(0,0)
    assert not m.spawn_jammer()
    m=late_fixture();m.wave=11;m.phase='break';m.start_wave()
    assert m.jammer_pending==1
    m.tick(2.1,{});assert len(m.jammers)==1 and not m.jammer_pending
    # A second worker cannot collect the same removal bounty.
    m=late_fixture(2);m.spawn_jammer();j=m.jammers[0];j[5]=True
    for _ in range(10):m.tick(.1,{'0':(B,0),'1':(B,0)})
    assert m.bank['cash']==248 and not m.jammers
    m=late_fixture();m.spawn_jammer();m.jammers[0][5]=True;p=m.players['0']
    for _ in range(5):m.tick(.1,{'0':(B,0)})
    p['x']=550;m.tick(.1,{'0':(B,0)});p['x']=104
    for _ in range(9):m.tick(.1,{'0':(B,0)})
    assert m.jammers
    m.tick(.1,{'0':(B,0)});assert not m.jammers


def mastery():
    assert [star_price(3,s) for s in range(4)]==[125,188,281,422]
    assert star_price(3,2000)>star_price(3,1999)>0
    m=late_fixture(2);m.phase='prep';m.bank['cash']=10000
    p=m.players['0'];q=m.players['1']
    assert m.options(p)==[12]
    m.tick(.01,{'0':(0,A)});assert p['menu']=='build'
    m.tick(.01,{'0':(0,Y)});assert m.bank['r']['0'][1:3]==[12,125]
    m.buy('1',12);assert stars(m.towers[0])==0
    assert m.bank['cash']==10000 and free_cash(m.bank)==9875
    m.tick(.01,{'0':(0,A)})
    assert stars(m.towers[0])==1 and m.towers[0][1]==375 and not m.bank['r']
    assert math.isclose(tower_damage(m.towers[0]),57.5)
    m.buy('0',12);assert stars(m.towers[0])==1  # stale token rejected
    for _ in range(7):m.buy('0',m.options(p)[0])
    assert stars(m.towers[0])==8 and math.isclose(tower_damage(m.towers[0]),110)
    total=m.towers[0][1];cash=m.bank['cash'];p['menu']='plan';p['sel']=0
    m.sell_request('0');m.sell_request('0')
    assert m.towers[0] is None and m.bank['cash']==cash+refund(total)
    # New fields survive compact JSON snapshots, without leaking private timers.
    m=late_fixture();m.towers[0][3]=7;m.over={0:'0'}
    m.spawn_jammer();m.jammers[0][5]=True
    m.towers[1]=[7,330,0.,2];m.spawn_jammer()
    packet=json.loads(json.dumps(m.snapshot()))
    assert packet['t'][0]==[3,250,7] and packet['oc']=={'0':'0'}
    assert len(packet['j'][0])==2 and len(packet['j'][1])==3
    assert len(json.dumps(packet).encode())<4096


for name,fn in [('overcharge hold/release/rate/no stacking',overcharge),('jammer spawn/flight/jam/removal/bounty/cap',jammers),('mastery price/damage/reserve/refund/snapshot',mastery),('all map geometry/snapshot/host picker/full wall targets',map_geometry),('endless formulas/ready/full walls',endless_and_ready),('atomic economy',economy),('reservation replacement/expiry/drop',replacement),
                ('all 10 waves x 1/2/3/4 players',scales),('damage/armor/freeze/repair costs',combat),
                ('wall queue and single attacker',queues),('build/branch/reserve/sale menus',menus),
                ('exclusive repair/rebuild/markers',repair_and_markers),('endless phases/defeat/carrier',waves_and_outcomes),
                ('targeting/caps/snapshot size',targeting_and_limits)]:test(name,fn)
print('%d rule groups: PASS'%checks)
