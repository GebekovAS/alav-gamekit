"""Медный дозор: host-authoritative cooperative defense for ALAV."""
import math
import alav as g

INK=(41,52,59)
CREAM=(255,244,214)
GOLD=(244,191,112)
TEAL=(64,185,167)
COLORS=[TEAL,(101,169,224),(220,153,88),(223,113,145)]
GATE=g.sprite(['ww...ww...ww','wggggggggggw','ww...ww...ww'],{'w':CREAM,'g':GOLD})
YARDS=[g.image('map-%d.png'%i) for i in range(1,5)]
MAP_PREVIEWS=g.image('map-previews.png')
BUILD_STRIP=g.image('build-strip.png')
TOWERS=g.image('towers.png')
PLAYERS=g.image('players.png')
ENEMIES=g.image('enemies.png')
ICONS=g.image('icons.png')
CORE=g.image('core.png')
HEADS=g.image('heads.png')
FX=g.image('effects.png')
PIN=g.image('pins.png')
BROKEN=g.image('core-broken.png')
GHOST=g.image('reservations.png')
BACKGROUNDS=[g.image(name+'-bg.png') for name in ('title','lobby','victory','defeat')]
# Four baked 128px frames per effect row. No runtime geometry for effects.
FX_NAMES=['rivet','muzzle','spark','lightning','crackle','rail','chips','slag',
          'shadow','splash','flame','shell','blast','laser','laser2','frost',
          'wave','roadfrost','spike','ice','scrap']
FX_ROWS={name:i for i,name in enumerate(FX_NAMES)}
FX_BOUNDS={name:(40,40,48,48) for name in FX_NAMES}
for name in ('lightning','rail','laser','laser2'):FX_BOUNDS[name]=(16,40,96,48)
for name in ('flame','wave'):FX_BOUNDS[name]=(4,4,120,120)
for name in ('blast','chips','splash'):FX_BOUNDS[name]=(20,4,88,120)
FX_CAP=37  # Plus at most three enemy status overlays: total effects <=40.
effect_limit=FX_CAP
effect_calls=0
effect_queue=[]

def fx(name,x,y,frame=0,scale=1,angle=0):
    effect_queue.append((name,x,y,frame,scale,angle))
    if len(effect_queue)>effect_limit:effect_queue.pop(0)

def ray(name,a,b,frame):
    dx,dy=b[0]-a[0],b[1]-a[1]
    fx(name,(a[0]+b[0])/2,(a[1]+b[1])/2,frame,
       math.hypot(dx,dy)/96,math.degrees(math.atan2(dy,dx)))

def attack(index,a,b,p,arc_scale=1):
    frame=min(3,int(p*4))
    x,y=b
    if index in (0,1):
        for j in range(index+1):
            q=(p+j*.16)%1
            fx('rivet',a[0]+(x-a[0])*q,a[1]+(y-a[1])*q,frame,.65)
        if p<.22:fx('muzzle',*a,frame,.6)
        if p>.6:fx('spark',x,y,frame,.65)
    elif index==2:
        if p<.8:
            ray('lightning',a,b,int(p*15)%3)
    elif index==3:
        if p<.8:ray('rail',a,b,frame)
        if p<.22:fx('muzzle',*a,frame,.9)
        if p>.25:fx('chips',x,y,frame,.85)
    elif index in (4,5,7):
        high=(42 if index==7 else 22)*arc_scale
        if p<.65:
            q=p/.65
            xx=a[0]+(x-a[0])*q;ground=a[1]+(y-a[1])*q
            fx('shadow',xx,ground,frame,.35+q*.4)
            fx('shell' if index==7 else 'slag',xx,ground-4*high*q*(1-q),frame,.8 if index!=5 else 1)
        else:fx('blast' if index==7 else 'splash',x,y,int((p-.65)/.35*4),.9 if index==7 else .7+index*.03)
    elif index==6:fx('flame',*a,frame,1)
    elif index in (8,9):
        if p<.85:
            ray('laser2' if index==9 else 'laser',a,b,frame)
    elif index==10:
        fx('roadfrost',x,y,frame,.7)
        fx('wave',*a,frame,.4+p*.6)
    else:
        if p<.6:
            q=p/.6;fx('spike',a[0]+(x-a[0])*q,a[1]+(y-a[1])*q,frame,.75,
                        math.degrees(math.atan2(y-a[1],x-a[0])))
        else:fx('ice',x,y,frame,.75)

