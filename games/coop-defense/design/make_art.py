"""Deterministic original pixel art; Pillow is a build-time dependency only."""
from pathlib import Path
import random
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parents[1] / 'assets'
OUT.mkdir(exist_ok=True)
P = ['#29343b','#46545a','#738180','#adb4a0','#eee2bd','#fff4d6',
     '#72825e','#899765','#98a570','#bac58b','#907655','#b99b70',
     '#d5ba86','#e3cb9b','#815342','#ad704b','#dc9958','#f4bf70',
     '#256b6c','#40b9a7','#a4eed4','#356d9b','#65a9e0','#b9def0',
     '#a4475c','#df7191','#f6b4b7','#b94e3c','#eb7650','#793e39']
# Share six near-equivalent material pigments: exactly 24 source colors.
for target, source in [(5,4),(9,8),(10,14),(13,4),(26,25),(29,14)]:
    P[target] = P[source]
assert len(set(P)) == 24
INK, STEEL, MID, LIGHT, CREAM, WHITE = P[:6]
COLORS = [P[19],P[22],P[16],P[25]]
ROAD = [(22,57),(142,57),(142,102),(82,102),(82,132),(262,132)]
MAP = ['..................','..1...2...........','S=======+.........','....3...=..4......','........|.........','....+====..5......','..6.=.............','....+=======|===C.','......7......8....','..................']

def save(im,name):
    im.save(OUT / name)

def terrain():
    rng=random.Random(49)
    im=Image.new('RGB',(300,204),P[7]); d=ImageDraw.Draw(im)
    for y in range(0,204,6):
        for x in range(0,300,6):
            if rng.random()<.32: d.rectangle((x,y,x+5,y+5),fill=rng.choice([P[6],P[7],P[8]]))
    d.line(ROAD,fill=INK,width=25, joint='curve')
    d.line(ROAD,fill=P[16],width=23, joint='curve')
    d.line(ROAD,fill=P[14],width=21, joint='curve')
    for a,b in zip(ROAD,ROAD[1:]):
        if a[1]==b[1]:
            for off in [-6,6]: d.line((a[0],a[1]+off,b[0],b[1]+off),fill=P[15],width=2)
        else:
            for off in [-6,6]: d.line((a[0]+off,a[1],b[0]+off,b[1]),fill=P[15],width=2)
    # Direction chevrons point along the lane, never onto a build plate.
    for x,y,direction in [(53,57,1),(108,57,1),(113,102,-1),(195,132,1),(232,132,1)]:
        d.line((x-2*direction,y-2,x+direction,y,x-2*direction,y+2),fill=P[17],width=1)
    # Entrance arch, outside the traffic lane.
    for y in [42,68]:
        d.rectangle((13,y,23,y+5),fill=INK);d.rectangle((15,y+1,21,y+3),fill=P[16])
    d.rectangle((14,47,16,67),fill=INK)
    d.rectangle((16,48,17,66),fill=P[19])
    # Raised light stone plates: a shared position list in full-screen coordinates.
    for cx,cy in [(104,100),(224,100),(164,190),(374,195),(374,250),(104,270),(225,355),(434,346)]:
        x,y=cx//2,(cy-32)//2
        d.rectangle((x-12,y-9,x+12,y+11),fill=P[6])
        d.polygon([(x-11,y-8),(x+9,y-8),(x+11,y-6),(x+11,y+8),(x-11,y+8)],fill=INK)
        d.rectangle((x-10,y-7,x+10,y+5),fill=LIGHT)
        d.line((x-9,y-7,x+9,y-7),fill=CREAM)
        d.rectangle((x-8,y-5,x+8,y+3),fill=MID)
        d.line((x-3,y-1,x+3,y-1),fill=P[20],width=2)
        d.line((x,y-4,x,y+2),fill=P[20],width=2)
    # Dress the edges; the route and assembly pads remain clear.
    for x,y in [(8,15),(54,15),(100,12),(174,25),(204,48),(271,25),(278,83),(194,176),(108,182),(20,173),(38,94),(214,108),(248,181)]:
        d.ellipse((x,y+5,x+12,y+10),fill=P[6])
        for dx,dy in [(1,1),(5,-1),(9,3)]:
            d.line((x+dx,y+dy+5,x+dx-1,y+dy),fill=P[6],width=2)
            d.point((x+dx,y+dy),fill=P[9])
    for x,y in [(8,180),(275,162),(225,24),(180,78),(50,172)]:
        d.ellipse((x-2,y+5,x+10,y+9),fill=P[6]);d.polygon([(x,y+5),(x+2,y),(x+7,y-1),(x+10,y+5)],fill=STEEL)
        d.line((x+2,y,x+7,y-1),fill=LIGHT)
    for x,y in [(252,16),(264,24),(20,147)]:
        d.rectangle((x+1,y+3,x+14,y+15),fill=P[6]); d.rectangle((x,y,x+12,y+12),fill=INK)
        d.rectangle((x+1,y+1,x+11,y+10),fill=P[15]);d.rectangle((x+2,y+2,x+10,y+3),fill=P[17]);d.line((x+2,y+4,x+10,y+10),fill=P[14],width=2)
    for x,y in [(10,35),(182,145),(285,112)]:
        d.ellipse((x-4,y+15,x+8,y+19),fill=P[6]);d.rectangle((x,y,x+2,y+16),fill=INK)
        d.rectangle((x-3,y-3,x+5,y+2),fill=INK);d.rectangle((x-2,y-2,x+4,y+1),fill=P[17])
    # Industrial pipe along the northern fence.
    d.line((8,5,290,5),fill=INK,width=5);d.line((8,4,290,4),fill=MID,width=3)
    for x in range(14,291,24):d.rectangle((x,2,x+2,7),fill=STEEL)
    full=im.resize((600,408),Image.Resampling.NEAREST);fd=ImageDraw.Draw(full)
    save(full.copy(),'yard-open.png')
    for x,y,vertical in [(279,152,True),(389,259,False)]:
        w,h=(10,38) if vertical else (42,10)
        fd.rectangle((x+3,y+5,x+3+w-1,y+5+h-1),fill=INK)
        fd.rectangle((x,y,x+w-1,y+h-1),fill=LIGHT)
        for n in range(3):
            xx=x+2 if vertical else x+3+n*13
            yy=y+3+n*13 if vertical else y+2
            fd.rectangle((xx,yy,xx+5,yy+5),fill=P[17])
    save(full,'yard.png')

