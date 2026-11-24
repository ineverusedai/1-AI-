import sys,json,time
sys.path.insert(0,'.')
t0=time.time()
from solver import solve
Q=json.load(open('problems/questions.json'))
ts=[];ans=[]
for q in Q:
    v=open('problems/'+q['video'],'rb').read()
    t=time.time();a=solve(v,q['options']);ts.append(time.time()-t)
    assert a in q['options']; ans.append(f"{q['q']}:{'ABCDEF'[q['options'].index(a)]}({a})")
print(' '.join(ans)); print('solve time mean %.2f max %.2f min %.2f'%(sum(ts)/len(ts),max(ts),min(ts)))