def affected_enemy(kind,x,y,style,scale=1):
    n=ENEMY_SIZES[kind]
    g.draw(FX,x,y,scale,src=(kind*44,(21+style)*128,n,n))


def enemy_style(e,live,now):
    if live:return 2 if e[5]>0 else 1 if e[3]>0 else 3 if e[6]>now else 4 if e[7]>now else 0
    return e[3] if len(e)>3 else 0

def text(s,x,y,color=CREAM,size=20,align='left'):
    if size>=40:g.text(s,x+1,y+1,INK,size,align)
    g.text(s,x,y,color,size,align)

def icon(i,x,y,scale=1):
    g.draw(ICONS,x,y,scale,src=(i*16,0,16,16))

def tower(kind,level,x,y,scale=2):
    g.draw(TOWERS,x,y,scale,src=((kind*4+level-1)*24,0,24,24))

def enemy(kind,x,y,scale=1):
    n=ENEMY_SIZES[kind]
    g.draw(ENEMIES,x,y,scale,src=(kind*44,0,n,n))

def hp(kind,x,y,fraction):
    n=ENEMY_SIZES[kind]
    g.rect(x,y-5,max(1,int(n*fraction)),2,TEAL)

def player(i,x,y,scale=2,badge=True):
    g.draw(PLAYERS,x,y,scale,src=(i*24,0,24,24))
    if badge:
        g.rect(x+18*scale,y+2*scale,18,20,INK)
        text(str(i+1),x+18*scale+9,y+2*scale,COLORS[i],16,'center')

def head(i,x,y):
    g.draw(HEADS,x,y,2.5,src=(i*16,0,16,16))

from maps import MAPS
from rules import (Match, BUTTONS, PADS, WALL_POS, ENEMIES as ENEMY_DATA, NAMES,
                   TOWERS as TOWER_DATA, enemy_kind, enemy_xy, scaled_wave, enemy_hp, repair_quote,
                   upgrade_options, refund, A, B, UP, DOWN, LEFT, RIGHT, START, SELECT)
# Keep the rules table separate from the sprite atlas.
ENEMY_SIZES=[10,14,14,22,28,44]
TOWER_NAMES=[NAMES[i:i+4] for i in (0,4,8)]
# Measurement only: COOP_DEBUG_WAVE=20 [COOP_DEBUG_CASH=5000]
# [COOP_DEBUG_TOWERS=full]. Normal rooms/readiness remain; the debug core cannot die.
packs=[]
active_map=MAPS[0]


def road_segment(progress):
    a,b,c,d,_=active_map['ends']
    return 0 if progress<=a else 1 if progress<=b else 2 if progress<=c else 3 if progress<=d else 4


def crowd_groups(enemies):
    """Keep membership until death/road corner/separation, never regroup by frame.

    36px admission / 56px release hysteresis avoids threshold flicker. Small kinds
    is decorative-batched; authoritative enemies/HP/positions remain individual.
    """
    global packs
    small={e[0]:e for e in enemies if enemy_kind(e[0])<3}
    kept=[];used=set()
    for group in packs:
        group=tuple(i for i in group if i in small)
        if len(group)<3:continue
        progress=[small[i][1] for i in group]
        if road_segment(min(progress))!=road_segment(max(progress)) or max(progress)-min(progress)>56:continue
        kept.append(group);used.update(group)
    for kind in range(3):
        available=sorted((e for i,e in small.items() if i not in used and enemy_kind(i)==kind),key=lambda e:e[1])
        while len(available)>=3:
            first=available[0][1];segment=road_segment(first)
            near=[]
            for e in available[:8]:
                if road_segment(e[1])!=segment or e[1]-first>36:break
                near.append(e)
            count=8 if len(near)>=8 else 5 if len(near)>=5 else 3 if len(near)>=3 else 0
            if count:
                group=tuple(e[0] for e in near[:count]);kept.append(group);used.update(group)
                del available[:count]
            else:del available[0]
    packs=kept
    return small,used