def base():
    im=Image.new('RGBA',(24,24));d=ImageDraw.Draw(im)
    d.ellipse((2,18,22,23),fill=(41,52,59,100))
    return im,d

def tower(kind,level):
    im,d=base()
    accent=[P[16],P[28],P[22]][kind]
    d.polygon([(3,18),(7,14),(18,14),(22,18),(21,22),(3,22)],fill=INK)
    d.rectangle((5,18,19,20),fill=STEEL);d.line((5,18,19,18),fill=LIGHT)
    d.rectangle((8,11,16,17),fill=INK);d.rectangle((9,12,15,17),fill=accent)
    if level>=2:
        for x in [4,18]:
            d.rectangle((x,12,x+2,19),fill=MID);d.point((x,13),fill=CREAM)
        d.rectangle((7,20,17,21),fill=accent)
    if kind==0:
        if level<=2:
            d.rectangle((5,6,17,12),fill=INK);d.rectangle((6,7,16,10),fill=accent)
            for y in ([5] if level==1 else [3,7]):
                d.rectangle((14,y,23,y+2),fill=INK);d.line((15,y,22,y),fill=LIGHT)
        elif level==3: # Copper coil, porcelain insulator, forked contact.
            d.rectangle((4,7,12,17),fill=INK)
            d.rectangle((5,8,11,16),fill=P[15])
            for y in [8,11,14]:
                d.line((4,y,12,y),fill=P[17],width=2)
                d.point((5,y),fill=CREAM)
            d.rectangle((7,3,10,7),fill=LIGHT)
            d.line((6,3,12,3),fill=CREAM,width=2)
            d.line((11,5,19,5,19,2),fill=P[22],width=2)
            d.line((15,5,22,8,23,5),fill=P[23],width=2)
            d.rectangle((14,12,20,16),fill=STEEL)
            d.point((18,13),fill=P[20])
        else: # Twin rail shoes, open glowing channel, recoil piston.
            d.rectangle((1,10,8,15),fill=INK)
            d.rectangle((2,11,7,13),fill=P[16])
            d.polygon([(8,10),(18,1),(22,1),(13,12)],fill=INK)
            d.line((9,9,18,2),fill=LIGHT,width=2)
            d.line((12,12,22,4),fill=P[16],width=3)
            d.line((11,9,20,2),fill=P[23],width=1)
            for x,y in [(10,7),(13,4),(16,1)]:
                d.rectangle((x,y,x+1,y+2),fill=CREAM)
            d.rectangle((6,13,15,16),fill=STEEL)
            d.line((7,14,14,14),fill=LIGHT)
    elif kind==1:
        if level<=2:
            d.ellipse((5,5,19,17),fill=INK);d.ellipse((7,7,17,15),fill=P[15])
            d.rectangle((7,5,17,8),fill=accent);d.rectangle((10,9,14,13),fill=P[17])
            if level==2:
                for x in [3,19]:d.rectangle((x,3,x+2,13),fill=INK);d.line((x+1,4,x+1,10),fill=LIGHT)
        elif level==3: # Brazier: open flame crown.
            d.ellipse((2,9,22,18),fill=INK);d.rectangle((5,10,19,15),fill=accent)
            for x,h in [(5,5),(10,0),(16,3)]:
                d.polygon([(x,12),(x-1,h+5),(x+2,h),(x+5,h+7),(x+4,12)],fill=P[28])
                d.line((x+2,h+5,x+2,11),fill=P[17],width=2)
        else: # Mortar: oversized angled cup with a visible dark mouth.
            d.polygon([(6,12),(8,3),(18,0),(23,6),(17,16)],fill=INK)
            d.polygon([(8,11),(10,4),(18,2),(20,6),(15,14)],fill=accent)
            d.ellipse((9,0,22,7),fill=LIGHT);d.ellipse((11,1,20,5),fill=INK)
    else:
        if level<=2:
            d.polygon([(12,1),(19,8),(12,14),(5,8)],fill=INK)
            d.polygon([(12,3),(17,8),(12,11),(7,8)],fill=accent);d.line((12,3,12,10),fill=P[23])
            if level==2:
                for x in [3,19]:d.rectangle((x,5,x+2,15),fill=accent)
        elif level==3: # Frost: radial snowflake antenna.
            for a,b in [((12,0),(12,16)),((3,4),(21,12)),((3,12),(21,4))]:
                d.line((*a,*b),fill=INK,width=4);d.line((*a,*b),fill=accent,width=2)
            d.rectangle((10,6,14,10),fill=P[23])
        else: # Icebreaker: split tall crystalline jaws.
            for x,y in [(4,4),(14,0)]:
                d.polygon([(x,14),(x, y+5),(x+4,y),(x+7,y+5),(x+5,15)],fill=INK)
                d.polygon([(x+2,12),(x+2,y+5),(x+4,y+2),(x+5,y+6)],fill=P[23])
            d.rectangle((9,12,16,15),fill=accent)
    return im

