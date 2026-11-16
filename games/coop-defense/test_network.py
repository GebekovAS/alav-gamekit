"""Exercise the real main.update with an in-memory transport (not a Wi-Fi test)."""
import ast
from pathlib import Path
import types

class Transport:
    def __init__(self,host):self.is_host=host;self.peers={};self.connected=True;self.inbox=[];self.sent=[];self.polls=0
    def recv(self):
        self.polls+=1;items=self.inbox;self.inbox=[];return items
    def send(self,msg,to=None):self.sent.append((to,msg))

class Kit:
    ROLE=None
    def __init__(self):self.keys=set();self.edges=set();self.created=[];self.saved={};self.saves=0
    def load(self):return self.saved
    def save(self,data):self.saved=data.copy();self.saves+=1
    def sprite(self,*args):return None
    def image(self,name):return None
    def host(self,name,max_players):
        assert name=='coop-defense' and max_players==4
        t=Transport(True);self.created.append(t);return t
    def join(self,name):
        assert name=='coop-defense'
        t=Transport(False);self.created.append(t);return t
    def hit(self,a,b):
        from rules import rect_hit
        return rect_hit(a,b)
    def down(self,key):return key in self.keys
    def pressed(self,key):return key in self.edges
    def tone(self,*a,**kw):pass
    def quit(self):raise AssertionError('unexpected quit')


def load():
    kit=Kit()
    tree=ast.parse(Path(__file__).with_name('main.py').read_text(encoding='utf-8'))
    tree.body=[n for n in tree.body if not (isinstance(n,ast.Import) and any(v.name=='alav' for v in n.names))
               and not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='run')]
    ns={'g':kit};exec(compile(tree,'main.py','exec'),ns)
    return ns,kit

h,hk=load();h['begin']('host');host=h['net'];host.peers={1:{},2:{}}
h['update'](.1)
assert host.polls==1 and set(h['match'].players)=={'0','1','2'}
host.inbox=[(1,[4,8,16]),(1,[4,8,16]),(2,[1,0,16])]
h['update'](.1)
assert h['match'].players['1']['ready'] and h['match'].players['2']['ready']
assert h['seen']['1']==4
# Duplicate sequence cannot toggle ready a second time.
host.inbox=[(1,[4,0,16])];h['update'](.1)
assert h['match'].players['1']['ready']
# Invalid payloads/prices/unknown players never reach the economy.
old=h['match'].bank['cash']
host.inbox=[(1,{'price':-100}),(1,[5,4096,0]),(8,[1,0,16])];h['update'](.1)
assert h['match'].bank['cash']==old
# Expired held input stops movement after 1 second, then reservation is removed on drop.
x=h['match'].players['1']['x']
for _ in range(11):h['update'](.1)
x=h['match'].players['1']['x'];h['update'](.1)
assert h['match'].players['1']['x']==x
from rules import transaction
transaction(h['match'].bank,'1',0,0,h['match'].time,True)
host.peers.pop(1);h['update'](.1)
assert '1' not in h['match'].players and '1' not in h['match'].bank['r']
assert '1' not in h['seen']
# Reconnection accepts a restarted sequence counter; new players wait during a wave.
h['match'].start();h['match'].start_wave();host.peers[1]={};host.peers[3]={}
host.inbox=[(1,[1,0,0])];h['update'](.1)
assert '1' in h['match'].players and '3' not in h['match'].players
assert any(to==3 and packet.get('wait') for to,packet in host.sent)
# A silent peer is removed after 5 seconds, even while still in peers.
for _ in range(51):h['update'](.1)
assert '1' not in h['match'].players
host.inbox=[(1,[1,0,0])];h['update'](.1)
assert '1' in h['match'].players and h['match'].players['1']['slot']!=0
# Joiners only send masks at 20 Hz. Money and phase come from snapshots.
c,ck=load();c['begin']('join');client=c['net']
packet=h['match'].snapshot();packet['you']='1'
client.inbox=[(0,packet)];ck.edges={'A'};c['update'](.01)
ck.edges=set();c['update'](.04)
assert client.sent[-1][1][2]==16 and c['match'] is None
ck.keys={'RIGHT'}
for _ in range(10):c['update'](.01)
assert len(client.sent)==3 and all(isinstance(p,list) and len(p)==3 for _,p in client.sent)
assert c['view']['c']==packet['c']
# A quick SELECT+START release cannot enqueue START for the next network packet.
ck.keys={'SELECT'};ck.edges={'START'}
assert c['masks']()[1]&1024==0
ck.keys=set();ck.edges=set()
# SELECT crosses the actual masks/packet path and blocks START readiness.
from rules import START,SELECT
h['match'].phase='prep'
h['match'].players['1']['ready']=False
host.inbox=[(1,[100,SELECT,START])];h['update'](.1)
assert not h['match'].players['1']['ready']
host.inbox=[(1,[101,0,START])];h['update'](.1)
assert h['match'].players['1']['ready']
# Each console persists the result once; a weaker result preserves the record.
h['match'].phase='defeat';h['match'].wave=23;h['match'].wave_players=2
h['update'](.1)
assert hk.saved['team_records']['2']==23 and hk.saves==1
packet=h['match'].snapshot();packet['you']='1'
client.inbox=[(0,packet)];c['update'](.1)
assert ck.saved['team_records']['2']==23 and ck.saves==1
c['update'](.1);assert ck.saves==1
packet=dict(packet,s='break');client.inbox=[(0,packet)];c['update'](.1)
packet=dict(packet,s='defeat',n=18);client.inbox=[(0,packet)];c['update'](.1)
assert ck.saved['team_records']['2']==23 and ck.saves==2
# A lost host returns to title, even when the game had an ALAV lobby role.
ck.ROLE='join';c['role_started']=True
for _ in range(51):c['update'](.1)
assert c['net'] is None and c['lost_message']=='Ведущий отключился'
c['update'](.1);assert c['net'] is None
assert host.polls>15 and client.polls>50
print('PASS real update: input sequences, 20Hz send, snapshots, stale input, drop, reconnect, deferred join, host loss, SELECT+START, per-console records')
