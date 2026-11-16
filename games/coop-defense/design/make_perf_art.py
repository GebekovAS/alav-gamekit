"""Append deterministic crowd cells to the existing enemies atlas (PC art tool).
Run with the installed Codex Python/Pillow after make_art.py, or on its own.
"""
from pathlib import Path
from PIL import Image

assets=Path(__file__).resolve().parent.parent/'assets'
source=Image.open(assets/'enemies.png').convert('RGBA').crop((0,0,264,44))
atlas=Image.new('RGBA',(512,44+36*48));atlas.alpha_composite(source)
effects=Image.open(assets/'effects.png').convert('RGBA')
spots=[(-18,-6),(-6,5),(6,-8),(18,4),(-17,9),(-3,-9),(12,12),(20,-10)]
for tint in range(4):
    for kind,n in enumerate((10,14,14)):
        small=source.crop((kind*44,0,kind*44+n,n)) if not tint else effects.crop((kind*44,(20+tint)*128,kind*44+n,(20+tint)*128+n))
        for size_index,count in enumerate((3,5,8)):
            for variant in range(3):
                cell=Image.new('RGBA',(64,48))
                for i,(x,y) in enumerate(spots[:count]):
                    cell.alpha_composite(small,(32-n//2+x+(variant-1)*(i%3-1),24-n//2+y))
                atlas.alpha_composite(cell,(variant*64,44+(tint*9+kind*3+size_index)*48))
atlas.save(assets/'enemies.png',optimize=True)