def player(i):
    im,d=base();c=COLORS[i]
    d.ellipse((1,16,23,23),fill=c);d.ellipse((4,17,20,21),fill=INK)
    d.rectangle((7,15,10,20),fill=INK);d.rectangle((14,15,17,20),fill=INK)
    d.rectangle((6,10,18,16),fill=INK);d.rectangle((7,11,17,15),fill=c);d.rectangle((7,11,9,15),fill=[P[18],P[21],P[15],P[24]][i])
    d.rectangle((4,11,6,16),fill=INK);d.rectangle((18,11,20,16),fill=INK)
    d.rectangle((7,3,17,10),fill=INK);d.rectangle((8,5,16,9),fill=P[12]);d.rectangle((9,6,16,7),fill=INK)
    d.rectangle((6,3,18,5),fill=INK);d.rectangle((8,1,16,4),fill=INK);d.rectangle((8,2,16,4),fill=c)
    d.line((9,2,14,2),fill=WHITE);d.point((8,3),fill=[P[18],P[21],P[15],P[24]][i]);d.rectangle((10,11,12,14),fill=CREAM)
    return im

ENEMY_SIZES=[10,14,14,22,28,44]

def enemy(k):
    n=ENEMY_SIZES[k]
    im=Image.new('RGBA',(n,n));d=ImageDraw.Draw(im)
    if k==0:
        d.polygon([(0,4),(3,1),(7,1),(9,4),(8,7),(6,7),(7,9),(5,9),(4,7),(2,9),(0,9)],fill=INK)
        d.rectangle((2,3,7,5),fill=P[14]);d.point((7,3),fill=P[16])
    elif k==1:
        d.rectangle((2,2,11,9),fill=INK);d.rectangle((3,3,10,7),fill=P[27])
        d.line((4,3,9,3),fill=P[28]);d.rectangle((4,5,10,5),fill=INK)
        for x in [3,9]:d.rectangle((x,10,x+2,13),fill=INK)
    elif k==2:
        d.polygon([(0,10),(6,5),(10,0),(13,2),(11,8),(7,10),(3,13),(0,13)],fill=INK)
        d.polygon([(4,9),(9,3),(11,2),(10,7)],fill=P[28]);d.line((8,10,13,12),fill=INK,width=2)
    elif k==3:
        d.rectangle((0,10,21,20),fill=INK);d.polygon([(1,10),(5,2),(16,2),(20,10)],fill=INK)
        d.polygon([(3,9),(6,3),(15,3),(18,9)],fill=LIGHT);d.rectangle((2,11,19,17),fill=MID)
        d.rectangle((5,12,17,14),fill=INK);d.line((7,12,15,12),fill=P[28])
        for x in [2,17]:d.rectangle((x,18,x+2,21),fill=INK)
    elif k==4:
        d.rectangle((2,7,25,23),fill=INK);d.rectangle((4,9,23,21),fill=P[15])
        d.rectangle((1,3,26,13),outline=LIGHT,width=2)
        for x,y in [(3,1),(11,0),(19,2),(7,7),(16,7)]:
            d.rectangle((x,y,x+5,y+4),fill=INK);d.point((x+4,y+1),fill=P[28])
        d.rectangle((9,16,19,18),fill=INK);d.line((11,16,17,16),fill=P[17])
        for x in [3,20]:d.rectangle((x,22,x+4,27),fill=INK)
    else:
        d.rectangle((3,13,40,36),fill=INK);d.rectangle((5,15,38,33),fill=P[16])
        d.polygon([(7,14),(13,6),(31,6),(37,14)],fill=INK)
        d.rectangle((12,9,32,22),fill=P[27]);d.line((14,10,30,10),fill=P[28],width=2)
        for x in [3,35]:
            d.rectangle((x,0,x+5,17),fill=INK);d.rectangle((x+2,2,x+3,11),fill=P[17])
        d.rectangle((14,15,30,18),fill=INK);d.line((17,15,27,15),fill=P[17],width=2)
        for x in [4,13,26,35]:d.rectangle((x,35,x+4,43),fill=INK)
    return im

