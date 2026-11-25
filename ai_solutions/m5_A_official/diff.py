# Helper: compares prev.png and frame.png (both copies of the screen), prints changed cells.
from PIL import Image
a=Image.open('prev.png').convert('RGB'); b=Image.open('frame.png').convert('RGB')
off=28; cs=(a.size[0]-off)/64
d=[]
for y in range(64):
  for x in range(64):
    p=(int(off+cs*x+cs/2),int(off+cs*y+cs/2))
    if a.getpixel(p)!=b.getpixel(p): d.append((x,y,a.getpixel(p),b.getpixel(p)))
print(len(d)); print([t for t in d if t[1]>0][:60])
