import sys; sys.path.insert(0, sys.path[0])
from analyze import *
from scipy.fft import dct

def mfcc_feat(x, nb=30, nc=13, fmax=5000):
    f, P = spec(x)
    s, e = trim(P)
    W = melfb(f, nb, 100, fmax)
    M = np.log(W @ P[:, s:e] + 1e-5 * P.max())
    C = dct(M, axis=0, norm='ortho')[1:nc]
    C = C - C.mean(1, keepdims=True)
    C = C / (C.std(1, keepdims=True) + 1e-9)
    return C.T

def m_mfcc(xs, nb=30, nc=13, fmax=5000):
    R = mfcc_feat(xs[0], nb, nc, fmax)
    return [dtw(eucD(R, mfcc_feat(o, nb, nc, fmax))) for o in xs[1:]]

if __name__ == '__main__':
    import functools
    for args in [(30,13,5000),(30,8,4000),(40,20,6000)]:
        report(f'mfcc{args}', functools.partial(m_mfcc, nb=args[0], nc=args[1], fmax=args[2]))
    for nb, fm in [(16,4000),(32,5500)]:
        report(f'mel{nb},{fm}', functools.partial(m_mel_dtw, nb=nb, fmax=fm))
