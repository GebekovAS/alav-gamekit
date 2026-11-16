"""Visual album with looping attack studies; no combat, economy or networking."""
import os
import math
import alav as g

INK=(41,52,59)
CREAM=(255,244,214)
GOLD=(244,191,112)
TEAL=(64,185,167)
COLORS=[TEAL,(101,169,224),(220,153,88),(223,113,145)]
YARD=g.image('yard-play.png')
BUILD_STRIP=g.image('build-strip.png')
TOWERS=g.image('towers.png')
PLAYERS=g.image('players.png')
ENEMIES=g.image('enemies.png')
ICONS=g.image('icons.png')
CORE=g.image('core.png')
HEADS=g.image('heads.png')
FX=g.image('effects.png')
ATTACK_BG=g.image('attacks-bg.png')
PIN=g.image('pin-blue.png')
BROKEN=g.image('core-broken.png')
GHOST=g.image('reserve-blue.png')
BACKGROUNDS=[g.image(name+'-bg.png') for name in ('title','lobby','victory','defeat')]
LOCKED='COOP_SCREEN' in os.environ
screen=int(os.environ.get('COOP_SCREEN','0'))%11
elapsed=0.0

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
effect_calls=0
effect_queue=[]

def fx(name,x,y,frame=0,scale=1,angle=0):
    effect_queue.append((name,x,y,frame,scale,angle))
    if len(effect_queue)>FX_CAP:effect_queue.pop(0)

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
            ray('lightning',a,b,int(p*15)%3);fx('crackle',x,y,frame,.65)
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
            fx('frost',x,y,frame,.6)
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

