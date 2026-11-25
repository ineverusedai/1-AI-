# Helper: reads frame.png only; accumulates seen (non-black) pixels into mem.json and prints merged map.
# Current frame's non-black pixels override memory. Usage: python3 fogmap.py [reset]
import sys, json, os
from PIL import Image
im=Image.open('frame.png').convert('RGB')
off=28; cs=(im.size[0]-off)/64
def px(x,y): return im.getpixel((int(off+cs*x+cs/2),int(off+cs*y+cs/2)))
mem={}
if os.path.exists('mem.json') and not (len(sys.argv)>1 and sys.argv[1]=='reset'):
    mem=json.load(open('mem.json'))
names={(0,0,0):' ',(51,51,51):'#',(102,102,102):'.',(255,220,0):'y',(255,133,27):'o',(30,147,255):'B',(204,204,204):'g',(249,60,49):'r',(255,255,255):'W',(79,204,48):'G'}
for y in range(0,60):
    for x in range(64):
        p=px(x,y)
        if p!=(0,0,0): mem['%d,%d'%(x,y)]=names.get(p,'?')
        elif '%d,%d'%(x,y) not in mem: pass
json.dump(mem,open('mem.json','w'))
print('    '+''.join(str((x//10)%10) for x in range(64)))
print('    '+''.join(str(x%10) for x in range(64)))
for y in range(0,60):
    print('%3d '%y+''.join(mem.get('%d,%d'%(x,y),' ') if px(x,y)==(0,0,0) else names.get(px(x,y),'?') for x in range(64)))
