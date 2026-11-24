import cv2, numpy as np
ims=[]
for i in range(1,13):
    im=cv2.imread('labeled/images/t%05d.jpg'%i)
    g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY).astype(np.float32)
    s=cv2.resize(g,(120,75),interpolation=cv2.INTER_AREA)
    s=cv2.GaussianBlur(s,(0,0),1.5)
    bg=cv2.GaussianBlur(s,(0,0),15)
    d=s-bg
    d=(d-d.mean())/(d.std()+1e-6)
    d=np.clip(128+40*d,0,255).astype(np.uint8)
    ims.append(cv2.resize(d,(240,150)))
rows=[np.hstack(ims[r*4:(r+1)*4]) for r in range(3)]
cv2.imwrite('work/grid.png',np.vstack(rows))
