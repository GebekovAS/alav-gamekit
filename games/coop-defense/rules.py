"""Authoritative, kit-free rules for Copper Watch v1."""
import math
import os
import random
from operator import itemgetter
from functools import lru_cache

from maps import MAPS, lane
PADS = MAPS[0]['pads']
ROUTE = MAPS[0]['route']
WALL_PROGRESS = MAPS[0]['gates']
WALL_POS = MAPS[0]['walls']
NAMES = ['Клепатель I','Клепатель II','Шквал','Молот','Котёл I','Котёл II','Жаровня','Мортира','Стужа I','Стужа II','Мороз','Ледокол']
# price, damage/hit, interval, range, blast radius, slow fraction, status seconds
TOWERS = [(50,10,.6,120,0,0,0),(60,18,.55,130,0,0,0),
          (130,9,.15,135,0,0,0),(140,50,1,155,0,0,0),
          (80,14,1.4,120,32,0,0),(85,24,1.4,130,40,0,0),
          (155,10,.35,78,78,0,0),(165,60,2.2,190,65,0,0),
          (70,4,1,115,0,.35,1.3),(75,8,1,125,0,.45,1.3),
          (145,6,1,115,115,.55,1.3),(155,30,1.2,135,0,0,1)]
# size, HP, speed, armor, bounty, wall damage/second, damage to core
ENEMIES = [(10,14,45,0,1,6,1),(14,45,36,0,2,10,3),(14,28,65,0,2,8,2),
           (22,180,26,6,6,16,8),(28,400,22,3,10,20,12),(44,2200,16,8,50,30,30)]
WAVES = [(12,6,0,0,0,0,25),(20,8,4,0,0,0,30),(30,8,6,1,0,0,35),
         (36,10,8,2,0,0,40),(24,6,4,2,0,1,50),(48,12,10,3,1,0,45),
         (56,12,12,4,1,0,50),(64,14,14,5,2,0,55),(72,16,16,6,2,0,60),
         (60,14,14,6,2,1,0)]
BUTTONS = ['UP','DOWN','LEFT','RIGHT','A','B','X','Y','L1','R1','START','SELECT']
UP,DOWN,LEFT,RIGHT,A,B,X,Y,L1,R1,START,SELECT = [1<<i for i in range(12)]
OVERCHARGE_HOLD=.3
JAMMER_BOUNTY=8
PROGRESS=itemgetter(1)


