# Helper: reads frame.png only; summarizes 5x5 cells (origin offset ox,oy) as '#' wall(dark), '.' floor, '*' other
import sys
from PIL import Image
im=Image.open('frame.png').convert('RGB')
off=28; cs=(im.size[0]-off)/64
def px(x,y): return im.getpixel((int(off+cs*x+cs/2),int(off+cs*y+cs/2)))
ox=int(sys.argv[1]) if len(sys.argv)>1 else 4
oy=int(sys.argv[2]) if len(sys.argv)>2 else 0
print('   '+''.join('%3d'%x for x in range(ox,60,5)))
for y in range(oy,60,5):
    r='%2d '%y
    for x in range(ox,60,5):
        cnt={}
        for dy in range(5):
            for dx in range(5):
                if x+dx<64 and y+dy<64:
                    p=px(x+dx,y+dy); cnt[p]=cnt.get(p,0)+1
        if cnt.get((102,102,102),0)>=20: ch='.'
        elif cnt.get((51,51,51),0)>=20: ch='#'
        else: ch='*'
        r+='  '+ch
    print(r)
