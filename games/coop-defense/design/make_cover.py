"""Ports-list poster cover.png (512x512): the title screen without its button hints.
Needs design/runtime-title.png (a title-screen render) and assets/title-bg.png. Run from the kit root."""
import os
from PIL import Image
here = os.path.dirname(__file__)
shot = Image.open(os.path.join(here, 'runtime-title.png')).convert('RGB')
bg = Image.open(os.path.join(here, '..', 'assets', 'title-bg.png')).convert('RGB')
cover = bg.crop((80, 0, 520, 440))
cover.paste(shot.crop((80, 0, 520, 350)), (0, 0))  # logo, core, workers; below y=350 only hints
cover = cover.resize((512, 512), Image.LANCZOS)
out = os.path.join(here, '..', 'cover.png')
cover.save(out, optimize=True)
print(out, cover.size, os.path.getsize(out), 'bytes')