def jammer_count(wave,players):
    if wave<12:return 0
    base=1+min(3,(wave-12)*3//13)
    return math.ceil(base*(.75,1,1.25,1.5)[max(1,min(4,players))-1])


def stars(t):
    return t[3] if len(t)>3 else 0


def star_price(index,count):
    base=sum(TOWERS[k][0] for k in (index//4*4,index//4*4+1,index))
    # Exact round-to-even without a floating-point ceiling on mastery levels.
    denominator=2**(count+1);whole,remainder=divmod(base*3**count,denominator)
    return whole+int(remainder*2>denominator or (remainder*2==denominator and whole%2))


def tower_damage(t):
    return TOWERS[t[0]][1]*(1+.15*stars(t))


def enemy_kind(ident):
    return ident % 8


def enemy_xy(ident, progress, map_id=0):
    return lane(progress,(ident*13+ident*ident*3)%21-10,map_id)


def enemies_in_range(ordered,points,x,y,radius,map_id):
    radius2=radius*radius
    for e in ordered:
        if e[2]<=0:continue
        ident=e[0];point=points.get(ident)
        if point is None:
            point=enemy_xy(ident,e[1],map_id);points[ident]=point
        dx=point[0]-x;dy=point[1]-y
        if dx*dx+dy*dy<=radius2:yield e


def wave_template(wave):
    return wave if wave<=10 else 6+(wave-11)%5


@lru_cache(maxsize=32)
def wave_stats(wave):
    extra=max(0,wave-10)
    return 1.16**extra,extra//5,1.05**extra


@lru_cache(maxsize=192)
def enemy_hp(kind,wave):
    return ENEMIES[kind][1]*wave_stats(wave)[0]


def bounty(kind,wave):
    return max(1,round(ENEMIES[kind][4]*wave_stats(wave)[2]))


def scaled_wave(wave, players):
    factor=(.75,1,1.25,1.5)[max(1,min(4,players))-1]
    row=WAVES[wave_template(wave)-1]
    counts=[math.ceil(n*factor) if k!=5 else n for k,n in enumerate(row[:6])]
    if wave>10:
        # Preserve the rare types and boss, trim the most numerous type first.
        while sum(counts)>130:
            k=max(range(5),key=lambda i:counts[i]);counts[k]-=1
    return counts,math.ceil(row[6]*factor) if wave<=10 else 60+5*(wave-10)


def damage(amount, armor, frozen=False, piercing=False):
    return max(1,amount-(0 if piercing else armor))*(1.5 if frozen else 1)


def slow_speed(speed, slow, boss=False, frozen=False):
    if frozen:return 0
    return speed*(1-slow*(.5 if boss else 1))


def refund(invested):
    return invested*70//100


def upgrade_options(index):
    if index is None:return [0,4,8]
    level=index%4
    return [index+1] if level==0 else [index+1,index+2] if level==1 else []


def bank_new():
    return {'cash':240,'r':{},'seats':{}}


def expire(bank, now, ids=None):
    for pid,r in list(bank['r'].items()):
        if r[3]<=now or (ids is not None and pid not in ids):del bank['r'][pid]


def free_cash(bank, except_pid=None):
    return bank['cash']-sum(r[2] for pid,r in bank['r'].items() if pid!=except_pid)


def transaction(bank, pid, pad, index, now, reserve=False, sell=False, price=None):
    """Host serializes calls; failure never changes cash or the previous reservation."""
    price=0 if sell else TOWERS[index][0] if price is None else price
    for owner,r in bank['r'].items():
        if owner!=pid and r[0]==pad:return 'Занято игроком %d'%(bank.get('seats',{}).get(owner,int(owner))+1)
    old=bank['r'].get(pid)
    same=old is not None and old[:3]==[pad,index,price] and old[4]==sell
    available=free_cash(bank,pid if reserve or same else None)
    if available<price:return 'Нужно ещё %d'%(price-available)
    if reserve:
        if not same:bank['r'][pid]=[pad,index,price,now+15,sell]
    else:
        bank['cash']-=price
        if same:bank['r'].pop(pid,None)
    return ''


def repair_quote(hp):
    healed=min(25,max(0,150-hp))
    return healed,math.ceil(healed/5)


def wall_queue(enemies, proposed, walls, result=None, gates=WALL_PROGRESS):
    """Only enemies stopped by a closed gate queue; each gate has one attacker.

    enemies sorted by current progress descending; returns positions and attacker ids.
    Spacing is along the route, independent of the decorative lateral lane.
    """
    limits=[p if hp>0 else None for p,hp in zip(gates,walls)]
    attackers=[None,None]
    if result is None:result={}
    else:result.clear()
    for e in enemies:
        ident,old=e[0],e[1]
        value=proposed[ident]
        for w,gate in enumerate(gates):
            if limits[w] is None or old>gate+.01:continue
            if value>=limits[w]:
                value=max(old,limits[w])
                if attackers[w] is None and value>=gate-.01:attackers[w]=ident
                limits[w]=value-14
                break
        result[ident]=value
    return result,attackers


def rect_hit(a,b):
    return a[0]<b[0]+b[2] and a[0]+a[2]>b[0] and a[1]<b[1]+b[3] and a[1]+a[3]>b[1]


class Match:
    def __init__(self, hit=rect_hit, map_id=0):
        self.map_id=map_id
        self.map=MAPS[map_id]
        self.hit=hit
        self.phase='room'; self.time=0.; self.timer=0.; self.wave=0
        self.bank=bank_new(); self.core=100; self.walls=[150.,150.]
        self.players={}; self.towers=[None]*8; self.enemies=[]; self.pending=[]
        self.markers={}; self.repairs={}; self.effects=[]; self.event=0
        self.spawned=0; self.serial=0; self.scan=0.; self.spawn_clock=0.; self.bonus=0
        self.elapsed=0.; self.kills=0; self.spent=0; self.wave_players=1; self.banner_until=0.
        self.scan_due=[i*.1/8 for i in range(8)]
        self.ordered=[];self.points={}
        self.step_dt=None;self.steps=()
        self.spawn_interval=.65
        self.over={};self.jammers=[];self.jammer_pending=0;self.jammer_clock=0.
        self.rng=random.Random(1300+map_id)
        # Opt-in measurement fixture only; never used by ordinary rooms.
        value=os.environ.get('COOP_DEBUG_WAVE','0')
        self.debug_wave=max(0,min(999,int(value))) if value.isdecimal() else 0

    def add_player(self,pid):
        if pid not in self.players:
            used={p['slot'] for p in self.players.values()}
            i=next(slot for slot in range(4) if slot not in used)
            self.bank['seats'][pid]=i
            self.players[pid]={'x':float(self.map['spawns'][i][0]),'y':float(self.map['spawns'][i][1]),'fx':1,'fy':0,
                'slot':i,'menu':'','sel':0,'target':-1,'ready':False,'msg':'','until':0.,'mark':-10.,
                'a_pad':-1,'a_time':0.,'unjam':-1,'b_time':0.}

    def choose_map(self,map_id):
        if self.phase!='room':return
        self.map_id=map_id;self.map=MAPS[map_id]
        for p in self.players.values():
            p['x'],p['y']=self.map['spawns'][p['slot']]
            p['ready']=False;p['target']=-1

    def remove_player(self,pid):
        self.players.pop(pid,None); self.bank['r'].pop(pid,None); self.markers.pop(pid,None)
        self.bank['seats'].pop(pid,None)
        for w,r in list(self.repairs.items()):
            if r[0]==pid:del self.repairs[w]

    def say(self,pid,message):
        p=self.players.get(pid)
        if p:p['msg']=message;p['until']=self.time+1.5

    def start(self):
        self.phase='prep';self.timer=0
        if self.debug_wave:
            self.wave=self.debug_wave-1
            value=os.environ.get('COOP_DEBUG_CASH','5000')
            self.bank['cash']=int(value) if value.isdecimal() else 5000
            if os.environ.get('COOP_DEBUG_TOWERS')=='full':
                self.towers=[[k,sum(TOWERS[j][0] for j in (k//4*4,k//4*4+1,k)),0.] for k in (2,3,7,3,7,6,10,11)]
        for p in self.players.values():p['ready']=False;p['menu']=''

    def start_wave(self,early=False):
        if early and self.phase=='break':self.bank['cash']+=max(0,int(self.timer))
        self.wave+=1;self.wave_players=len(self.players)
        counts,self.bonus=scaled_wave(self.wave,self.wave_players)
        self.jammer_pending=jammer_count(self.wave,self.wave_players);self.jammer_clock=2.
        self.spawn_interval=min(.65,35/max(1,sum(counts)))
        # Interleave the types so counters matter throughout the release.
        self.pending=[]
        while any(counts):
            for k in range(6):
                if counts[k]:self.pending.append((k,0.));counts[k]-=1
        self.spawned=0;self.spawn_clock=0.;self.phase='wave';self.timer=0
        for p in self.players.values():
            p['ready']=False

    def targets(self,p):
        key=(self.map_id,p['x'],p['y'],p['fx'],p['fy'],self.walls[0]>=150,self.walls[1]>=150)
        if p.get('_targets_key')==key:return p['_targets']
        choices=[]
        for i,(x,y) in enumerate(self.map['pads']+self.map['walls']):
            dx=x-p['x'];dy=y-p['y'];d=dx*dx+dy*dy
            if i>=8 and self.walls[i-8]>=150:continue
            if d<=42*42:choices.append((d,-(dx*p['fx']+dy*p['fy']),i))
        result=[v[2] for v in sorted(choices)]
        p['_targets_key']=key;p['_targets']=result
        return result

    def options(self,p):
        target=p['target']
        if not 0<=target<8:return []
        t=self.towers[target]
        return [12+stars(t)] if t and t[0]%4>=2 else upgrade_options(t[0] if t else None)

    def price(self,pad,index):
        return star_price(self.towers[pad][0],index-12) if index>=12 else TOWERS[index][0]

    def buy(self,pid,index,reserve=False):
        p=self.players[pid];pad=p['target']
        if pad not in self.targets(p):self.say(pid,'Подойдите к месту');return
        if index not in self.options(p):self.say(pid,'Башня уже изменена');return
        price=self.price(pad,index)
        error=transaction(self.bank,pid,pad,index,self.time,reserve,price=price)
        if error:self.say(pid,error);return
        if reserve:self.say(pid,'Резерв 15 с');p['menu']='';return
        old=self.towers[pad]
        spent=(old[1] if old else 0)+price
        self.towers[pad]=[old[0],spent,old[2],stars(old)+1] if index>=12 else [index,spent,0.,0]
        # A tower may be built under a worker; move that worker onto free ground.
        blockers=[(self.map['core'][0]-15,self.map['core'][1]-15,30,30)]+[(self.map['pads'][i][0]-15,self.map['pads'][i][1]-15,30,30) for i,t in enumerate(self.towers) if t]
        for q in self.players.values():
            if self.hit((q['x']-9,q['y']-10,18,20),(self.map['pads'][pad][0]-15,self.map['pads'][pad][1]-15,30,30)):
                x,y=self.map['pads'][pad]
                for nx,ny in [(x-38,y),(x+38,y),(x,y-38),(x,y+38)]:
                    if 42<=nx<=568 and 67<=ny<=387 and not any(self.hit((nx-9,ny-10,18,20),b) for b in blockers):
                        q['x'],q['y']=nx,ny;break
        self.spent+=price;p['menu']='';self.say(pid,'Мастерство +1' if index>=12 else 'Построено')

    def sell_request(self,pid):
        p=self.players[pid];pad=p['sel']%8;t=self.towers[pad]
        if t is None:self.say(pid,'Здесь нет башни');return
        r=self.bank['r'].get(pid)
        if r and r[0]==pad and r[4]:
            if pad not in self.targets(p):self.say(pid,'Для продажи подойдите к месту');return
            self.bank['cash']+=refund(t[1]);self.towers[pad]=None
            self.jammers[:]=[j for j in self.jammers if not (j[3]==pad and j[5])]
            self.bank['r'].pop(pid,None);self.say(pid,'Продано: +%d'%refund(t[1]));return
        error=transaction(self.bank,pid,pad,t[0],self.time,True,True)
        self.say(pid,error or 'Продажа в плане: A рядом с местом')

    def action(self,pid,held,pressed,dt):
        p=self.players[pid]
        # Built towers: release before .3s opens the menu; a long hold consumes A.
        tap=False
        if not p['menu'] and self.phase in ('prep','break','wave'):
            choices=self.targets(p) if pressed&A or (p['a_pad']>=0 and not held&A) else None
            target=p['target'] if choices is None or p['target'] in choices else choices[0] if choices else -1
            if pressed&A and 0<=target<8 and self.towers[target]:
                p['a_pad']=target;p['a_time']=0.;pressed&=~A
            if p['a_pad']>=0:
                if held&A:p['a_time']+=dt
                else:
                    tap=p['a_time']<OVERCHARGE_HOLD and p['a_pad']==target
                    p['a_pad']=-1;p['a_time']=0.
            if tap:pressed|=A
        else:p['a_pad']=-1;p['a_time']=0.
        if pressed&START and not held&SELECT and self.phase in ('prep','break'):
            p['ready']=not p['ready']
            return
        if self.phase=='room':
            if pid=='0' and pressed&(LEFT|RIGHT):
                self.choose_map((self.map_id+(-1 if pressed&LEFT else 1))%len(MAPS))
                return
            if pressed&A:p['ready']=not p['ready']
            return
        if self.phase=='defeat':return
        choices=self.targets(p)
        if p['menu']=='build':
            options=self.options(p)
            if not options:p['menu']='';return
            if pressed&(LEFT|UP|L1):p['sel']=(p['sel']-1)%len(options)
            if pressed&(RIGHT|DOWN|R1):p['sel']=(p['sel']+1)%len(options)
            index=options[p['sel']%len(options)]
            if pressed&B:p['menu']=''
            elif pressed&A:self.buy(pid,index)
            elif pressed&Y:self.buy(pid,index,True)
        elif p['menu']=='plan':
            if pressed&(LEFT|UP|L1):p['sel']=(p['sel']-1)%8
            if pressed&(RIGHT|DOWN|R1):p['sel']=(p['sel']+1)%8
            if pressed&B:
                self.bank['r'].pop(pid,None);p['menu']=''
            elif pressed&A:self.sell_request(pid)
            elif pressed&Y:p['menu']=''
        else:
            dx=bool(held&RIGHT)-bool(held&LEFT);dy=bool(held&DOWN)-bool(held&UP)
            if dx or dy:
                p['fx'],p['fy']=dx,dy
                speed=120*dt/(math.sqrt(2) if dx and dy else 1)
                for axis,delta in [('x',dx*speed),('y',dy*speed)]:
                    x=p['x']+(delta if axis=='x' else 0);y=p['y']+(delta if axis=='y' else 0)
                    blockers=[(self.map['core'][0]-15,self.map['core'][1]-15,30,30)]
                    blockers.extend((self.map['pads'][i][0]-15,self.map['pads'][i][1]-15,30,30) for i,t in enumerate(self.towers) if t)
                    if not any(self.hit((x-9,y-10,18,20),b) for b in blockers):
                        p[axis]=max(42,min(568,x)) if axis=='x' else max(67,min(387,y))
                choices=self.targets(p)
                p['target']=choices[0] if choices else -1
            if p['target'] not in choices:p['target']=choices[0] if choices else -1
            if choices and pressed&(L1|R1):
                at=choices.index(p['target']) if p['target'] in choices else 0
                p['target']=choices[(at+(-1 if pressed&L1 else 1))%len(choices)]
            if pressed&Y:p['menu']='plan';p['sel']=max(0,min(7,p['target']))
            elif pressed&A:
                target=p['target'];r=self.bank['r'].get(pid)
                if target in choices and r and r[0]==target:
                    if r[4]:p['menu']='plan';p['sel']=target;self.sell_request(pid)
                    else:self.buy(pid,r[1])
                elif 0<=target<8:
                    if self.options(p):p['menu']='build';p['sel']=0
                    else:self.say(pid,'Ветка завершена; Y — план продажи')
                elif target>=8:self.say(pid,'держи B — ремонт')
        if pressed&X and self.time-p['mark']>=1:
            target=(p['sel']%8 if p['menu']=='plan' else p['target'])
            if target>=0:
                self.markers[pid]=[target,self.time+6];p['mark']=self.time
                owner=next((i for i,r in self.bank['r'].items() if r[0]==target and i!=pid),None)
                if owner:self.say(owner,'Игрок %d: нужны деньги'%(p['slot']+1))
        # Ownership persists only while the button is held beside the same wall.
        jam=next((j for j in self.jammers if j[5] and j[3] in choices),None) if not p['menu'] and held&B else None
        if jam:
            pad=jam[3];p['target']=pad
            p['b_time']=p['b_time']+dt if p['unjam']==pad else dt;p['unjam']=pad
            if p['b_time']>=1-1e-9:
                self.jammers.remove(jam);self.bank['cash']+=JAMMER_BOUNTY
                p['unjam']=-1;p['b_time']=0.;self.say(pid,'Глушилка снята: +%d'%JAMMER_BOUNTY)
        else:p['unjam']=-1;p['b_time']=0.
        if not jam and not p['menu'] and held&B:
            wall_choices=[t for t in choices if t>=8]
            if wall_choices:p['target']=wall_choices[0]
        w=p['target']-8
        if not jam and not p['menu'] and held&B and w in (0,1) and p['target'] in choices and self.walls[w]<150:
            r=self.repairs.get(w)
            if r and r[0]!=pid:self.say(pid,'Уже чинит игрок %d'%(self.players.get(r[0],{}).get('slot',0)+1))
            else:
                if r is None:r=[pid,0.];self.repairs[w]=r
                r[1]+=dt
        elif self.repairs:
            for w,r in list(self.repairs.items()):
                if r[0]==pid:del self.repairs[w]

    def spawn(self,kind,progress):
        self.spawned+=1;self.serial+=1;ident=self.serial*8+kind
        self.enemies.append([ident,progress,enemy_hp(kind,self.wave),0.,0.,0.,0.,0.,{}])

    def spawn_jammer(self):
        if len(self.enemies)+len(self.jammers)>=64:return False
        used={j[3] for j in self.jammers}
        pads=[i for i,t in enumerate(self.towers) if t and i not in used]
        if not pads:return False
        # Random among the strongest three unclaimed towers, weighted by investment.
        pads.sort(key=lambda i:self.towers[i][1],reverse=True)
        pad=self.rng.choices(pads[:3],weights=[max(1,self.towers[i][1]) for i in pads[:3]])[0]
        edge=self.rng.randrange(4);v=self.rng.uniform(40,560)
        x,y=((0,v*.65+40),(600,v*.65+40),(v,32),(v,440))[edge]
        self.serial+=1
        self.jammers.append([self.serial*8+6,x,y,pad,enemy_hp(1,self.wave),False])
        return True

    def progress_order(self):
        # C Timsort beats Python insertion repair at the bounded 64-enemy cap.
        # Sort spawn order so ties retain exactly the original target priority.
        self.ordered=sorted(self.enemies,key=PROGRESS,reverse=True)
        return self.ordered

    def effect(self,index,a,b):
        self.event+=1;self.effects.append([self.event,index,round(a[0],1),round(a[1],1),round(b[0],1),round(b[1],1),self.time])
        if len(self.effects)>16:self.effects.pop(0)

    def tick(self,dt,inputs):
        self.time+=dt
        if self.bank['r']:expire(self.bank,self.time,self.players)
        if self.markers:
            for pid,m in list(self.markers.items()):
                if m[1]<=self.time:self.markers.pop(pid,None)
        while self.effects and self.time-self.effects[0][6]>=1.2:self.effects.pop(0)
        for pid in sorted(self.players,key=int):
            held,pressed=inputs.get(pid,(0,0))
            self.action(pid,held,pressed,dt)
        self.over.clear()
        for pid,p in self.players.items():
            pad=p['a_pad']
            if (not p['menu'] and inputs.get(pid,(0,0))[0]&A and p['a_time']>=OVERCHARGE_HOLD
                    and 0<=pad<8 and self.towers[pad] and pad in self.targets(p)):
                self.over.setdefault(pad,pid)
        if self.phase=='room':
            if self.players and all(p['ready'] for p in self.players.values()):self.start()
            return
        if self.phase=='defeat':return
        self.elapsed+=dt
        if self.phase in ('prep','break'):
            if self.phase=='break':self.timer=max(0,self.timer-dt)
            ready=all(p['ready'] for p in self.players.values())
            if (self.phase=='break' and self.timer<=0) or ready:self.start_wave(ready)
        for w,r in list(self.repairs.items()):
            p=self.players.get(r[0])
            if self.walls[w]>=150 or not p or p['menu'] or not inputs.get(r[0],(0,0))[0]&B or p['target']!=w+8 or w+8 not in self.targets(p):
                del self.repairs[w]
                continue
            broken=self.walls[w]<=0
            if broken and any(abs(e[1]-self.map['gates'][w])<=20 for e in self.enemies):
                r[1]=0;self.say(r[0],'Уберите врагов от заслона');continue
            if r[1]<(2 if broken else 1):continue
            heal,cost=(25,10) if broken else repair_quote(self.walls[w])
            if cost and free_cash(self.bank)>=cost:
                self.bank['cash']-=cost;self.walls[w]+=heal
            elif cost:self.say(r[0],'Нужно ещё %d'%(cost-free_cash(self.bank)))
            r[1]=0
        if self.phase!='wave':return
        self.timer+=dt;self.spawn_clock-=dt
        self.jammer_clock-=dt
        if self.jammer_pending and len(self.enemies)+len(self.jammers)<64 and self.jammer_clock<=0:
            self.spawn_jammer();self.jammer_pending-=1;self.jammer_clock=6.
        for j in self.jammers[:]:
            if j[5]:continue
            if not self.towers[j[3]]:
                self.jammers.remove(j);self.spawn_jammer();continue
            x,y=self.map['pads'][j[3]];dx=x-j[1];dy=y-j[2];distance=math.hypot(dx,dy)
            if distance<=100*dt:j[1],j[2],j[5]=x,y,True
            else:j[1]+=dx/distance*100*dt;j[2]+=dy/distance*100*dt
        jammed={j[3] for j in self.jammers if j[5]}
        if self.pending and len(self.enemies)+len(self.jammers)<64 and self.spawn_clock<=0:
            kind,progress=self.pending.pop(0);self.spawn(kind,progress)
            self.spawn_clock=self.spawn_interval
        # Advance in the pre-movement order, applying both gate queues in place.
        # No proposed/accepted position dictionaries or extra enemy passes.
        gate0,gate1=self.map['gates'];walls=self.walls
        limit0=gate0 if walls[0]>0 else None
        limit1=gate1 if walls[1]>0 else None
        attacker0=attacker1=None
        now=self.time;enemy_data=ENEMIES
        if dt!=self.step_dt:
            self.step_dt=dt;self.steps=tuple(row[2]*dt for row in enemy_data)
        steps=self.steps
        length=self.map['length'];cleanup_needed=False
        for e in self.progress_order():
            ident=e[0];kind=ident%8;old=e[1]
            if e[5]>0:e[5]=max(0,e[5]-dt)
            if e[8]:
                for strength in tuple(e[8]):
                    if e[8][strength]<=now:del e[8][strength]
                e[4]=max(e[8],default=0)
                e[3]=max(e[8].values(),default=now)-now
            else:e[4]=0;e[3]=0.
            if e[5]>0:step=0.
            elif e[4]:step=enemy_data[kind][2]*(1-e[4]*(.5 if kind==5 else 1))*dt
            else:step=steps[kind]
            value=old+step
            if limit0 is not None and old<=gate0+.01 and value>=limit0:
                value=max(old,limit0)
                if attacker0 is None and value>=gate0-.01:attacker0=ident
                limit0=value-14
            elif limit1 is not None and old<=gate1+.01 and value>=limit1:
                value=max(old,limit1)
                if attacker1 is None and value>=gate1-.01:attacker1=ident
                limit1=value-14
            e[1]=value
            if value>=length or e[2]<=0:cleanup_needed=True
        if attacker0 is not None:walls[0]=max(0,walls[0]-enemy_data[attacker0%8][5]*dt)
        if attacker1 is not None:walls[1]=max(0,walls[1]-enemy_data[attacker1%8][5]*dt)
        due=[]
        for pad,t in enumerate(self.towers):
            self.scan_due[pad]-=dt
            if t:t[2]-=dt*(1.5 if pad in self.over else 1)
            if self.scan_due[pad]<=0:
                self.scan_due[pad]+=.1
                if t is not None and t[2]<=0 and pad not in jammed:due.append(pad)
        if due:
            armor_bonus=wave_stats(self.wave)[1]
            points={}
            self.points=points
            ordered=self.progress_order()
            for pad in due:
                t=self.towers[pad]
                index=t[0];price,amount,interval,radius,blast,slow,seconds=TOWERS[index]
                amount=tower_damage(t)
                x,y=self.map['pads'][pad]
                flyer=next((j for j in self.jammers if not j[5] and (j[1]-x)**2+(j[2]-y)**2<=radius*radius),None)
                if flyer:
                    flyer[4]-=amount;self.effect(index,(x,y-16),(flyer[1],flyer[2]))
                    t[2]=max(-.1,t[2])+interval
                    if flyer[4]<=0:self.jammers.remove(flyer);self.bank['cash']+=JAMMER_BOUNTY;self.kills+=1
                    continue
                target=next(enemies_in_range(ordered,points,x,y,radius,self.map_id),None)
                if target is None:continue
                tx,ty=points[target[0]]
                victims=list(enemies_in_range(ordered,points,x,y,radius,self.map_id)) if index in (6,10) else list(enemies_in_range(ordered,points,tx,ty,blast,self.map_id)) if blast else [target]
                for e in victims:
                    kind=enemy_kind(e[0]);e[2]-=damage(amount,ENEMIES[kind][3]+armor_bonus,e[5]>0,index==3)
                    if e[2]<=0:cleanup_needed=True
                    if slow:
                        e[8][slow]=self.time+seconds
                        e[4]=max(e[4],slow);e[3]=max(e[3],seconds)
                    if index==11:e[5]=max(e[5],seconds)
                    e[6]=self.time+.084
                    if index==6:e[7]=self.time+.3
                self.effect(index,(x,y-16),(tx,ty));t[2]=max(-.1,t[2])+interval
        # Escapes apply before the wave-clear check, including a simultaneous final hit.
        for e in self.enemies[:] if cleanup_needed else ():
            if e[1]>=length:
                kind=e[0]%8
                if not self.debug_wave:self.core=max(0,self.core-ENEMIES[kind][6])
                self.enemies.remove(e)
            elif e[2]<=0:
                kind=e[0]%8
                self.kills+=1;self.bank['cash']+=bounty(kind,self.wave);self.enemies.remove(e)
                point=self.points.get(e[0]) if due else None
                if point is None:point=enemy_xy(e[0],e[1],self.map_id)
                self.effect(-1,point,point)
                if kind==4:
                    for j in range(6):
                        if self.wave>10 and self.spawned+len(self.pending)>=130:break
                        if len(self.enemies)+len(self.jammers)<64:self.spawn(0,max(0,e[1]-j*3))
                        else:self.pending.insert(0,(0,max(0,e[1]-j*3)))
        if self.core<=0:self.phase='defeat'
        elif not self.enemies and not self.pending and not self.jammer_pending and not any(not j[5] for j in self.jammers):
            self.bank['cash']+=self.bonus
            if self.wave%10==0:self.banner_until=self.time+2
            self.phase='break';self.timer=40
            for p in self.players.values():p['ready']=False;p['menu']=''

    def snapshot(self):
        ps={}
        for pid,p in self.players.items():
            ps[pid]=[round(p['x'],1),round(p['y'],1),p['menu'],p['sel'],p['target'],int(p['ready']),p['msg'] if p['until']>self.time else '',p['slot']]
        enemies=[]
        health=[enemy_hp(k,self.wave) for k in range(6)]
        for e in self.enemies:
            row=[e[0],round(e[1],1)]
            kind=enemy_kind(e[0])
            if e[2]<health[kind] or e[3]>0 or e[5]>0 or e[6]>self.time or e[7]>self.time:
                row.extend([round(max(0,e[2]),1),2 if e[5]>0 else 1 if e[3]>0 else 3 if e[6]>self.time else 4 if e[7]>self.time else 0])
            enemies.append(row)
        return {'map':self.map_id,'banner':self.wave if self.time<self.banner_until else 0,'team':self.wave_players,'s':self.phase,'n':self.wave,'c':self.bank['cash'],'h':self.core,'tm':round(self.timer,1),
                'now':round(self.time,2),'p':ps,'e':enemies,'t':[t[:2]+[stars(t)] if t else None for t in self.towers],
                'oc':{str(pad):pid for pad,pid in self.over.items()},
                'j':[[j[0],j[3]] if j[5] else [j[0],round(j[1],1),round(j[2],1)] for j in self.jammers],
                'w':[round(h) for h in self.walls],'r':self.bank['r'],'m':self.markers,
                'fix':{str(w):r[0] for w,r in self.repairs.items()},'fx':self.effects,
                'stats':[int(self.elapsed),self.kills,self.spent]}
