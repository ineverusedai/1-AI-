import json,numpy as np,cv2,time,sys
sys.path.insert(0,'.')
import importlib
d=json.load(open('labeled/labels.json')); X=np.load('work/X2c.npy'); sp=json.load(open('work/split.json'))
from PIL import Image,ImageDraw,ImageFont
FONT='/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'; cache={}
def tmpl(word,h,sig):
    k=(word,h,sig)
    if k in cache: return cache[k]
    f=ImageFont.truetype(FONT,h*4); bb=f.getbbox(word); w=bb[2]-bb[0]+8; hh=bb[3]-bb[1]+8
    im=Image.new('L',(w,hh),0); ImageDraw.Draw(im).text((4-bb[0],4-bb[1]),word,font=f,fill=255)
    a=cv2.resize(np.asarray(im,np.float32),(max(1,w//4),max(1,hh//4)),interpolation=cv2.INTER_AREA)
    cache[k]=cv2.GaussianBlur(a,(0,0),sig); return cache[k]
for ch in [0,1]:
  for sig in [1.0,1.5]:
    for sizes in [tuple(range(26,46,2)),tuple(range(28,42,3))]:
        c=0;t0=time.time()
        for i in sp['val']:
            x=d[i]; img=-X[i,ch]
            s=[max(cv2.matchTemplate(img,tmpl(w,h,sig),cv2.TM_CCOEFF_NORMED).max() for h in sizes) if ' ' not in w else -9 for w in x['choices']]
            c+=x['choices'][int(np.argmax(s))]==x['answer']
        print(ch,sig,sizes,c,(time.time()-t0)/300)