def attacks():
    g.draw(ATTACK_BG,0,0)
    g.text('АТАКИ',20,10,GOLD,26)
    t=float(os.environ.get('COOP_TIME',elapsed))
    for index in range(12):
        col=index%3;row=index//3
        x=col*196+8;y=row*88+48
        radial=index in (6,10)
        tower(index//4,index%4+1,x+(65 if radial else 15),y+2,1.6)
        p=(t/1.2+index*.07)%1
        # Capture selects the material's most informative moment; live loops stay phased.
        if 'COOP_POSE' in os.environ:p=[.5,.5,.3,.15,.43,.43,.5,.78,.4,.4,.6,.8][index]
        style=0 if .66<p<.73 else 1 if index==6 else 2 if index==10 else -1
        target=x+(112 if radial else 150)
        if p<.92:
            if style>=0:affected_enemy(1,target,y+29,style,1.5)
            else:enemy(1,target,y+29,1.5)
        a=(x+53,y+25);b=(x+160,y+39)
        if index in (6,10):a=(x+84,y+28);b=(x+122,y+39)
        attack(index,a,b,p,.75 if index==7 else 1)
        if p>.92:fx('scrap',*b,3,.65)
        g.text(TOWER_NAMES[index//4][index%4],x+98,y+61,CREAM,16,'center')

def text(s,x,y,color=CREAM,size=20,align='left'):
    if size>=40:g.text(s,x+1,y+1,INK,size,align)
    g.text(s,x,y,color,size,align)

def icon(i,x,y,scale=1):
    g.draw(ICONS,x,y,scale,src=(i*16,0,16,16))

def tower(kind,level,x,y,scale=2):
    g.draw(TOWERS,x,y,scale,src=((kind*4+level-1)*24,0,24,24))

ENEMY_SIZES=[10,14,14,22,28,44]
TOWER_NAMES=[['Клепатель I','Клепатель II','Шквал','Молот'],
             ['Котёл I','Котёл II','Жаровня','Мортира'],
             ['Стужа I','Стужа II','Мороз','Ледокол']]
PRICES=[[50,60,130,140],[80,85,155,165],[70,75,145,155]]

def enemy(kind,x,y,scale=1):
    n=ENEMY_SIZES[kind]
    g.draw(ENEMIES,x,y,scale,src=(kind*44,0,n,n))

def hp(kind,x,y,fraction):
    n=ENEMY_SIZES[kind]
    g.rect(x,y-5,n,3,INK);g.rect(x,y-5,int(n*fraction),2,TEAL)

# Four packs of ten, each enemy has an individual persistent lateral offset.
# Progress is measured on the baked map centreline, including its turns.
ROUTE=[(44,146),(284,146),(284,236),(164,236),(164,296),(524,296)]

def lane(progress,offset):
    for a,b in zip(ROUTE,ROUTE[1:]):
        length=abs(b[0]-a[0])+abs(b[1]-a[1])
        if progress<=length:
            dx=(b[0]-a[0])/length;dy=(b[1]-a[1])/length
            return a[0]+dx*progress-dy*offset,a[1]+dy*progress+dx*offset
        progress-=length
    return ROUTE[-1]

CROWD=[]
for pack,start in enumerate([12,102,354,566]):
    for j in range(10):
        ident=pack*10+j
        offset=(ident*13+ident*ident*3)%21-10
        x,y=lane(start+j*7+[0,2,-1,3,-2,1,-1,2,-2,0][j],offset)
        CROWD.append((0,x-5,y-5))
for kind,progress,offset in [(1,85,-7),(2,181,6),(1,305,-5),(2,326,8),(1,506,-6),(2,530,6)]:
    x,y=lane(progress,offset);CROWD.append((kind,x-7,y-7))
assert len(CROWD)==46

def player(i,x,y,scale=2,badge=True):
    g.draw(PLAYERS,x,y,scale,src=(i*24,0,24,24))
    if badge:
        g.rect(x+18*scale,y+2*scale,18,20,INK)
        text(str(i+1),x+18*scale+9,y+2*scale,COLORS[i],16,'center')

def head(i,x,y):
    g.draw(HEADS,x,y,2.5,src=(i*16,0,16,16))

def hud():
    g.rect(0,0,600,32,INK)
    icon(0,14,7);text('5/10',38,5,GOLD,22)
    icon(1,241,7);text('240',265,5,GOLD,22)
    icon(2,482,7);text('82',506,5,TEAL,22)

def nav():
    g.rect(8,411,48,23,INK);text('< B',13,413,CREAM,16)
    g.rect(544,411,48,23,INK);text('A >',550,413,CREAM,16)


def world(plans=False,prompt=True):
    g.draw(YARD,0,32)
    for kind,x,y in CROWD:enemy(kind,x,y)
    if plans:
        enemy(4,458,282);hp(4,458,282,.8)
        enemy(3,359,285);hp(3,359,285,.6)
    else:
        enemy(5,234,124);hp(5,234,124,.72)
        enemy(3,359,285);hp(3,359,285,.6)
    hp(1,CROWD[40][1],CROWD[40][2],.55)
    # Deliberately staged busy wave, no damage simulation or networking.
    attack(2,(118,85),(152,146),.31)
    attack(3,(183,169),(255,145),.3)
    attack(7,(378,168),(282,233),.8)
    attack(5,(374,225),(339,294),.8)
    attack(9,(434,319),(370,295),.4)
    fx('flame',104,269,2,1.55)
    fx('roadfrost',238,296,2,.7)
    fx('wave',225,339,2,1.35)
    affected_enemy(0,164,282,1)
    affected_enemy(0,233,294,2)
    affected_enemy(3,359,285,0)
    fx('scrap',199,233,2,.6)
    for i,x,y in [(0,197,170),(1,421,205),(2,526,190),(3,40,326)]:
        text(str(i+1),x+45,y+4,COLORS[i],16,'center')
    if plans:
        g.draw(GHOST,200,60,2)
        g.rect(200,115,48,6,INK);g.rect(201,116,33,4,COLORS[1])
        # Blue pin points at the reserved pad, distinct from the ghost body.
        g.draw(PIN,212,34);text('2',224,35,INK,16,'center')
    elif prompt:
        icon(3,255,174,1.25)

def build():
    hud();world(prompt=False)
    g.rect(200,80,48,40,GOLD,fill=False)
    g.line(224,120,224,129,GOLD)
    g.draw(BUILD_STRIP,69,372)
    for k,price in enumerate([50,80,70]):
        text(str(price),69+k*155+86,379,GOLD,24)


def intermission():
    g.draw(BACKGROUNDS[1],0,0)
    icon(8,26,23,1.5);text('35',60,15,GOLD,40)
    icon(1,463,26,1.5);text('240',494,19,GOLD,30)
    # Wave 6 composition, matching TOWERS.md (two players).
    for k,count in enumerate([48,12,10,3,1]):
        x=34+k*110
        enemy(k,x,63,2 if k==0 else 1.5)
        text('x%d'%count,x+47,74,CREAM,20)
    for i in range(4):
        y=120+i*67
        g.rect(26,y,548,59,INK);g.rect(26,y,6,59,COLORS[i])
        text(str(i+1),49,y+17,COLORS[i],22,'center');head(i,66,y+9)
        if i==0:
            tower(0,2,139,y+4);icon(7,195,y+22);tower(0,4,227,y+4)
            price='140'
        elif i==1:
            tower(2,1,227,y+4);icon(7,170,y+22);price='70'
        elif i==2:
            # Any player can request sale of another player's tower in the plan.
            tower(1,2,139,y+4)
            g.rect(115,y+18,18,20,INK);text('2',124,y+18,COLORS[1],16,'center')
            icon(7,195,y+22);icon(1,242,y+17,1.5)
            text('70%',286,y+19,CREAM,18);price='+115'
        else:
            tower(2,2,139,y+4);icon(7,195,y+22);tower(2,4,227,y+4);price='155'
        icon(1,374,y+22);text(price,400,y+15,GOLD,26)
        if i!=1:icon(4,515,y+14,2)
        else:g.rect(518,y+18,24,24,COLORS[i],fill=False)


def branch():
    g.draw(BACKGROUNDS[1],0,0)
    tower(0,2,270,22,2.5)
    # The same selected II splits into two irreversible specialisations.
    for i,(name,price,counter) in enumerate([('Шквал',130,2),('Молот',140,3)]):
        x=40+i*270
        g.rect(x,108,250,274,GOLD if i==0 else INK)
        g.rect(x+2,110,246,270,(70,84,90) if i==0 else INK)
        tower(0,3+i,x+77,128,4)
        text(name,x+125,242,CREAM,28,'center')
        icon(1,x+83,282,1.25);text(str(price),x+112,277,GOLD,28)
        icon(0 if i==0 else 5,x+38,331,1.5)
        for n in range(3 if i==0 else 1):g.rect(x+71+n*7,340,4,9,GOLD)
        if i==1:g.line(x+42,352,x+59,332,CREAM)
        icon(7,x+120,335);enemy(counter,x+171,330,1.5)
    icon(3,285,393,1.5)


def tree():
    g.draw(BACKGROUNDS[1],0,0)
    g.text('БАШНИ',20,10,GOLD,26)
    for k in range(3):
        y=48+k*83
        for j,x in enumerate([20,164,321,465]):
            tower(k,j+1,x+25,y,1.5)
            g.text(TOWER_NAMES[k][j],x+60,y+39,CREAM,16,'center')
            g.text(('' if j==0 else '+')+str(PRICES[k][j]),x+60,y+58,GOLD,16,'center')
        icon(7,132,y+17);icon(7,285,y+17)
        g.line(307,y+24,313,y+24,GOLD);g.line(313,y+24,313,y-3,GOLD)
        g.line(313,y-3,513,y-3,GOLD);g.line(513,y-3,513,y,GOLD)
    g.line(20,305,580,305,(115,129,128))
    for k,name in enumerate(['Мелочь','Ходок','Бегунок','Панцирник','Носильщик','Босс']):
        x=[50,142,234,342,459,558][k]
        enemy(k,x-ENEMY_SIZES[k]/2,361-ENEMY_SIZES[k])
        g.text(name,x,367,CREAM,16,'center')
        g.text(str(ENEMY_SIZES[k]),x,388,GOLD,16,'center')

def stage(mode):
    if mode==0:
        g.draw(BACKGROUNDS[0],0,0)
        text('МЕДНЫЙ',300,26,CREAM,54,'center');text('ДОЗОР',300,80,GOLD,70,'center')
        g.draw(CORE,228,163,3)
        for i,x,y in [(0,105,276),(1,182,302),(2,358,302),(3,435,276)]:player(i,x,y,2.5,False)
        icon(3,284,387,2)
    elif mode==7:
        g.draw(BACKGROUNDS[1],0,0)
        text('СМЕНА',300,30,GOLD,46,'center')
        for i in range(4):
            x=38+i*134
            g.rect(x,126,122,238,INK)
            g.rect(x,126,122,5,COLORS[i])
            text(str(i+1),x+61,148,COLORS[i],26,'center')
            if i<3:
                player(i,x+25,202,3,False);icon(4,x+45,305,2)
            else:
                g.rect(x+31,216,60,65,(70,84,90),fill=False)
                text('...',x+61,224,COLORS[i],30,'center')
                text('ЖДЁМ',x+61,309,CREAM,18,'center')
        text('3 / 4',300,379,CREAM,24,'center')
    elif mode==5:
        g.draw(BACKGROUNDS[2],0,0)
        text('ПОБЕДА',300,29,INK,52,'center')
        g.draw(CORE,240,119,2.5)
        for i,x,y in [(0,91,250),(1,193,270),(2,344,270),(3,446,250)]:player(i,x,y,2.5,False)
        g.rect(154,354,292,42,INK)
        icon(0,170,367);text('10/10',196,360,GOLD,24)
        icon(8,306,367);text('12:18',332,360,CREAM,24)
    else:
        g.draw(BACKGROUNDS[3],0,0)
        text('ПОРАЖЕНИЕ',300,30,(246,180,183),48,'center')
        g.draw(BROKEN,228,142,3)
        for k,x,y,scale in [(1,151,173,1),(2,391,183,1),(1,180,284,1),(4,365,280,1),(5,278,302,1)]:enemy(k,x,y,scale)
        for start in [151,398]:
            for j in range(6):enemy(0,start+j*7,246+[0,6,-3,5,-1,7][j])
        icon(0,189,365);text('7/10',215,361,GOLD,24)
        icon(8,326,365);text('08:42',353,361,CREAM,24)
        icon(3,217,407,1.5);text('ЕЩЁ СМЕНУ?',250,407,CREAM,18)

def update(dt):
    global screen,elapsed
    elapsed+=dt
    if LOCKED:return
    if g.pressed('A'):screen=(screen+1)%11
    elif g.pressed('B'):screen=(screen-1)%11

def draw():
    global effect_calls
    effect_queue.clear()
    g.clear(INK)
    if screen in (0,5,6,7):stage(screen)
    elif screen==2:build()
    elif screen==4:intermission()
    elif screen==8:branch()
    elif screen==9:tree()
    elif screen==10:attacks()
    else:
        hud();world(screen==3)
    effect_calls=len(effect_queue)
    for name,x,y,frame,scale,angle in effect_queue:
        bx,by,w,h=FX_BOUNDS[name]
        g.draw(FX,x-w*scale/2,y-h*scale/2,scale,angle=angle,
               src=((frame%4)*128+bx,FX_ROWS[name]*128+by,w,h))
    nav()

g.run(update,draw,'Медный дозор')

