"""Shared feature extraction (used by training scripts and solver.py)."""
import io
import numpy as np
from scipy.io import wavfile

SR = 22050
NFFT = 1024
HOP = 220  # ~10 ms
NMEL = 64


def _mel(f):
    return 2595.0 * np.log10(1.0 + f / 700.0)


def _imel(m):
    return 700.0 * (10 ** (m / 2595.0) - 1.0)


def mel_fb(n_mels=NMEL, fmin=60.0, fmax=7000.0, sr=SR, nfft=NFFT):
    freqs = np.arange(nfft // 2 + 1) * sr / nfft
    pts = _imel(np.linspace(_mel(fmin), _mel(fmax), n_mels + 2))
    fb = np.zeros((n_mels, len(freqs)), np.float32)
    for i in range(n_mels):
        l, c, r = pts[i], pts[i + 1], pts[i + 2]
        up = (freqs - l) / max(c - l, 1e-6)
        dn = (r - freqs) / max(r - c, 1e-6)
        fb[i] = np.maximum(0, np.minimum(up, dn))
    fb /= fb.sum(1, keepdims=True) + 1e-9
    return fb


FB = mel_fb()
WIN = np.hanning(NFFT).astype(np.float32)


def read_wav(src):
    if isinstance(src, (bytes, bytearray)):
        src = io.BytesIO(src)
    sr, d = wavfile.read(src)
    d = d.astype(np.float32)
    if d.ndim > 1:
        d = d.mean(1)
    if d.dtype != np.float32 or np.abs(d).max() > 2:
        d = d / 32768.0
    if sr != SR:
        from scipy.signal import resample_poly
        from math import gcd
        g = gcd(sr, SR)
        d = resample_poly(d, SR // g, sr // g).astype(np.float32)
    return d


def power_spec(x):
    if len(x) < NFFT:
        x = np.pad(x, (0, NFFT - len(x)))
    n = 1 + (len(x) - NFFT) // HOP
    idx = np.arange(NFFT)[None, :] + HOP * np.arange(n)[:, None]
    fr = x[idx] * WIN
    return (np.abs(np.fft.rfft(fr, axis=1)) ** 2).astype(np.float32)


def trim(P, rel_db=-40.0):
    e = P.sum(1)
    edb = 10 * np.log10(e + 1e-12)
    thr = edb.max() + rel_db
    nz = np.nonzero(edb > thr)[0]
    if len(nz) == 0:
        return P
    return P[max(nz[0] - 2, 0): nz[-1] + 3]


def logmel(x, do_trim=True):
    P = power_spec(x)
    if do_trim:
        P = trim(P)
    M = P @ FB.T
    L = np.log(M + 1e-8)
    L = np.maximum(L, L.max() - 12.0)  # ~52 dB floor
    return L.astype(np.float32)