net=None
match=None
view=None
previous=None
my_id='0'
net_clock=0.
send_clock=0.
snapshot_age=0.
last_snapshot=0.
clock=0.
seq=0
pending_presses=0
remote={}
seen={}
last_input={}
known=set()
suspended=set()
lost_message=''
lost_until=0.
muted=False
last_fx=0
leaving=False
role_started=False
exit_hold=0.
save_data=g.load()
records=save_data.setdefault("map_records",{})
# Preserve old team records on the original map.
for key,value in save_data.get('team_records',{}).items():records.setdefault('0:'+key,value)
selected_map=save_data.get('map',0)
if type(selected_map) is not int or not 0<=selected_map<len(MAPS):selected_map=0
recorded=False


def begin(role,solo=False):
    global net,match,view,previous,my_id,remote,seen,last_input,known,net_clock,send_clock,suspended
    global snapshot_age,last_snapshot,pending_presses,last_fx,leaving,packs
    net=g.host('coop-defense',max_players=4) if role=='host' else g.join('coop-defense')
    match=Match(g.hit,selected_map) if role=='host' else None
    my_id='0';view=None;previous=None;remote={};seen={};last_input={};known={'0'}
    net_clock=0.;send_clock=0.;snapshot_age=0.;last_snapshot=clock
    pending_presses=0;last_fx=0;leaving=False;suspended=set()
    packs=[]
    if match:
        match.add_player('0')
        if solo:match.start()
        view=match.snapshot()


def leave(message=''):
    global net,match,view,previous,lost_message,lost_until,leaving
    # There is no transport close in the public kit API. Leaving the room exits
    # through the kit; a lost host returns to the title without opening a socket.
    net=None;match=None;view=None;previous=None;leaving=False
    lost_message=message;lost_until=clock+5


def masks():
    held=pressed=0
    for i,b in enumerate(BUTTONS):
        if g.down(b):held|=1<<i
        if g.pressed(b):pressed|=1<<i
    if held&SELECT:pressed&=~START
    return held,pressed


