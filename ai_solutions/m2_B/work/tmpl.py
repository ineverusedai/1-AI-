import json,numpy as np,cv2,time
from PIL import Image,ImageDraw,ImageFont
d=json.load(open('labeled/labels.json')); X=np.load('work/X.npy'); sp=json.load(open('work/split.json'))
FONT='/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
cache={}
def tmpl(word,h):
    k=(word,h)
    if k in cache: return cache[k]
    f=ImageFont.truetype(FONT,h*4)
    bb=f.getbbox(word); w=bb[2]-bb[0]+8; hh=bb[3]-bb[1]+8
    im=Image.new('L',(w,hh),0); ImageDraw.Draw(im).text((4-bb[0],4-bb[1]),word,font=f,fill=255)
    a=np.asarray(im,np.float32)
    a=cv2.resize(a,(max(1,w//4),max(1,hh//4)),interpolation=cv2.INTER_AREA)
    a=cv2.GaussianBlur(a,(0,0),1.5)
    cache[k]=a; return a
def score(img,word,sizes):
    best=-1
    for h in sizes:
        t=tmpl(word,h)
        if t.shape[0]>=img.shape[0] or t.shape[1]>=img.shape[1]: continue
        r=cv2.matchTemplate(-img,t,cv2.TM_CCOEFF_NORMED); best=max(best,r.max())
    return best
for sizes in [tuple(range(16,40,2)),tuple(range(20,34,2))]:
    c=0; idx=sp['val']; t0=time.time()
    for i in idx:
        x=d[i]; cands=[w for w in x['choices'] if len(w)==2] if True else x['choices']
        s=[score(X[i],w,sizes) if len(w)<=3 else -9 for w in x['choices']]
        c+= x['choices'][int(np.argmax(s))]==x['answer']
    print(sizes,c,len(idx),(time.time()-t0)/len(idx))
