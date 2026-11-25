# compute DTW cost features for all items (train + heldout); heldout values are only used at final evaluation
import json, sys, pickle, time
import numpy as np
sys.path.insert(0, '.')
from dtw import dtw_cost
D = pickle.load(open('work/logmel.pkl', 'rb'))
def norm(X, mode):
    if mode in ('cmn', 'both'): X = X - X.mean(0)
    if mode in ('frame', 'both'): X = X - X.mean(1, keepdims=True)
    return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-6)
MODES = ['none', 'cmn', 'frame', 'both']
F = {}
t0 = time.time()
for t, it in D.items():
    feats = []
    for o in it['opts']:
        f = []
        for mode in MODES:
            r = norm(it['ref'], mode); q = norm(o, mode)
            f.append(dtw_cost(1 - r @ q.T))
        f.append(np.log(len(o) / len(it['ref'])))
        feats.append(f)
    F[t] = np.array(feats)
pickle.dump(F, open('work/dtwfeat.pkl', 'wb'))
print('done', time.time() - t0)
