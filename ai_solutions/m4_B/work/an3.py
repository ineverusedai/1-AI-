import cv2,numpy as np,sys
def load(p):
    cap=cv2.VideoCapture(p);fr=[]
    while True:
        ok,f=cap.read()
        if not ok:break
        fr.append(f[...,1].astype(np.float32)/255)
    return np.array(fr)
for q in sys.argv[1:]:
    F=load(f'problems/videos/{q}.mp4')
    a=F[:-1];b=F[1:]
    ebg=((b-np.roll(a,2,axis=2))**2).sum(0)
    efg=((b-np.roll(a,-2,axis=2))**2).sum(0)
    D=cv2.GaussianBlur(ebg-efg,(0,0),2)
    img=np.clip(128+D*3,0,255).astype(np.uint8)
    cv2.imwrite(f'work/{q}_mask.png',img)
    print(q,D.min(),D.max())
