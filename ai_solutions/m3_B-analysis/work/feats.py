import io, wave
import numpy as np
from scipy.signal import stft, lfilter
from scipy.linalg import solve_toeplitz

SR = 22050
HOP = 220  # 10 ms


def read(b):
    w = wave.open(io.BytesIO(b))
    sr = w.getframerate(); n = w.getnframes(); ch = w.getnchannels()
    x = np.frombuffer(w.readframes(n), dtype='<i2').astype(np.float64)
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    if sr != SR:
        from scipy.signal import resample_poly
        x = resample_poly(x, SR, sr)
    return x / (np.abs(x).max() + 1e-9)


def spec(x, nfft=1024):
    f, t, Z = stft(x, SR, nperseg=nfft, noverlap=nfft - HOP, boundary=None, padded=False)
    return f, np.abs(Z) ** 2  # (F, T)


def trim(P, rel_db=-35):
    e = 10 * np.log10(P.sum(0) + 1e-12)
    m = e > e.max() + rel_db
    idx = np.where(m)[0]
    return idx[0], idx[-1] + 1


def melfb(f, nb=40, fmin=80, fmax=5000):
    mel = lambda h: 2595 * np.log10(1 + h / 700)
    imel = lambda m: 700 * (10 ** (m / 2595) - 1)
    pts = imel(np.linspace(mel(fmin), mel(fmax), nb + 2))
    W = np.zeros((nb, len(f)))
    for i in range(nb):
        l, c, r = pts[i], pts[i + 1], pts[i + 2]
        W[i] = np.clip(np.minimum((f - l) / (c - l), (r - f) / (r - c)), 0, None)
    return W


def dtw(D, band=None):
    n, m = D.shape
    C = np.full((n + 1, m + 1), np.inf)
    C[0, 0] = 0
    L = np.zeros((n + 1, m + 1))
    for i in range(1, n + 1):
        prev = C[i - 1]
        cur = C[i]
        di = D[i - 1]
        # vectorised over j is awkward due to cur[j-1]; do loop via cumulative trick
        a = prev[1:]          # from (i-1, j)
        b = prev[:-1]         # from (i-1, j-1)
        best = np.minimum(a, b)
        tmp = di + best
        # horizontal moves: cur[j] = min(tmp[j], cur[j-1] + di[j])
        out = np.empty(m)
        run = np.inf
        for j in range(m):
            run = min(tmp[j], run + di[j])
            out[j] = run
        cur[1:] = out
    return C[n, m] / (n + m)
