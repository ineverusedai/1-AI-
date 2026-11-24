import cv2, numpy as np
# v3: 160x100, 2채널 = [일반 저역통과, 메디안(9) 으로 작은 꽃/잎 점을 지운 저역통과]
W,H=160,100
def _hp(t):
    t=cv2.GaussianBlur(t,(0,0),1.0)
    d=t-cv2.GaussianBlur(t,(0,0),20)
    return (d-d.mean())/(d.std()+1e-6)
def preprocess(im_bgr):
    g=cv2.cvtColor(im_bgr,cv2.COLOR_BGR2GRAY)
    s=cv2.resize(g,(320,200),interpolation=cv2.INTER_AREA)
    a=cv2.resize(s.astype(np.float32),(W,H),interpolation=cv2.INTER_AREA)
    m=cv2.resize(cv2.medianBlur(s,9).astype(np.float32),(W,H),interpolation=cv2.INTER_AREA)
    return np.stack([_hp(a),_hp(m)]).astype(np.float32)
def decode(b):
    return cv2.imdecode(np.frombuffer(b,np.uint8),cv2.IMREAD_COLOR)
