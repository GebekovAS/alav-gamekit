"""Small contract checks for the effect queue; no alternate drawing backend."""
import ast
import math
from pathlib import Path
source=Path(__file__).resolve().parent/'mockup.py'
tree=ast.parse(source.read_text(encoding='utf-8'))
names={'fx','ray','attack'}
module=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[])
ns={'math':math,'effect_queue':[],'FX_CAP':37}
exec(compile(module,str(source),'exec'),ns)
for tower in range(12):
    seen=set()
    for step in range(120):
        ns['effect_queue'].clear()
        ns['attack'](tower,(50,80),(150,95),step/120)
        seen.update(e[0] for e in ns['effect_queue'])
        assert len(ns['effect_queue'])<=4
    expected=[{'rivet','muzzle','spark'},{'rivet','muzzle','spark'},
              {'lightning','crackle'},{'rail','muzzle','chips'},
              {'slag','shadow','splash'},{'slag','shadow','splash'},
              {'flame'},{'shell','shadow','blast'},{'laser','frost'},
              {'laser2','frost'},{'wave','roadfrost'},{'spike','ice'}][tower]
    assert seen==expected,(tower,seen)
ns['effect_queue'].clear()
for i in range(60):ns['fx']('spark',i,0)
assert len(ns['effect_queue'])==37
assert [e[1] for e in ns['effect_queue']]==list(range(23,60)), 'oldest must be replaced'
print('12 attack timelines, <=4 sprites/attack, FIFO cap 37 + 3 status overlays <=40: PASS')
