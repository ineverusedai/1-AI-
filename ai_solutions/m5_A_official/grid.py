# Helper: reads frame.png only, prints 64x64 cell grid as characters.
import sys
from PIL import Image
im=Image.open('frame.png').convert('RGB')
W,H=im.size
off=28; cs=(W-off)/64
cols={}
rows=[]
for y in range(64):
    r=''
    for x in range(64):
        p=im.getpixel((int(off+cs*x+cs/2),int(off+cs*y+cs/2)))
        if p not in cols:
            cols[p]=chr(ord('a')+len(cols)) if len(cols)<26 else '?'
        r+=cols[p]
    rows.append(r)
x0=int(sys.argv[1]) if len(sys.argv)>1 else 0
x1=int(sys.argv[2]) if len(sys.argv)>2 else 64
y0=int(sys.argv[3]) if len(sys.argv)>3 else 0
y1=int(sys.argv[4]) if len(sys.argv)>4 else 64
print('    '+''.join(str((x//10)%10) for x in range(x0,x1)))
print('    '+''.join(str(x%10) for x in range(x0,x1)))
for y in range(y0,y1):
    print('%3d '%y+rows[y][x0:x1])
for p,c in cols.items(): print(c,p)
