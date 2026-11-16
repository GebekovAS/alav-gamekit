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
    def find(self,name):return []
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


def load(saved=None):
    kit=Kit()
    if saved is not None:kit.saved=saved
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
assert hk.saved['map_records']['0:2']==23 and hk.saves==1
packet=h['match'].snapshot();packet['you']='1'
client.inbox=[(0,packet)];c['update'](.1)
assert ck.saved['map_records']['0:2']==23 and ck.saves==1
c['update'](.1);assert ck.saves==1
packet=dict(packet,s='break');client.inbox=[(0,packet)];c['update'](.1)
packet=dict(packet,s='defeat',n=18);client.inbox=[(0,packet)];c['update'](.1)
assert ck.saved['map_records']['0:2']==23 and ck.saves==2
# A lost host returns to title, even when the game had an ALAV lobby role.
ck.ROLE='join';c['role_started']=True
for _ in range(51):c['update'](.1)
assert c['net'] is None and c['lost_message']=='Ведущий отключился'
c['update'](.1);assert c['net'] is None
assert host.polls>15 and client.polls>50
print('PASS real update: input sequences, 20Hz send, snapshots, stale input, drop, reconnect, deferred join, host loss, SELECT+START, per-console records')

# Host choice travels through actual update/snapshot reception; clients cannot choose.
h,hk=load();h['begin']('host');h['net'].peers={1:{}}
hk.edges={'RIGHT'};h['update'](.1);hk.edges=set()
assert h['match'].map_id==1 and hk.saved['map']==1
c,ck=load();c['begin']('join')
packet=h['match'].snapshot();packet['you']='1';c['net'].inbox=[(0,packet)]
c['update'](.1);assert c['view']['map']==1
h['net'].inbox=[(1,[1,0,8])];h['update'](.1)
assert h['match'].map_id==1
# Reload saved data through the same initialization as a new process.
h,hk=load({'map':2,'team_records':{'2':25}})
assert h['records']['0:2']==25
h['begin']('host',True)
assert h['match'].map_id==2 and h['match'].phase=='prep'
h['match'].phase='defeat';h['match'].wave=19;h['match'].wave_players=2
h['update'](.1)
assert hk.saved['map_records']['2:2']==19
assert hk.saved['map_records']['0:2']==25
h['recorded']=False;h['match'].wave_players=4;h['update'](.1)
assert hk.saved['map_records']['2:2']==19 and hk.saved['map_records']['2:4']==19
print('PASS host map picker/live join snapshot/solo selection/per-map records')

# Current title creates a room; discovering/joining rooms belongs to ALAV Store.
h,hk=load();hk.find=lambda name:['127.0.0.1'];hk.edges={'A'}
h['update'](.1)
assert h['net'] is not None and h['net'].is_host
print('PASS title creates host; ALAV Store supplies join role')

for saved in ({},{'map':-1},{'map':4},{'map':'2'},{'map':True}):
    ns,kit=load(saved);ns['begin']('host',True)
    assert ns['match'].map_id==0
print('PASS saved-map reload/default/validation and legacy record migration')

# Late-game controls cross the real masks -> host action -> snapshot -> join path.
from rules import A,B,Y,star_price
h,hk=load();h['begin']('host',True);host=h['net'];host.peers={1:{}}
h['update'](.1);m=h['match'];m.bank['cash']=1000
m.towers[0]=[3,250,0.,0]
p=m.players['1'];p['x'],p['y'],p['target']=104,138,0
number=0
def remote_input(held,pressed=0):
    global number
    number+=1;host.inbox=[(1,[number,held,pressed])];h['update'](.1)
remote_input(A,A);assert not p['menu']
remote_input(0);assert p['menu']=='build'
remote_input(0,Y);assert m.bank['r']['1'][1:3]==[12,125]
remote_input(A,A);remote_input(0);assert m.towers[0][3]==1 and m.bank['cash']==875
remote_input(0)
for i in range(4):remote_input(A,A if i==0 else 0)
assert m.over=={0:'1'}
c,ck=load();c['begin']('join')
import json
packet=json.loads(json.dumps(m.snapshot()));packet['you']='1'
c['net'].inbox=[(0,packet)];c['update'](.1)
assert c['view']['oc']=={'0':'1'} and c['view']['t'][0]==[3,375,1]
remote_input(0);assert not m.over and not p['menu']
m.jammers=[[9006,104.,100.,0,100.,True]]
for _ in range(9):remote_input(B)
assert m.jammers
remote_input(B);assert not m.jammers and m.bank['cash']==883
print('PASS network A tap/hold/release, mastery reservation/purchase, JSON join state, B removal/bounty')