def update(dt):
    global selected_map,clock,seq,pending_presses,send_clock,net_clock,my_id,view,previous
    global snapshot_age,last_snapshot,last_fx,muted,leaving,exit_hold,role_started,recorded
    clock+=dt
    held,pressed=masks()
    if net is None:
        if g.ROLE and not role_started:
            role_started=True
            begin(g.ROLE)
            return
        # Network play is started by the ALAV Store (Создать игру / Рядом играют): it sets g.ROLE.
        if pressed&A:begin('host')
        return
    # recv must also run in rooms, result screens, build/plan menus and while searching.
    messages=net.recv()
    local=view['p'].get(my_id) if view else None
    exit_button=B if view is None or view['s']=='room' or view.get('wait') else 0
    exit_hold=exit_hold+dt if exit_button and held&exit_button else 0.
    if exit_hold>=1.5:g.quit();return
    send_clock+=dt;net_clock+=dt;snapshot_age+=dt
    if net.is_host:
        ids={'0'}|{str(pid) for pid in net.peers}
        arriving={str(pid) for pid,msg in messages if isinstance(msg,list) and len(msg)==3 and all(type(v) is int for v in msg) and 0<=msg[1]<4096 and 0<=msg[2]<4096}
        for pid in list(match.players):
            if pid!='0' and (pid not in ids or clock-last_input.get(pid,clock)>5):
                suspended.add(pid)
                match.remove_player(pid);remote.pop(pid,None);seen.pop(pid,None);last_input.pop(pid,None)
        for pid in sorted(ids,key=int):
            if pid not in match.players and (pid not in suspended or pid in arriving) and (match.phase!='wave' or pid in known):
                match.add_player(pid);known.add(pid);last_input[pid]=clock;seen.pop(pid,None);suspended.discard(pid)
        for pid,msg in messages:
            pid=str(pid)
            if pid not in match.players:continue
            if not isinstance(msg,list) or len(msg)!=3 or not all(type(v) is int for v in msg):continue
            number,h,p=msg
            if number<=seen.get(pid,-1) or h<0 or p<0 or h>=4096 or p>=4096:continue
            seen[pid]=number;last_input[pid]=clock
            old=remote.get(pid,(0,0));remote[pid]=(h,old[1]|p)
        inputs={'0':(held,pressed)}
        for pid,value in remote.items():
            inputs[pid]=value if clock-last_input.get(pid,0)<1 else (0,0)
        if match.phase=='defeat' and pressed&A:
            match.__init__(g.hit,match.map_id)
            for pid in sorted(ids,key=int):match.add_player(pid)
        match.tick(min(dt,.1),inputs)
        if match.map_id!=selected_map:
            selected_map=match.map_id;save_data['map']=selected_map;g.save(save_data)
        for pid,value in list(remote.items()):remote[pid]=(value[0],0)
        if net_clock>=.1:
            view=match.snapshot()
            net_clock%=.1
            for pid in list(net.peers):
                packet=dict(view);packet['you']=str(pid);packet['tick']=seq
                if str(pid) not in match.players:packet['wait']=True
                net.send(packet,to=pid)
            seq+=1
    else:
        for _,msg in messages:
            if not isinstance(msg,dict) or 'p' not in msg or 'you' not in msg:continue
            previous=view;view=msg;my_id=msg['you'];last_snapshot=clock;snapshot_age=0.
        pending_presses|=pressed
        if send_clock>=.05:
            send_clock%=.05;seq+=1;net.send([seq,held,pending_presses]);pending_presses=0
        if view is None:
            if clock-last_snapshot>15:leave('Ведущий не найден')
            return
        if clock-last_snapshot>5:leave('Ведущий отключился');return
    if view:
        if view['s']=='defeat' and not recorded:
            key='%d:%d'%(view.get('map',0),view['team'])
            records[key]=max(records.get(key,0),view['n'])
            g.save(save_data);recorded=True
        elif view['s']!='defeat':recorded=False
        events=view.get('fx',[])
        fresh=[e for e in events if e[0]>last_fx]
        if fresh:
            last_fx=max(e[0] for e in fresh)
            if not muted:
                index=fresh[-1][1]
                g.tone(440 if index<8 else 820,35,volume=.08)


def interpolate(a,b):
    if net.is_host or previous is None or snapshot_age>=1:return b
    weight=min(1,snapshot_age/.1)
    return a+(b-a)*weight


def draw_title():
    g.draw(BACKGROUNDS[0],0,0)
    text('МЕДНЫЙ',300,20,CREAM,54,'center');text('ДОЗОР',300,73,GOLD,70,'center')
    g.draw(CORE,244,153,2.3)
    for i,x,y in [(0,105,253),(1,182,277),(2,358,277),(3,435,253)]:player(i,x,y,2.5,False)
    text('A — начать',300,358,GOLD,24,'center')
    text('С друзьями: ALAV Store → Рядом играют',300,400,CREAM,16,'center')
    if clock<lost_until:
        g.rect(70,177,460,64,INK);text(lost_message,300,198,GOLD,24,'center')


def seat(pid):
    p=view['p'].get(pid)
    return p[7] if p else int(pid)%4


