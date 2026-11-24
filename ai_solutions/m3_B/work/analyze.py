import sys, json, time
import numpy as np
sys.path.insert(0, sys.path[0])
from feats import *

BASE = sys.argv[1]


def load(q):
    d = f'{BASE}/problems/q{q:02d}'
    return [read(open(f'{d}/{n}.wav', 'rb').read()) for n in ['ref', 'opt1', 'opt2', 'opt3', 'opt4']]


def mel_feat(x, nb=24, fmax=4500):
    f, P = spec(x)
    s, e = trim(P)
    W = melfb(f, nb, 100, fmax)
    M = np.log(W @ P[:, s:e] + 1e-6 * P.max())
    M = M - M.mean(1, keepdims=True)
    M = M / (M.std(1, keepdims=True) + 1e-9)
    return M.T


def env_feat(x):
    f, P = spec(x)
    s, e = trim(P)
    E = np.log(P[:, s:e].sum(0) + 1e-6 * P.sum(0).max())
    return E


def cosD(A, B):
    A = A / (np.linalg.norm(A, axis=1, keepdims=True) + 1e-9)
    B = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-9)
    return 1 - A @ B.T


def eucD(A, B):
    return np.sqrt(((A[:, None, :] - B[None, :, :]) ** 2).sum(-1))


def m_mel_dtw(xs, nb=24, fmax=4500, dist=cosD):
    R = mel_feat(xs[0], nb, fmax)
    return [dtw(dist(R, mel_feat(o, nb, fmax))) for o in xs[1:]]


def m_env_dtw(xs):
    r = env_feat(xs[0]); r = (r - r.mean()) / r.std()
    out = []
    for o in xs[1:]:
        e = env_feat(o); e = (e - e.mean()) / e.std()
        out.append(dtw(np.abs(r[:, None] - e[None, :])))
    return out


def m_env_xcorr(xs):
    # untrimmed envelope cross-correlation over all lags (lower = better -> return -max corr)
    def env(x):
        f, P = spec(x)
        E = np.log(P.sum(0) + 1e-4 * P.sum(0).max())
        return (E - E.mean()) / E.std()
    r = env(xs[0])
    out = []
    for o in xs[1:]:
        e = env(o)
        c = np.correlate(e, r, 'full') / min(len(e), len(r))
        out.append(-c.max())
    return out


def report(name, fn, Q=range(1, 25)):
    picks = []
    t0 = time.time()
    for q in Q:
        xs = DATA[q]
        sc = np.array(fn(xs))
        o = np.argsort(sc)
        best = o[0]
        # margin: (2nd - best) / (spread of others)
        marg = (sc[o[1]] - sc[o[0]]) / (np.std(sc) + 1e-12)
        picks.append(best + 1)
        print(f'  q{q:02d} pick={best+1} margin={marg:5.2f} scores=' + ' '.join(f'{v:.4f}' for v in sc))
    print(name, 'picks', picks, f'{time.time()-t0:.1f}s')
    return picks


DATA = {q: load(q) for q in range(1, 25)}
if __name__ == '__main__':
    res = {}
    res['mel24cos'] = report('mel24cos', m_mel_dtw)
    res['env_dtw'] = report('env_dtw', m_env_dtw)
    res['env_xcorr'] = report('env_xcorr', m_env_xcorr)
    json.dump({k: [int(v) for v in vs] for k, vs in res.items()}, open(f'{BASE}/work/res1.json', 'w'))
