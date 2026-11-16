"""Contact sheets at native 600x440 resolution for each review round."""
from PIL import Image, ImageDraw
from pathlib import Path
import sys
p=Path(__file__).resolve().parent
files=sorted(p.glob('[0-9][0-9]-*.png'))
review_dir=p/'out'/'reviews'
review_dir.mkdir(parents=True,exist_ok=True)
for group in range((len(files)+4)//5):
 batch=files[group*5:(group+1)*5]
 out=Image.new('RGB',(1200,1398),'#29343b');d=ImageDraw.Draw(out)
 for i,f in enumerate(batch):
  x=(i%2)*600;y=(i//2)*466
  out.paste(Image.open(f),(x,y+26));d.text((x+10,y+5),f.name,fill='white')
 out.save(review_dir/('round-%s-%s.png'%(sys.argv[1],group+1)))
