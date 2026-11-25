import sys,json,time
sys.path.insert(0,'.')
import numpy as np, solver
Q=json.load(open('problems/questions.json'))
for q in Q:
    t=time.time()
    vid=open('problems/'+q['video'],'rb').read()
    F=solver._decode(vid); D=solver.motion_map(F); s=solver.score_options(D,q['options'])
    o=np.argsort(s)[::-1]
    dt=time.time()-t
    print(q['q'], q['options'][o[0]], 'ABCDEF'[o[0]], f"top={s[o[0]]:.3f} 2nd={s[o[1]]:.3f}({q['options'][o[1]]}) margin={s[o[0]]-s[o[1]]:.3f} t={dt:.2f}s")
