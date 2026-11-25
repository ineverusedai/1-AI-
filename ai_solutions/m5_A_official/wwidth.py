# Helper: reads frame.png only; for given (row,startx) pairs prints length of white (255,255,255) run starting at startx.
import sys
from PIL import Image
im=Image.open('frame.png').convert('RGB')
off=28; cs=(im.size[0]-off)/64
def px(x,y): return im.getpixel((int(off+cs*x+cs/2),int(off+cs*y+cs/2)))
args=list(map(int,sys.argv[1:]))
for i in range(0,len(args),2):
    r,s=args[i],args[i+1]; x=s
    while x<64 and px(x,r)==(255,255,255): x+=1
    print('row',r,'start',s,'white until x',x-1,'width',x-s)
