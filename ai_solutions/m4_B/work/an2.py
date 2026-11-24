import cv2,numpy as np,sys,time
def load(p):
    cap=cv2.VideoCapture(p);fr=[]
    while True:
        ok,f=cap.read()
        if not ok:break
        fr.append(f[...,1].astype(np.float32)/255)
    return np.array(fr)
R=4
keys=[(dy,dx) for dy in range(-R,R+1) for dx in range(-R,R+1)]
for q in sys.argv[1:]:
    t0=time.time()
    F=load(f'problems/videos/{q}.mp4')
    res=[]
    for t in range(0,89,8):
        a,b=F[t],F[t+1]
        E=np.array([cv2.blur((b-np.roll(a,k,axis=(0,1)))**2,(9,9)) for k in keys])
        cnt=np.bincount(E.argmin(0).ravel(),minlength=len(keys))
        o=np.argsort(-cnt)[:2]
        res.append((keys[o[0]],keys[o[1]],cnt[o[1]]))
    print(q,res[:4],time.time()-t0)
