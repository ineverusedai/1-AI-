import numpy as np
from scipy.signal import resample_poly, stft, get_window
from scipy.linalg import solve_toeplitz
from feats import spec, trim, SR, HOP

def lpc_formants(x, order=12, nf=3):
    y = resample_poly(x, 1, 2)  # 11025
    sr = SR // 2
    y = np.append(y[0], y[1:] - 0.97 * y[:-1])
    hop = HOP // 2; win = int(0.025 * sr)
    w = np.hamming(win)
    nfr = 1 + (len(y) - win) // hop
    F = np.full((nfr, nf), np.nan); E = np.zeros(nfr)
    for i in range(nfr):
        s = y[i*hop:i*hop+win] * w
        E[i] = np.sum(s**2)
        r = np.correlate(s, s, 'full')[win-1:win+order]
        if r[0] <= 1e-10: continue
        r[0] *= 1.0001
        a = solve_toeplitz(r[:-1], r[1:])
        roots = np.roots(np.concatenate([[1], -a]))
        roots = roots[np.imag(roots) > 0]
        fr = np.angle(roots) * sr / (2*np.pi)
        bw = -np.log(np.abs(roots)) * sr / np.pi
        ok = (fr > 150) & (fr < 4800) & (bw < 500)
        fr = np.sort(fr[ok])[:nf]
        F[i, :len(fr)] = fr
    return F, E

def sine_tracks(x, nf=3, nfft=1024):
    f, P = spec(x, nfft)
    A = np.sqrt(P)
    T = A.shape[1]
    F = np.full((T, nf), np.nan); E = P.sum(0)
    for t in range(T):
        c = A[:, t]
        pk = np.where((c[1:-1] > c[:-2]) & (c[1:-1] >= c[2:]))[0] + 1
        if len(pk) == 0: continue
        pk = pk[c[pk] > 0.03 * c.max()]
        pk = pk[np.argsort(c[pk])[::-1]]
        df = f[1]-f[0]; sel = []
        for k in pk:
            if all(abs(k-j)*df > 250 for j in sel): sel.append(k)
            if len(sel) == nf: break
        pk = sel
        # parabolic interp
        fr = []
        for k in pk:
            a, b, g = np.log(c[k-1]+1e-12), np.log(c[k]+1e-12), np.log(c[k+1]+1e-12)
            d = 0.5*(a-g)/(a-2*b+g+1e-12)
            fr.append((k+d) * (f[1]-f[0]))
        fr = np.sort(fr)
        F[t, :len(fr)] = fr
    return F, E
