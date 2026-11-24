"""Sine-wave-speech captcha solver (mission 3, method B).

solve(ref_wav, option_wavs) -> 1..4

Content-only scoring (sample counts / file metadata are NOT used):
  A  : log-mel spectrogram (100-5000 Hz, 40 bands, 10 ms hop), per-band mean removed,
       cosine-distance DTW between reference and option  (lower = better)
  A2 : same log-mel, frame-linear alignment with +-150 ms lag search, global Pearson
       correlation over non-silent frames                 (higher = better)
  B  : log RMS envelope (10 ms), best Pearson correlation over +-200 ms lags (higher = better)
Each method's 4 scores are z-normalised across the options and summed; argmax wins.
"""
import io
import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal as ss

SR = 22050
HOP = 220
NFFT = 512
_FB = None


def _load(b):
    sr, x = wavfile.read(io.BytesIO(b))
    x = x.astype(np.float64)
    if x.ndim > 1:
        x = x.mean(1)
    if sr != SR:
        from math import gcd
        g = gcd(int(sr), SR)
        x = ss.resample_poly(x, SR // g, int(sr) // g)
    x /= (np.abs(x).max() + 1e-9)
    return x


def _melfb(nb=40, fmin=100, fmax=5000):
    mel = lambda f: 2595 * np.log10(1 + f / 700)
    imel = lambda m: 700 * (10 ** (m / 2595) - 1)
    pts = imel(np.linspace(mel(fmin), mel(fmax), nb + 2))
    fr = np.fft.rfftfreq(NFFT, 1 / SR)
    W = np.zeros((nb, len(fr)))
    for k in range(nb):
        a, b, c = pts[k:k + 3]
        W[k] = np.clip(np.minimum((fr - a) / (b - a), (c - fr) / (c - b)), 0, None)
    return W


def _logmel(x):
    global _FB
    if _FB is None:
        _FB = _melfb()
    _, _, S = ss.stft(x, SR, nperseg=NFFT, noverlap=NFFT - HOP, boundary=None)
    return np.log(_FB @ (np.abs(S) ** 2) + 1e-6).T  # frames x bands


def _env(x):
    n = len(x) // HOP
    e = np.sqrt((x[:n * HOP].reshape(n, HOP) ** 2).mean(1))
    return np.log(e + 1e-4)


def _dtw(C):
    n, m = C.shape
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        Ci = C[i - 1]
        prev = D[i - 1]
        best = np.minimum(prev[:-1], prev[1:]) + Ci
        cur = D[i]
        acc = np.inf
        for j in range(m):
            v = best[j]
            l = acc + Ci[j]
            if l < v:
                v = l
            cur[j + 1] = v
            acc = v
    return D[n, m] / (n + m)


def _nonsilent(L):
    e = L.max(1)
    return e > e.max() - np.log(1e4)


def _score_A(R, O):
    a = R[_nonsilent(R)]
    b = O[_nonsilent(O)]
    a = a - a.mean(0)
    b = b - b.mean(0)
    a = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-9)
    b = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return _dtw(1 - a @ b.T)


def _best_lag_corr(R, O, maxlag, mask_fn=None):
    best = -1.0
    for lag in range(-maxlag, maxlag + 1):
        a = R[max(0, lag):]
        b = O[max(0, -lag):]
        n = min(len(a), len(b))
        if n < 10:
            continue
        a = a[:n]
        b = b[:n]
        if mask_fn is not None:
            k = mask_fn(a)
            a = a[k]
            b = b[k]
        a = a - a.mean(0)
        b = b - b.mean(0)
        c = float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-12))
        if c > best:
            best = c
    return best


def _z(v):
    v = np.asarray(v, dtype=float)
    return (v - v.mean()) / (v.std() + 1e-9)


def scores(ref_wav, option_wavs):
    xr = _load(ref_wav)
    Lr = _logmel(xr)
    Er = _env(xr)
    sA, sA2, sB = [], [], []
    for ob in option_wavs:
        xo = _load(ob)
        Lo = _logmel(xo)
        Eo = _env(xo)
        sA.append(-_score_A(Lr, Lo))
        sA2.append(_best_lag_corr(Lr, Lo, 15, _nonsilent))
        sB.append(_best_lag_corr(Er, Eo, 20))
    total = _z(sA) + _z(sA2) + _z(sB)
    return total, (np.array(sA), np.array(sA2), np.array(sB))


def solve(ref_wav: bytes, option_wavs: list) -> int:
    total, _ = scores(ref_wav, option_wavs)
    return int(np.argmax(total)) + 1


if __name__ == '__main__':
    import json, os, sys, time
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'problems')
    qs = json.load(open(os.path.join(base, 'questions.json')))
    for q in qs:
        ref = open(os.path.join(base, q['ref']), 'rb').read()
        opts = [open(os.path.join(base, p), 'rb').read() for p in q['options']]
        t = time.time()
        total, (a, a2, b) = scores(ref, opts)
        dt = time.time() - t
        o = np.argsort(-total)
        print('q%02d pick=%d  zsum=%s  margin=%.2f  picksA/A2/B=%d%d%d  %.2fs' % (
            q['q'], o[0] + 1, np.round(total, 2), total[o[0]] - total[o[1]],
            np.argmax(a) + 1, np.argmax(a2) + 1, np.argmax(b) + 1, dt))
