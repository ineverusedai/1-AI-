import cv2,numpy as np
def norm(d):
    d=(d-d.mean())/(d.std()+1e-6); return np.clip(128-40*d,0,255).astype(np.uint8)
out=[]
for f in ['t00942','t00001','t00002']:
    im=cv2.imread('labeled/images/%s.jpg'%f); g=cv2.cvtColor(im,cv2.COLOR_BGR2GRAY).astype(np.float32)
    row=[]
    s=cv2.resize(g,(320,200),interpolation=cv2.INTER_AREA)
    for k in [0,5,9]:
        t=s.copy()
        if k: t=cv2.medianBlur(t.astype(np.uint8),k).astype(np.float32)
        t=cv2.resize(t,(160,100),interpolation=cv2.INTER_AREA); t=cv2.GaussianBlur(t,(0,0),1.0)
        row.append(norm(t-cv2.GaussianBlur(t,(0,0),20)))
    # value channel min-ish: erosion removes bright spots
    t=cv2.erode(s,np.ones((5,5)));t=cv2.resize(t,(160,100),interpolation=cv2.INTER_AREA); t=cv2.GaussianBlur(t,(0,0),1.0)
    row.append(norm(t-cv2.GaussianBlur(t,(0,0),20)))
    out.append(np.hstack([cv2.resize(r,(320,200)) for r in row]))
cv2.imwrite('work/variants.png',np.vstack(out))
