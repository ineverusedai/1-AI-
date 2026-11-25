# Helper: reads frame.png only; prints, for given rows, the x-extent of the leftmost run of gray (102,102,102).
import sys
from PIL import Image
im=Image.open('frame.png').convert('RGB')
off=28; cs=(im.size[0]-off)/64
def px(x,y): return im.getpixel((int(off+cs*x+cs/2),int(off+cs*y+cs/2)))
for r in map(int,sys.argv[1:]):
    w=0
    while w<64 and px(w,r)==(102,102,102): w+=1
    print('row',r,'gray width',w)