def draw_room():
    g.draw(BACKGROUNDS[1],0,0);text('СМЕНА',300,30,GOLD,46,'center')
    map_id=view.get('map',0)
    g.draw(MAP_PREVIEWS,34,73,src=(map_id*120,0,120,82))
    text(MAPS[map_id]['name'],174,81,GOLD,24)
    text('LEFT/RIGHT — карта (ведущий)',174,116,CREAM,16)
    ids=list(sorted(view['p'],key=int))
    for slot in range(4):
        x=38+slot*134;i=seat(ids[slot]) if slot<len(ids) else slot
        g.rect(x,168,122,196,INK);g.rect(x,168,122,5,COLORS[i])
        text(str(i+1),x+61,177,COLORS[i],26,'center')
        if slot<len(ids):
            player(i,x+25,216,3,False)
            if view['p'][ids[slot]][5]:icon(4,x+45,305,2)
            else:text('A',x+61,307,CREAM,24,'center')
        else:text('ЖДЁМ',x+61,309,CREAM,18,'center')
    text('%d / 4'%len(ids),300,375,CREAM,24,'center')
    text('A — готов     B (держать) — выйти',300,412,CREAM,18,'center')


def draw_hud():
    g.rect(0,0,600,32,INK)
    icon(0,14,7);text(str(view['n']),38,5,GOLD,22)
    icon(1,241,7);text(str(view['c']),265,5,GOLD,22)
    icon(2,482,7);text(str(view['h']),506,5,TEAL,22)
    if view['s'] in ('prep','break'):
        g.rect(174,35,252,25,INK)
        text('ПОДГОТОВКА' if view['s']=='prep' else 'ПЕРЕДЫШКА %d'%math.ceil(view['tm']),300,37,CREAM,20,'center')
        for row,(pid,p) in enumerate(sorted(view['p'].items(),key=lambda v:int(v[0]))):
            x=12+row*42
            text(str(seat(pid)+1),x,38,COLORS[seat(pid)],16)
            if p[5]:icon(4,x+13,37)
        local=view['p'].get(my_id)
        if local and not local[5]:text('START — готов',590,38,GOLD,16,'right')
    if view.get('banner'):
        bubble('Рубеж %d'%view['banner'],300,100)


