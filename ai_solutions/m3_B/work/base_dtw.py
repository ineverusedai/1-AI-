import json, sys, pickle, time
import numpy as np
sys.path.insert(0, '.')
from dtw import dtw_cost
D = pickle.load(open('work/logmel.pkl', 'rb'))
S = json.load(open('work/split.json'))
tr = S['train'][:400]
def norm(X, mode):
    if mode == 'cmn':
        X = X - X.mean(0)
    elif mode == 'frame':
        X = X - X.mean(1, keepdims=True)
    elif mode == 'both':
        X = X - X.mean(0); X = X - X.mean(1, keepdims=True)
    return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-6)
for mode in ['none', 'cmn', 'frame', 'both']:
    t0 = time.time(); ok = 0
    for t in tr:
        r = norm(D[t]['ref'], mode)
        cs = [dtw_cost(1 - r @ norm(o, mode).T) for o in D[t]['opts']]
        ok += (int(np.argmin(cs)) + 1 == D[t]['ans'])
    print(mode, ok, len(tr), ok / len(tr), '%.1fs' % (time.time() - t0), flush=True)