def icons():
    sheet=Image.new('RGBA',(16*12,16))
    for i in range(12):
        im=Image.new('RGBA',(16,16));d=ImageDraw.Draw(im)
        if i==0:
            for x,h in [(2,5),(6,9),(10,13)]:d.rectangle((x,14-h,x+2,14),fill=P[17])
        elif i==1:
            d.ellipse((2,1,13,14),fill=INK);d.ellipse((3,2,12,12),fill=P[17]);d.line((7,4,7,10),fill=P[14],width=2)
        elif i==2:
            d.polygon([(1,5),(4,2),(7,2),(8,4),(10,2),(13,2),(15,5),(14,9),(8,15),(2,9)],fill=P[20])
        elif i==3:
            d.ellipse((0,0,15,15),fill=CREAM);d.ellipse((1,1,14,14),fill=INK)
            d.line((4,11,7,4,8,4,11,11),fill=WHITE,width=2);d.line((5,9,10,9),fill=WHITE)
        elif i==4:
            d.line((2,8,6,12,14,3),fill=P[20],width=3)
        elif i==5:
            d.polygon([(2,1),(13,1),(13,8),(7,15),(2,8)],fill=INK);d.rectangle((4,3,11,7),fill=COLORS[2])
        elif i==6:
            d.line((3,13,12,4),fill=LIGHT,width=4);d.arc((7,0,15,8),0,280,fill=LIGHT,width=3)
        elif i==7:
            d.line((2,8,13,8),fill=CREAM,width=2);d.line((9,4,13,8,9,12),fill=CREAM,width=2)
        elif i==8:
            d.ellipse((1,1,14,14),outline=CREAM,width=2);d.line((8,3,8,8,11,10),fill=CREAM,width=2)
        elif i==9:
            d.polygon([(8,1),(15,8),(11,8),(11,14),(5,14),(5,8),(1,8)],fill=P[17])
        elif i==10:
            d.rectangle((2,2,14,14),outline=CREAM,width=2);d.line((4,10,7,7,10,10,12,5),fill=CREAM,width=2)
        else:
            d.ellipse((1,1,14,14),fill=CREAM);d.rectangle((7,3,8,9),fill=INK);d.rectangle((7,11,8,12),fill=INK)
        sheet.alpha_composite(im,(i*16,0))
    save(sheet,'icons.png')

def core(dead=False):
    im=Image.new('RGBA',(48,48));d=ImageDraw.Draw(im)
    d.ellipse((3,36,46,46),fill=(41,52,59,100))
    d.polygon([(5,35),(9,20),(14,20),(14,40),(4,40)],fill=INK);d.polygon([(35,20),(40,20),(45,40),(34,40)],fill=INK)
    d.ellipse((7,4,41,38),fill=INK);d.ellipse((9,5,39,35),fill=P[14]);d.ellipse((11,6,37,32),fill=P[16]);d.ellipse((13,8,35,30),fill=INK)
    d.ellipse((15,9,33,29),fill=P[29] if dead else P[18]);d.ellipse((17,10,31,26),fill=P[14] if dead else P[19])
    d.polygon([(24,11),(29,18),(24,26),(19,18)],fill=P[27] if dead else P[20])
    for x,y in [(11,12),(34,12),(11,28),(34,28)]:d.rectangle((x,y,x+2,y+2),fill=CREAM)
    d.rectangle((17,32,31,37),fill=INK);d.rectangle((19,33,29,35),fill=P[15]);d.line((7,38,13,38),fill=LIGHT);d.line((36,38,42,38),fill=LIGHT)
    if dead:
        d.line((24,7,21,14,26,18,21,24,24,31),fill=INK,width=2)
        d.line((12,24,18,21,21,24),fill=INK,width=2)
        d.rectangle((10,33,14,35),fill=P[14])
    save(im,'core-broken.png' if dead else 'core.png')

terrain();icons();core();core(True)
sheet=Image.new('RGBA',(24*12,24))
for k in range(3):
    for level in range(1,5):sheet.alpha_composite(tower(k,level),((k*4+level-1)*24,0))
