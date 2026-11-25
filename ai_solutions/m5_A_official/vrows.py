# Helper: reads frame.png only; for given (x, starty) pairs prints count of white (255,255,255) rows going down from starty.
import sys
from PIL import Image
im=Image.open('frame.png').convert('RGB')
off=28; cs=(im.size[0]-off)/64
def px(x,y): return im.getpixel((int(off+cs*x+cs/2),int(off+cs*y+cs/2)))
a=list(map(int,sys.argv[1:]))
for i in range(0,len(a),3):
    name=a[i]; x,s=a[i+1],a[i+2]; y=s
    while y<64 and px(x,y)==(255,255,255): y+=1
    print('tank',name,'x',x,'white rows from',s,'to',y-1,'count',y-s)
