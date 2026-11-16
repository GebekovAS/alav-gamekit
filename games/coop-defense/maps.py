"""Shared map geometry, in screen coordinates (HUD occupies y < 32)."""
import math

MAPS = [
    dict(name='Медный изгиб', theme='copper',
         route=[(44,146),(284,146),(284,236),(164,236),(164,296),(524,296)],
         pads=[(104,100),(224,100),(164,190),(374,195),(374,250),(104,270),(225,355),(434,346)],
         gates=[300,750], spawns=[(480,350),(550,350),(480,386),(550,386)]),
    dict(name='Ржавый двор', theme='rust',
         route=[(44,130),(390,130),(390,218),(140,218),(140,310),(524,310)],
         pads=[(104,82),(260,82),(200,174),(444,174),(444,250),(84,270),(230,365),(434,365)],
         gates=[390,1000], spawns=[(490,350),(550,350),(490,386),(550,386)]),
    dict(name='Ночное депо', theme='night',
         route=[(44,150),(310,150),(310,238),(210,238),(210,306),(524,306)],
         pads=[(104,102),(250,102),(250,194),(365,194),(365,260),(150,285),(275,356),(434,356)],
         gates=[310,710], spawns=[(490,350),(550,350),(490,386),(550,386)]),
    dict(name='Инейный перегон', theme='frost',
         route=[(44,140),(460,140),(460,250),(140,250),(140,346),(524,346)],
         pads=[(104,92),(270,92),(180,195),(350,195),(400,298),(84,298),(230,394),(434,394)],
         gates=[470,1180], spawns=[(490,386),(550,386),(500,290),(550,290)]),
]


def lane(progress, offset=0, map_id=0):
    m=MAPS[map_id];a,b,c,d,end=m['ends'];route=m['route']
    if progress<=a:return route[0][0]+progress,route[0][1]+offset
    if progress<=b:return route[1][0]-offset,route[1][1]+progress-a
    if progress<=c:return route[2][0]-progress+b,route[2][1]-offset
    if progress<=d:return route[3][0]-offset,route[3][1]+progress-c
    if progress<=end:return route[4][0]+progress-d,route[4][1]+offset
    return m['core']


for m in MAPS:
    m['segments']=[];m['ends']=[];length=0
    for a,b in zip(m['route'],m['route'][1:]):
        dx,dy=b[0]-a[0],b[1]-a[1]
        size=math.hypot(dx,dy)
        m['segments'].append((*a,dx/size,dy/size,length))
        length+=size;m['ends'].append(length)
    m['length']=length;m['core']=m['route'][-1]
for i,m in enumerate(MAPS):
    m['walls']=[lane(p,map_id=i) for p in m['gates']]
    m['angles']=[math.degrees(math.atan2(s[3],s[2])) for s in m['segments']]
