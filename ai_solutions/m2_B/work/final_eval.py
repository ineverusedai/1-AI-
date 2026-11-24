import sys,os; sys.path.insert(0,os.getcwd())
import json,time,numpy as np,sys
t0=time.time(); import solver; print('import',round(time.time()-t0,2),'s')
d=json.load(open('labeled/labels.json')); sp=json.load(open('work/split.json'))
idx=sp[sys.argv[1] if len(sys.argv)>1 else 'holdout']
bs=[open('labeled/'+d[i]['file'],'rb').read() for i in idx]
solver.solve(bs[0],d[idx[0]]['choices'])  # warmup
ts=[];c=0;wrong=[]
for b,i in zip(bs,idx):
    t=time.perf_counter(); r=solver.solve(b,d[i]['choices']); ts.append(time.perf_counter()-t)
    if r==d[i]['answer']: c+=1
    else: wrong.append((d[i]['file'],d[i]['choices'],d[i]['answer'],r))
ts=np.array(ts)*1000
print(f'acc {c}/{len(idx)} = {c/len(idx):.4f}')
print(f'time ms mean {ts.mean():.1f} p50 {np.median(ts):.1f} p99 {np.percentile(ts,99):.1f} max {ts.max():.1f}')
for w in wrong: print('WRONG',w)
