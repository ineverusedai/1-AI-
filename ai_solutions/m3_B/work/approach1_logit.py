# Approach 1: conditional-logit (4-way softmax) scorer on DTW-distance features. Train-only, 5-fold CV inside train.
import json, pickle, time, sys
import numpy as np, torch
torch.set_num_threads(2)
F = pickle.load(open('work/dtwfeat.pkl', 'rb')); S = json.load(open('work/split.json'))
L = {x['dir']: x['answer'] for x in json.load(open('labeled/labels.json'))}
def mk(ts, cols):
    X = np.stack([F[t][:, cols] for t in ts]).astype(np.float32)  # N,4,f
    X = np.concatenate([X, X - X.mean(1, keepdims=True)], 2)       # add within-item centered feats
    y = np.array([L[t] - 1 for t in ts]); return torch.tensor(X), torch.tensor(y)
def fit(X, y, l2=1e-3, epochs=500):
    mu = X.reshape(-1, X.shape[2]).mean(0); sd = X.reshape(-1, X.shape[2]).std(0) + 1e-6
    w = torch.zeros(X.shape[2], requires_grad=True)
    opt = torch.optim.LBFGS([w], max_iter=epochs, line_search_fn='strong_wolfe')
    Xn = (X - mu) / sd
    def clo():
        opt.zero_grad(); loss = torch.nn.functional.cross_entropy(-(Xn @ w), y) + l2 * (w ** 2).sum(); loss.backward(); return loss
    opt.step(clo)
    return w.detach(), mu, sd
def pred(m, X):
    w, mu, sd = m; return (-(((X - mu) / sd) @ w)).argmax(1)
tr = np.array(S['train'])
for name, cols in [('all4+len', [0, 1, 2, 3, 4]), ('cmn+both', [1, 3]), ('none+frame+len', [0, 2, 4])]:
    t0 = time.time(); ok = 0
    folds = np.array_split(np.random.RandomState(0).permutation(len(tr)), 5)
    for k in range(5):
        va = tr[folds[k]]; trn = tr[np.concatenate([folds[j] for j in range(5) if j != k])]
        m = fit(*mk(trn, cols)); Xv, yv = mk(va, cols); ok += (pred(m, Xv) == yv).sum().item()
    print(name, 'CV acc', ok, len(tr), ok / len(tr), '%.1fs' % (time.time() - t0))
t0 = time.time(); m = fit(*mk(tr, [0, 1, 2, 3, 4])); print('final fit time %.2fs' % (time.time() - t0), 'w', m[0].numpy().round(3))
pickle.dump({'w': m[0].numpy(), 'mu': m[1].numpy(), 'sd': m[2].numpy(), 'cols': [0, 1, 2, 3, 4]}, open('work/logit_model.pkl', 'wb'))