def tower_at(index,x,y,scale=2):
    tower(index//4,index%4+1,x,y,scale)


def draw_world():
    global effect_limit,active_map
    m=MAPS[view.get('map',0)]
    active_map=m
    pads=m['pads'];walls=m['walls'];map_id=view.get('map',0)
    g.draw(YARDS[map_id],0,32)
    # Solid cross-road doors and hinges, visibly different from mounting pads.
    for w,(wx,wy) in enumerate(walls):
        vertical=m['angles'][road_segment(m['gates'][w])]%180==0
        if view['w'][w]>0:
            g.draw(GATE,wx-24,wy-6,4,angle=90 if vertical else 0)
        else:
            for d in (-24,24):g.rect(wx-6 if vertical else wx+d-4,wy+d-4 if vertical else wy-6,12 if vertical else 8,8 if vertical else 12,GOLD)
        g.rect(wx-20,wy+26,40,3,INK)
        if view['w'][w]>0:g.rect(wx-20,wy+26,40*view['w'][w]/150,3,TEAL)
        if str(w) in view.get('fix',{}):icon(6,wx-8,wy-36)
    for pad,t in enumerate(view['t']):
        if t:
            x,y=pads[pad];tower_at(t[0],x-24,y-32)
    g.draw(CORE if view['h']>0 else BROKEN,m['core'][0]-40,m['core'][1]-39,1.65)
    health_caps=[enemy_hp(k,view['n']) for k in range(6)]
    live=net.is_host and match is not None
    enemies=match.enemies if live else view['e']
    now=match.time if live else view['now']
    effect_limit=20 if len(enemies)>40 else FX_CAP
    old_enemies={e[0]:e for e in previous['e']} if previous and not live else {}
    small,packed=crowd_groups(enemies)
    for group in packs:
        # A dying member only changes the count, never the surviving membership.
        count=len(group);drawn=8 if count>=8 else 5 if count>=5 else 3
        members=group[:drawn]
        progress=sum(interpolate(old_enemies.get(i,small[i])[1],small[i][1]) for i in members)/drawn
        x,y=enemy_xy(members[0],progress,map_id)
        segment=road_segment(progress);angle=m['angles'][segment]
        # Shared atlas tint follows the representative member; individual rules
        # and all large enemy status silhouettes stay unchanged.
        style=enemy_style(small[members[0]],live,now)
        tint=0 if not style else 1 if style==3 else 2 if style==4 else 3
        row=tint*9+enemy_kind(members[0])*3+(0 if drawn==3 else 1 if drawn==5 else 2)
        g.draw(ENEMIES,x-32,y-24,angle=angle,src=((members[0]//8%3)*64,44+row*48,64,48))
        for ident in group[drawn:]:packed.discard(ident)
    for e in enemies:
        if e[0] in packed:continue
        ident,progress=e[:2];kind=enemy_kind(ident);n=ENEMY_SIZES[kind]
        old=old_enemies.get(ident,e);progress=interpolate(old[1],progress)
        x,y=enemy_xy(ident,progress,map_id);health=e[2] if len(e)>2 else health_caps[kind]
        style=enemy_style(e,live,now)
        if style:
            affected_enemy(kind,x-n/2,y-n/2,0 if style==3 else 1 if style==4 else 2)
        else:enemy(kind,x-n/2,y-n/2)
        if kind>=3 and health<health_caps[kind]:hp(kind,x-n/2,y-n/2,health/health_caps[kind])
    for pid,r in view['r'].items():
        pad,index,cost,expires,sale=r;x,y=pads[pad];i=seat(pid)
        if not sale:g.draw(GHOST,x-24,y-36,2,src=(index*24,0,24,24))
        icon(1 if sale else 9,x-8,y-55)
        text(str(i+1),x+23,y-35,COLORS[i],16,'center')
        g.rect(x-22,y+16,44,4,INK);g.rect(x-22,y+16,44*max(0,min(1,(expires-view['now'])/15)),3,COLORS[i])
    for pid,m in view['m'].items():
        target,expires=m;coords=pads+walls
        if 0<=target<len(coords):
            x,y=coords[target];g.draw(PIN,x-12,y-64,src=(seat(pid)*24,0,24,28));text(str(seat(pid)+1),x,y-63,INK,16,'center')
    for pid,p in view['p'].items():
        old=previous['p'].get(pid,p) if previous else p
        if live and pid in match.players:x,y=match.players[pid]['x'],match.players[pid]['y']
        else:x=interpolate(old[0],p[0]);y=interpolate(old[1],p[1])
        player(seat(pid),x-24,y-32,2)
        if p[5]:icon(4,x-8,y-51)
    local=view['p'].get(my_id)
    if local:
        target=local[4]
        if not local[2] and not local[6]:
            if 0<=target<8:
                x,y=pads[target];g.rect(x-24,y-21,48,42,GOLD,fill=False)
                icon(3,local[0]+22,local[1]-30,1.25)
            elif 8<=target<10 and view['w'][target-8]<150:
                hp_now=view['w'][target-8]
                cost=10 if hp_now<=0 else repair_quote(hp_now)[1]
                bx,by=bubble('         ',local[0],local[1]-62)
                g.rect(bx+9,by+4,20,20,GOLD,fill=False)
                text('B',bx+19,by+5,GOLD,16,'center')
                icon(6,bx+37,by+6)
                text(str(cost),bx+63,by+5,GOLD,16)
    # The original attack timelines are driven by authoritative attack events.
    effect_queue.clear()
    latest={}
    events=match.effects if live else view.get('fx',[])
    for e in events:
        if e[1] in (2,6,8,9,10):latest[(e[1],e[2],e[3])]=e[0]
    for e in events:
        # A beam/ring is one sustained attack, not a stack of identical sprites.
        if e[1] in (2,6,8,9,10):
            source=(e[1],e[2],e[3])
            if latest[source]!=e[0]:continue
        age=now-e[6]+(0 if net.is_host else min(snapshot_age,.1))
        if 0<=age<1.2:
            if e[1]<0:
                if age<.384:fx('scrap',e[4],e[5],min(3,int(age/.096)),.65)
            else:attack(e[1],(e[2],e[3]),(e[4],e[5]),(now%1.2)/1.2 if e[1] in (2,6,8,9,10) else age/1.2)
    for name,x,y,frame,scale,angle in effect_queue:
        bx,by,w,h=FX_BOUNDS[name]
        g.draw(FX,x-w*scale/2,y-h*scale/2,scale,angle=angle,src=((frame%4)*128+bx,FX_ROWS[name]*128+by,w,h))
    draw_hud()


def draw_build(p):
    target=p[4]
    if not 0<=target<8:return
    t=view['t'][target];options=upgrade_options(t[0] if t else None)
    if not options:return
    selected=p[3]%len(options)
    if t is None:
        g.draw(BUILD_STRIP,69,372)
        for i,index in enumerate(options):
            x=69+i*155
            g.rect(x,372,148,62,GOLD if i==selected else INK,fill=False)
            text(str(TOWER_DATA[index][0]),x+86,379,GOLD,24)
        g.rect(115,343,370,25,INK);text('A — купить   Y — резерв   B — назад',300,347,CREAM,16,'center')
    elif len(options)==2:
        # Preserve the approved 09-branch composition and silhouettes.
        g.draw(BACKGROUNDS[1],0,0);tower_at(t[0],270,22,2.5)
        for i,index in enumerate(options):
            x=40+i*270
            g.rect(x,108,250,274,GOLD if i==selected else INK)
            g.rect(x+2,110,246,270,(70,84,90) if i==selected else INK)
            tower_at(index,x+77,128,4)
            text(NAMES[index],x+125,242,CREAM,28,'center')
            icon(1,x+83,282,1.25);text(str(TOWER_DATA[index][0]),x+112,277,GOLD,28)
            icon(0 if i==0 else 5,x+38,331,1.5);icon(7,x+120,335)
            counter=2 if index==2 else 3 if index in (3,11) else 0
            enemy(counter,x+171,330,1.5)
        text('Крестовина   A — купить   Y — резерв   B — назад',300,407,CREAM,16,'center')
    else:
        index=options[0];g.rect(69,340,462,94,INK)
        tower_at(index,90,350,3);text(NAMES[index],179,349,CREAM,24)
        icon(1,180,385);text(str(TOWER_DATA[index][0]),204,380,GOLD,24)
        text('A — купить   Y — резерв   B — назад',300,414,CREAM,16,'center')


def draw_plan(p):
    g.draw(BACKGROUNDS[1],0,0)
    reserved=sum(r[2] for r in view['r'].values())
    text('План команды',300,8,GOLD,28,'center')
    text('Всего %d / резерв %d / свободно %d'%(view['c'],reserved,view['c']-reserved),300,43,CREAM,16,'center')
    if view['s'] in ('prep','break'):
        counts,_=scaled_wave(view['n']+1,len(view['p']))
        for k,count in enumerate(counts):
            if count:
                x=16+k*96;enemy(k,x,69,2 if k==0 else 1.5);text('x%d'%count,x+(24 if k==0 else 34 if k<3 else 45 if k<5 else 65),78,CREAM,16)
        if view['s']=='break':text('%d с'%math.ceil(view['tm']),580,104,GOLD,16,'right')
    for row,(pid,q) in enumerate(sorted(view['p'].items(),key=lambda v:int(v[0]))):
        y=122+row*55;i=seat(pid)
        g.rect(26,y,548,49,INK);g.rect(26,y,6,49,COLORS[i]);head(i,42,y+3)
        text(str(i+1),91,y+13,COLORS[i],20)
        r=view['r'].get(pid)
        if r:
            pad,index,cost,expires,sale=r
            tower_at(index,112,y,2);icon(7,168,y+16)
            text('+%d'%refund(view['t'][pad][1]) if sale and view['t'][pad] else str(cost),196,y+12,GOLD,22)
            text('Продать' if sale else 'Резерв',294,y+4,CREAM,16)
            text('Место %d • %d с'%(pad+1,max(0,math.ceil(expires-view['now']))),294,y+25,CREAM,16)
        if q[5]:icon(4,526,y+14,1.5)
    pad=p[3]%8;t=view['t'][pad]
    g.rect(26,350,548,84,INK)
    text('Место %d'% (pad+1),44,357,GOLD,22)
    if t:
        tower_at(t[0],160,350,2)
        text('Продажа +%d (70%%)'%refund(t[1]),226,357,CREAM,20)
    else:text('Пусто',226,357,CREAM,20)
    text('L1/R1 — место  A — продажа рядом',300,387,CREAM,16,'center')
    text('B — отменить свой резерв / назад   Y — закрыть',300,413,CREAM,16,'center')


def bubble(message,x,y):
    width=min(576,len(message)*9+20)
    left=max(12,min(588-width,x-width/2));top=max(66,min(391,y))
    g.rect(left,top,width,29,INK)
    g.rect(max(left+6,min(left+width-10,x-3)),top+29,6,5,INK)
    text(message,left+width/2,top+5,GOLD,16,'center')
    return left,top


def draw_result():
    g.draw(BACKGROUNDS[3],0,0)
    text('ПОРАЖЕНИЕ',300,29,(246,180,183),48,'center')
    g.draw(BROKEN,228,142,3)
    for k,x,y in [(1,151,173),(2,391,183),(4,365,280),(5,278,302)]:enemy(k,x,y)
    seconds,kills,spent=view['stats']
    g.rect(60,348,480,56,INK)
    text('Волна %d    %02d:%02d'%(view['n'],seconds//60,seconds%60),300,350,GOLD,24,'center')
    text('Рекорд команды (%d): %d'%(view['team'],records.get('%d:%d'%(view.get('map',0),view['team']),view['n'])),300,380,CREAM,18,'center')
    text('A — новая смена (ведущий)' if not net.is_host else 'A — новая смена',300,413,CREAM,18,'center')


def draw():
    g.clear(INK)
    if net is None:draw_title();return
    if view is None:
        g.draw(BACKGROUNDS[1],0,0);text('ПОИСК СМЕНЫ',300,160,GOLD,34,'center')
        text('B (держать) — выйти',300,282,CREAM,22,'center');return
    if view['s']=='room':draw_room();return
    if view['s']=='defeat':draw_result();return
    draw_world()
    p=view['p'].get(my_id)
    if p:
        if p[2]=='build':draw_build(p)
        elif p[2]=='plan':draw_plan(p)
        if p[6]:
            if p[2]=='plan':
                row=sorted(view['p'],key=int).index(my_id)
                bubble(p[6],300,94+row*55)
            else:bubble(p[6],p[0],p[1]-76)
        elif not p[2]:
            if view['s']=='prep':
                text('A — строить у площадки, START — готов',300,414,CREAM,16,'center')
    if not net.is_host and snapshot_age>1:
        g.rect(155,188,290,50,INK);text('Нет связи с ведущим',300,203,GOLD,22,'center')
    if view.get('wait'):
        g.rect(80,170,440,80,INK);text('Вход после волны',300,190,GOLD,26,'center')
        text('B (держать) — выйти',300,224,CREAM,18,'center')


g.run(update,draw,'Медный дозор')
