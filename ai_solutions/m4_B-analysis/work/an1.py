import cv2,numpy as np,sys
def load(p):
    cap=cv2.VideoCapture(p);fr=[]
    while True:
        ok,f=cap.read()
        if not ok:break
        fr.append(f[...,1].astype(np.float32)/255)
    return np.array(fr)
F=load(sys.argv[1])
R=4
for t in [0,1,30,60]:
    a,b=F[t],F[t+1]
    best=[]
    errs={}
    for dy in range(-R,R+1):
        for dx in range(-R,R+1):
            s=np.roll(a,(dy,dx),axis=(0,1))
            e=cv2.blur((b-s)**2,(9,9))
            errs[(dy,dx)]=e
    keys=list(errs);E=np.array([errs[k] for k in keys])
    am=E.argmin(0)
    cnt=np.bincount(am.ravel(),minlength=len(keys))
    order=np.argsort(-cnt)[:5]
    print(t,[(keys[i],cnt[i]) for i in order], 'zero err', E[keys.index((0,0))].mean())
