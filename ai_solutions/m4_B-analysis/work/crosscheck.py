# Independent check: bbox-free multi-scale template matching (cv2.matchTemplate) of each option
# on the motion map, and robustness using only the first 30 / 8 frames.
import sys,json,time
sys.path.insert(0,'.')
import numpy as np, cv2, solver
Q=json.load(open('problems/questions.json'))
agree_tm=agree30=agree8=0; mt=[];m30=[];m8=[]
for q in Q:
    F=solver._decode(open('problems/'+q['video'],'rb').read())
    D=solver.motion_map(F)
    ref=q['options'][int(np.argmax(solver.score_options(D,q['options'])))]
    # template matching
    Dn=D.astype(np.float32)
    sc=[]
    for opt in q['options']:
        best=-1
        g=solver._render(opt,solver._fonts()[0])
        for hh in range(80,141,10):
            ww=int(round(g.shape[1]*hh/g.shape[0]))
            if ww+20>=488: continue
            t=cv2.resize(g,(ww,hh),interpolation=cv2.INTER_AREA)
            t=cv2.copyMakeBorder(t,10,10,10,10,cv2.BORDER_CONSTANT,0)
            t=cv2.GaussianBlur(t,(0,0),2.5).astype(np.float32)
            r=cv2.matchTemplate(Dn,t,cv2.TM_CCOEFF_NORMED)
            best=max(best,float(r.max()))
        sc.append(best)
    o=np.argsort(sc)[::-1]; tm=q['options'][o[0]]; mt.append(sc[o[0]]-sc[o[1]])
    agree_tm+=tm==ref
    for n,acc,lst in ((31,'30',m30),(9,'8',m8)):
        Dk=solver.motion_map(F[:n]); s=solver.score_options(Dk,q['options']); oo=np.argsort(s)[::-1]
        lst.append((q['options'][oo[0]]==ref, s[oo[0]]-s[oo[1]]))
    print(q['q'],ref,tm,f"tm_margin={mt[-1]:.3f}",'30f',m30[-1],'8f',m8[-1],flush=True)
print('template agree',agree_tm,'/36 min margin',min(mt))
print('30 frames agree',sum(a for a,_ in m30),'min margin',min(m for _,m in m30))
print('8 frames agree',sum(a for a,_ in m8),'min margin',min(m for _,m in m8))