save(sheet,'towers.png')
sheet=Image.new('RGBA',(24*4,24))
for i in range(4):sheet.alpha_composite(player(i),(i*24,0))
save(sheet,'players.png')
sheet=Image.new('RGBA',(44*6,44))
for i in range(6):sheet.alpha_composite(enemy(i),(i*44,0))
save(sheet,'enemies.png')
# Reservation silhouette keeps its exact tower shape and transparent player tint.
ghost=tower(2,1)
for y in range(24):
    for x in range(24):
        r,g,b,a=ghost.getpixel((x,y))
        if a:ghost.putpixel((x,y),(101,169,224,128 if a==255 else 35))
save(ghost,'reserve-blue.png')
assert Image.open(OUT/'yard.png').size==(600,408)

# Separate atmospheric plates; no gameplay pads behind the menu compositions.
for name,top,bottom in [('title',(23,38,44),(48,67,61)),('lobby',(34,53,58),(55,76,77)),('victory',(97,139,122),(174,185,126)),('defeat',(50,30,36),(76,48,46))]:
    im=Image.new('RGB',(300,220));d=ImageDraw.Draw(im)
    for y in range(220):
        t=y/219
        c=tuple(int(top[j]*(1-t)+bottom[j]*t) for j in range(3))
        d.line((0,y,300,y),fill=c)
    if name=='victory':
        for x in range(-150,451,70):
            d.polygon([(150,150),(x,0),(x+22,0)],fill=(183,197,139))
    d.ellipse((-50,136,350,340),fill={'title':(37,55,54),'lobby':(45,65,68),'victory':(119,155,120),'defeat':(60,39,42)}[name])
    if name in ('title','victory'):
        for r in range(63,12,-1):
            col=(43+(63-r)//3,78+(63-r),72+(63-r)) if name=='title' else (126,166+(63-r)//2,130)
            d.ellipse((150-r,128-r,150+r,128+r),fill=col)
    if name=='title':
        for x,y in [(4,145),(267,154),(18,95),(273,105)]:
            sil=enemy(0)
            sil.putdata([(17,28,33,a) for r,g,b,a in sil.get_flattened_data()])
            im.paste(sil,(x,y),sil)
    if name=='victory':
        rng=random.Random(5)
        for _ in range(55):
            x,y=rng.randrange(16,284),rng.randrange(45,192)
            d.rectangle((x,y,x+1,y+2),fill=rng.choice([P[17],P[20],CREAM]))
    save(im.resize((600,440),Image.Resampling.NEAREST),name+'-bg.png')

portraits=Image.new('RGBA',(64,16))
for i,c in enumerate(COLORS):
    im=Image.new('RGBA',(16,16));d=ImageDraw.Draw(im)
    d.rectangle((3,6,12,13),fill=INK);d.rectangle((4,7,11,12),fill=P[12])
    d.rectangle((3,2,12,6),fill=INK);d.rectangle((4,2,11,5),fill=c)
    d.line((5,2,9,2),fill=CREAM);d.rectangle((1,5,14,7),fill=INK);d.line((2,5,13,5),fill=c)
    d.rectangle((5,8,6,9),fill=INK);d.rectangle((9,8,10,9),fill=INK)
    d.line((6,12,9,12),fill=P[15]);d.rectangle((2,14,13,15),fill=c)
    portraits.alpha_composite(im,(i*16,0))
save(portraits,'heads.png')

pin=Image.new('RGBA',(24,28));d=ImageDraw.Draw(pin)
d.polygon([(0,0),(23,0),(23,18),(12,27),(0,18)],fill=INK)
d.polygon([(2,2),(21,2),(21,17),(12,24),(2,17)],fill=COLORS[1])
save(pin,'pin-blue.png')

# Static build-strip art; prices stay in ALAV's font in main.py.
strip=Image.new('RGBA',(458,62));d=ImageDraw.Draw(strip)
coins=Image.open(OUT/'icons.png').crop((16,0,32,16))
for k in range(3):
    x=k*155
    d.rectangle((x,0,x+147,61),fill=P[17] if k==0 else INK)
    d.rectangle((x+2,2,x+145,59),fill=STEEL if k==0 else INK)
    strip.alpha_composite(tower(k,1).resize((48,48),Image.Resampling.NEAREST),(x+8,6))
    strip.alpha_composite(coins,(x+64,11))
    d.rectangle((x+65,43,x+128,46),fill=MID)
    d.rectangle((x+65,43,x+65+[45,36,56][k]-1,46),fill=[P[17],P[28],P[22]][k])
save(strip,'build-strip.png')



# Attack atlas: four frames per material, 128px cells, same source pigments.
def effects():
    import math
    names=['rivet','muzzle','spark','lightning','crackle','rail','chips','slag',
           'shadow','splash','flame','shell','blast','laser','laser2','frost',
           'wave','roadfrost','spike','ice','scrap']
    atlas=Image.new('RGBA',(512,24*128))
    def rgba(c,a):
        return tuple(bytes.fromhex(c[1:]))+(a,)
    for row,name in enumerate(names):
        for f in range(4):
            im=Image.new('RGBA',(128,128));d=ImageDraw.Draw(im)
            if name=='rivet':
                d.polygon([(54,62),(68,60),(73,64),(68,68),(54,66)],fill=INK)
                d.rectangle((56,62,68,65),fill=P[17]);d.line((58,62,67,62),fill=CREAM,width=2)
            elif name in ('muzzle','spark','crackle','frost'):
                c=P[23] if name in ('crackle','frost') else P[17]
                r=12-f*2
                for j in range(6):
                    a=j*math.pi/3+f*.3
                    x=64+int(math.cos(a)*r);y=64+int(math.sin(a)*r)
                    d.line((64,64,x,y),fill=c,width=3)
                d.rectangle((61,61,67,67),fill=CREAM)
            elif name=='lightning':
                variants=[[(16,64),(35,59),(43,70),(61,55),(71,68),(91,58),(112,64)],
                          [(16,64),(31,72),(48,58),(64,72),(80,57),(95,67),(112,64)],
                          [(16,64),(37,54),(51,69),(71,60),(83,73),(101,59),(112,64)]]
                pts=variants[f%3]
                d.line(pts,fill=rgba(P[22],100),width=9)
                d.line(pts,fill=P[22],width=5);d.line(pts,fill=CREAM,width=2)
                d.line((61,pts[3][1],72,45,82,49),fill=P[23],width=2)
            elif name in ('rail','laser','laser2'):
                c=P[17] if name=='rail' else P[22]
                width=5 if name=='rail' else 5 if name=='laser' else 9
                alpha=230-f*50 if name=='rail' else 210
                d.line((16,64,112,64),fill=rgba(c,alpha//3),width=width+(2 if name=='rail' else 6))
                d.line((16,64,112,64),fill=rgba(c,alpha),width=width)
                d.line((16,64,112,64),fill=rgba(CREAM,alpha),width=3 if name!='laser' else 2)
                if name=='rail':d.polygon([(99,60),(115,64),(99,68)],fill=CREAM)
                if name=='rail':
                    for x in [30,53,80]:d.rectangle((x,60-f,x+5,61-f),fill=rgba(P[17],alpha))
            elif name=='chips':
                d.ellipse((44-f*3,58-f,84+f*3,72+f),outline=rgba(P[12],180-f*30),width=3)
                for j in range(7):
                    a=j*1.7;r=10+f*4;x=64+int(math.cos(a)*r);y=60+int(math.sin(a)*r)
                    d.polygon([(x,y),(x+5,y-3),(x+7,y+2),(x+1,y+3)],fill=LIGHT if j%2 else INK)
            elif name in ('slag','shell'):
                if name=='slag':
                    d.ellipse((54,54,74,74),fill=rgba(P[28],70))
                    d.polygon([(54,62),(59,55),(69,57),(74,65),(67,73),(57,70)],fill=P[28])
                    d.ellipse((58,58,68,65),fill=P[17]);d.rectangle((60,59,65,61),fill=CREAM)
                else:
                    d.polygon([(57,70),(54,61),(61,52),(68,53),(74,62),(67,72)],fill=INK)
                    d.polygon([(57,61),(62,55),(67,56),(71,62),(65,69)],fill=P[12])
                    d.line((57,63,66,68),fill=P[28],width=3)
            elif name=='shadow':
                d.ellipse((53-f*2,62-f,75+f*2,68+f),fill=rgba(INK,90+f*20))
            elif name=='splash':
                d.ellipse((40-f*3,58,88+f*3,76),fill=rgba(P[28],180-f*20))
                d.ellipse((48-f*2,60,79+f*2,70),fill=P[28])
                d.line((50,65,61,62,72,67,81,64),fill=P[17],width=3)
                for x,y in [(44,52),(81,48),(91,59)]:d.rectangle((x,y+f*3,x+3,y+4+f*3),fill=P[17])
            elif name in ('flame','wave'):
                r=45 if name=='flame' else 54
                color=P[28] if name=='flame' else P[23]
                d.ellipse((64-r,64-r*.64,64+r,64+r*.64),outline=rgba(color,110 if name=='flame' else 55),width=7)
                d.ellipse((64-r,64-r*.64,64+r,64+r*.64),outline=color,width=2 if name=='flame' else 1)
                for j in range(14):
                    a=j*math.pi/7;x=64+int(math.cos(a)*r);y=64+int(math.sin(a)*r*.64)
                    if name=='flame':
                        h=7+(j+f)%3*2
                        d.polygon([(x-4,y+2),(x-3,y-5),(x+1,y-h),(x+5,y+2)],fill=P[28])
                        d.line((x,y,x+1,y-h+5),fill=P[17],width=2)
                    else:d.line((x-2,y-1,x+2,y+1),fill=P[23],width=1)
            elif name=='blast':
                r=22+f*5
                d.ellipse((64-r,65-r//2,64+r,70+r//2),outline=rgba(P[12],170-f*25),width=3)
                for dx,dy,rr in [(-20,-10,12),(17,-14,15),(0,-25,16)]:
                    d.ellipse((64+dx-rr,64+dy-rr-f*3,64+dx+rr,64+dy+rr),fill=rgba(STEEL,180-f*25))
                d.polygon([(37,65),(47,54),(44,45),(60,51),(66,38),(74,52),(87,48),(82,60),(94,68),(72,78),(52,75)],fill=rgba(P[28],245-f*35))
                d.polygon([(48,64),(59,58),(64,47),(70,60),(82,66),(67,72)],fill=P[17])
                d.ellipse((58,59,71,70),fill=CREAM)
            elif name=='roadfrost':
                for j in range(8):
                    x=38+j*7;y=63+(j%3)*4
                    d.line((x-4,y,x+4,y),fill=rgba(P[23],170),width=2)
                    d.line((x,y-4,x,y+4),fill=P[22],width=2)
            elif name=='spike':
                d.polygon([(47,60),(65,56),(82,64),(65,72),(47,68),(58,64)],fill=P[21])
                d.polygon([(51,61),(66,58),(82,64),(61,65)],fill=P[23])
                d.line((54,62,73,63),fill=CREAM,width=2)
            elif name=='ice':
                d.polygon([(48,48),(72,46),(82,56),(80,79),(51,81),(45,71)],fill=rgba(P[22],130),outline=P[23],width=2)
                d.line((49,50,75,76,79,63),fill=CREAM,width=2)
                d.line((52,77,56,65,50,58),fill=P[23],width=2)
            elif name=='scrap':
                for j in range(8):
                    a=j*2.4;r=5+f*4;x=64+int(math.cos(a)*r);y=64+int(math.sin(a)*r)
                    d.rectangle((x,y,x+4,y+3),fill=rgba(MID if j%2 else P[16],240-f*40))
            atlas.alpha_composite(im,(f*128,row*128))
    # Exact enemy silhouettes for short hit flash / burn / slow tints.
    for style,c in enumerate([CREAM,P[28],P[22]]):
        for k in range(6):
            im=enemy(k);pixels=[]
            tint=tuple(bytes.fromhex(c[1:]))
            for r,g,b,a in im.get_flattened_data():
                pixels.append((*tint,a) if style==0 else (int(r*.25+tint[0]*.75),int(g*.25+tint[1]*.75),int(b*.25+tint[2]*.75),a))
            im.putdata(pixels);atlas.alpha_composite(im,(k*44,(21+style)*128))
    save(atlas,'effects.png')
effects()

# Static mockup scenery shares one opaque draw; attacks and crowd stay separate.
yard=Image.open(OUT/'yard.png').convert('RGBA')
for k,level,x,y in [(0,3,80,70),(0,4,140,156),(1,4,350,155),
                    (2,3,201,315),(1,2,350,212),(2,2,410,308),(1,3,80,239)]:
    yard.alpha_composite(tower(k,level).resize((48,48),Image.Resampling.NEAREST),(x,y-32))
yard.alpha_composite(Image.open(OUT/'core.png').resize((79,79),Image.Resampling.NEAREST),(484,257-32))
# Four stationary repairers and their dark badge plates are scenery too.
yd=ImageDraw.Draw(yard)
for i,x,y in [(0,197,170),(1,421,205),(2,526,190),(3,40,326)]:
    yard.alpha_composite(player(i).resize((48,48),Image.Resampling.NEAREST),(x,y-32))
    yd.rectangle((x+36,y-28,x+53,y-9),fill=INK)
save(yard.convert('RGB'),'yard-play.png')
reference=Image.open(OUT/'lobby-bg.png').convert('RGB');rd=ImageDraw.Draw(reference)
for i in range(12):
    x=i%3*196+8;y=i//3*88+48
    rd.rectangle((x+8,y+29,x+183,y+52),fill=P[14])
    rd.rectangle((x+8,y+29,x+183,y+30),fill=P[15])
save(reference,'attacks-bg.png')

print('Original art generated:',len(list(OUT.glob('*.png'))),'PNGs')

# Store icon: a real crop of the existing core and original copper tower art.
icon=Image.open(OUT/'title-bg.png').resize((128,128),Image.Resampling.NEAREST).convert('RGBA')
icon.alpha_composite(Image.open(OUT/'core.png').resize((80,80),Image.Resampling.NEAREST),(24,13))
icon.alpha_composite(tower(0,3).resize((48,48),Image.Resampling.NEAREST),(8,75))
icon.alpha_composite(player(0).resize((48,48),Image.Resampling.NEAREST),(76,75))
icon.save(OUT.parent/'icon.png')

# Runtime-only previews retain every approved tower silhouette.
ghosts=Image.open(OUT/'towers.png').convert('RGBA')
ghosts.putdata([(101,169,224,a//2) for r,g,b,a in ghosts.get_flattened_data()])
save(ghosts,'reservations.png')
pins=Image.new('RGBA',(96,28))
for i,c in enumerate(COLORS):
    im=Image.open(OUT/'pin-blue.png').convert('RGBA')
    rgb=tuple(bytes.fromhex(c[1:]))
    im.putdata([(*rgb,a) if (r,g,b)==(101,169,224) else (r,g,b,a) for r,g,b,a in im.get_flattened_data()])
    pins.alpha_composite(im,(i*24,0))
save(pins,'pins.png')

# All geometry comes from the same data as authoritative rules.
import importlib.util
spec=importlib.util.spec_from_file_location('map_art_data',OUT.parent/'maps.py')
map_data=importlib.util.module_from_spec(spec);spec.loader.exec_module(map_data)
previews=Image.new('RGB',(480,82))
for ident,m in enumerate(map_data.MAPS):
    if ident==0:
        full=Image.open(OUT/'yard-open.png').convert('RGB')
    else:
        rng=random.Random(490+ident)
        ground=[P[7],P[6],P[0],P[3]][ident]
        im=Image.new('RGB',(300,204),ground);d=ImageDraw.Draw(im)
        road=[(x//2,(y-32)//2) for x,y in m['route']]
        def clear_ground(x,y,r=14):
            for a,b in zip(road,road[1:]):
                if min(a[0],b[0])-r<=x<=max(a[0],b[0])+r and min(a[1],b[1])-r<=y<=max(a[1],b[1])+r:return False
            return all(abs(x-px/2)>r or abs(y-(py-32)/2)>r for px,py in m['pads']+m['spawns']+[m['core']])
        # Sparse material flecks and recognizable scenery on free grass only.
        for y in range(10,197,5):
            for x in range(8,293,5):
                if clear_ground(x,y,6) and rng.random()<.25:
                    d.rectangle((x,y,x+2,y+1),fill=P[14] if ident==1 else P[1] if ident==2 else P[4])
        for y in range(20,191,27):
            for x in range(18,290,35):
                if not clear_ground(x,y,19):continue
                if ident==1:
                    d.ellipse((x-9,y-3,x+9,y+4),fill=P[18]);d.line((x-6,y,x+3,y),fill=P[19])
                    d.rectangle((x+5,y-9,x+12,y-3),fill=P[14]);d.line((x+6,y-9,x+11,y-9),fill=P[16])
                elif ident==2:
                    d.line((x-12,y+4,x+13,y+4),fill=P[2],width=2)
                    d.line((x-12,y+10,x+13,y+10),fill=P[2],width=2)
                    for xx in range(x-10,x+14,6):d.line((xx,y+2,xx,y+12),fill=P[14])
                    d.rectangle((x-1,y-12,x+1,y+1),fill=P[2]);d.rectangle((x-4,y-14,x+4,y-11),fill=P[17])
                    d.line((x-2,y-10,x+2,y-10),fill=P[4])
                else:
                    d.polygon([(x-12,y),(x-4,y-6),(x+10,y-2),(x+13,y+5),(x-8,y+6)],fill=P[23])
                    d.line((x-6,y+1,x+4,y-2),fill=P[22],width=2)
                    d.rectangle((x-9,y-8,x-5,y-5),fill=P[4])
        d.line(road,fill=INK,width=25,joint='curve')
        d.line(road,fill=P[16],width=23,joint='curve')
        d.line(road,fill=P[14],width=21,joint='curve')
        for a,b in zip(road,road[1:]):
            for off in (-6,6):
                delta=(0,off) if a[1]==b[1] else (off,0)
                d.line((a[0]+delta[0],a[1]+delta[1],b[0]+delta[0],b[1]+delta[1]),fill=P[15],width=2)
        for px,py in m['pads']:
            x,y=px//2,(py-32)//2
            d.rectangle((x-12,y-9,x+12,y+11),fill=ground)
            d.rectangle((x-11,y-8,x+11,y+8),fill=INK)
            d.rectangle((x-10,y-7,x+10,y+5),fill=LIGHT)
            d.line((x-9,y-7,x+9,y-7),fill=CREAM)
            d.rectangle((x-8,y-5,x+8,y+3),fill=MID)
            d.line((x-3,y-1,x+3,y-1),fill=P[20],width=2)
            d.line((x,y-4,x,y+2),fill=P[20],width=2)
        d.line((8,5,290,5),fill=INK,width=5);d.line((8,4,290,4),fill=MID,width=3)
        for x in range(14,291,24):d.rectangle((x,2,x+2,7),fill=STEEL)
        full=im.resize((600,408),Image.Resampling.NEAREST)
    save(full,'map-%d.png'%(ident+1))
    previews.paste(full.resize((120,82),Image.Resampling.NEAREST),(ident*120,0))
save(previews,'map-previews.png')
