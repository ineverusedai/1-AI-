"""Sine-wave-speech captcha solver (mission 3, method B).

solve(ref_wav, option_wavs) -> 1..4

Idea: the correct option is a sine-wave re-synthesis (F1/F2/F3 tones) of the same
sentence, so its spectral-envelope / formant trajectory follows the reference over
time.  Each clip is trimmed by energy (leading/trailing silence of any length is
removed), then compared to the reference with DTW (so tempo / offset differences do
not matter) using three independent feature sets:

  1. MFCC-like spectral envelope (mel 30 bands <= 4 kHz, DCT c1..c7, per-utterance CMVN), Euclidean
  2. log-mel 24 bands <= 4.5 kHz, per-band CMVN, cosine distance
  3. explicit formant tracks: LPC formants (ref) vs. sine-tone peaks (option),
     |log f| distance + energy contour

Each method's 4 DTW costs are z-scored across the options and summed; the
lowest combined cost wins.  Only audio samples are used (no file names, sizes,
lengths, or header metadata).
"""
import io
import os
import wave

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")  # tiny matrices: threading only adds overhead

import numpy as np
from scipy.fft import dct
from scipy.signal import resample_poly, stft
from scipy.spatial.distance import cdist

_FB = {}

SR = 22050
HOP = 220  # 10 ms


# ---------------------------------------------------------------- I/O
def _read(b):
    w = wave.open(io.BytesIO(b))
    sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
    raw = w.readframes(n)
    if sw == 2:
        x = np.frombuffer(raw, dtype='<i2').astype(np.float64)
    elif sw == 1:
        x = np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128
    elif sw == 4:
        x = np.frombuffer(raw, dtype='<i4').astype(np.float64)
    else:  # 24-bit
        a = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        x = (a[:, 0].astype(np.int32) | (a[:, 1].astype(np.int32) << 8) | (a[:, 2].astype(np.int32) << 16))
        x = np.where(x >= 1 << 23, x - (1 << 24), x).astype(np.float64)
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    if sr != SR:
        g = np.gcd(SR, sr)
        x = resample_poly(x, SR // g, sr // g)
    return x / (np.abs(x).max() + 1e-12)


def _spec(x, nfft=1024):
    if len(x) < nfft:
        x = np.pad(x, (0, nfft - len(x)))
    f, _, Z = stft(x, SR, nperseg=nfft, noverlap=nfft - HOP, boundary=None, padded=False)
    return f, np.abs(Z) ** 2


def _thr(e_db, rel_db=-35.0):
    """Activity threshold (dB): 35 dB below the loudest frame, raised above an
    estimated noise floor when the padding is noisy instead of digital silence."""
    floor = np.percentile(e_db, 10)
    return min(max(e_db.max() + rel_db, floor + 10.0), e_db.max() - 20.0)


def _trim_idx(f, P):
    band = (f >= 100) & (f <= 4000)
    e = 10 * np.log10(P[band].sum(0) + 1e-20)
    idx = np.where(e > _thr(e))[0]
    return idx[0], idx[-1] + 1


def _melfb(f, nb, fmin, fmax):
    key = (len(f), nb, fmin, fmax)
    if key in _FB:
        return _FB[key]
    mel = lambda h: 2595 * np.log10(1 + h / 700)
    imel = lambda m: 700 * (10 ** (m / 2595) - 1)
    pts = imel(np.linspace(mel(fmin), mel(fmax), nb + 2))
    W = np.zeros((nb, len(f)))
    for i in range(nb):
        l, c, r = pts[i], pts[i + 1], pts[i + 2]
        W[i] = np.clip(np.minimum((f - l) / (c - l), (r - f) / (r - c)), 0, None)
    _FB[key] = W
    return W


# ---------------------------------------------------------------- DTW
def _dtw(D):
    """Symmetric DTW (steps (1,0),(0,1),(1,1)), cost normalised by n+m.
    Row recursion vectorised with a cumulative-min trick."""
    n, m = D.shape
    prev = np.full(m + 1, np.inf)
    prev[0] = 0.0
    for i in range(n):
        d = D[i]
        tmp = d + np.minimum(prev[1:], prev[:-1])
        S = np.cumsum(d)
        cur = np.empty(m + 1)
        cur[0] = np.inf
        cur[1:] = np.minimum.accumulate(tmp - S) + S
        prev = cur
    return prev[m] / (n + m)


def _cmvn(M):
    M = M - M.mean(1, keepdims=True)
    return M / (M.std(1, keepdims=True) + 1e-9)


# ---------------------------------------------------------------- features
def _mel_and_mfcc(f, P):
    s, e = _trim_idx(f, P)
    W30, W24 = _melfb(f, 30, 100, 4000), _melfb(f, 24, 100, 4500)
    B30, B24 = W30 @ P, W24 @ P
    # log floor: tiny fraction of the max, or the per-band noise floor if the clip is noisy
    fl30 = np.maximum(1e-5 * B30.max(), np.percentile(B30, 10, axis=1, keepdims=True))
    fl24 = np.maximum(1e-6 * B24.max(), np.percentile(B24, 10, axis=1, keepdims=True))
    # MFCC-like envelope
    M30 = np.log(B30[:, s:e] + fl30)
    C = _cmvn(dct(M30, axis=0, norm='ortho')[1:8]).T
    # log-mel 24
    M24 = _cmvn(np.log(B24[:, s:e] + fl24)).T
    M24 = M24 / (np.linalg.norm(M24, axis=1, keepdims=True) + 1e-9)
    return C, M24


def _fill(F):
    F = F.copy()
    t = np.arange(len(F))
    for k in range(F.shape[1]):
        v = F[:, k]
        ok = ~np.isnan(v)
        if ok.sum() >= 2:
            F[:, k] = np.interp(t, t[ok], v[ok])
        else:
            F[:, k] = v[ok].mean() if ok.any() else 1000.0 * (k + 1)
    return F


def _formant_feat(F, E, we=0.5):
    e = 10 * np.log10(E / (E.max() + 1e-20) + 1e-12)
    th = _thr(e)
    idx = np.where(e > th)[0]
    s, t = idx[0], idx[-1] + 1
    F, e = F[s:t].copy(), e[s:t]
    F[e < th + 5] = np.nan
    e = e - th - 35.0  # so that clipping at -40..0 is relative to the threshold
    L = np.log(_fill(F))
    return np.column_stack([L * np.array([1.0, 1.0, 0.5]), we * np.clip(e, -40, 0) / 40.0])


def _lpc_formants(x, order=12, nf=3):
    y = resample_poly(x, 1, 2)
    sr = SR / 2
    y = np.append(y[0], y[1:] - 0.97 * y[:-1])
    hop, win = HOP // 2, int(0.025 * sr)
    if len(y) < win:
        y = np.pad(y, (0, win - len(y)))
    w = np.hamming(win)
    nfr = 1 + (len(y) - win) // hop
    fr_idx = np.arange(win)[None, :] + hop * np.arange(nfr)[:, None]
    frames = y[fr_idx] * w
    E = (frames ** 2).sum(1)
    F = np.full((nfr, nf), np.nan)
    act = np.where(E >= E.max() * 1e-4)[0]
    if len(act) == 0:
        return F, E
    fa = frames[act]
    # autocorrelation lags 0..order for all active frames at once
    R = np.stack([(fa[:, :win - k] * fa[:, k:]).sum(1) for k in range(order + 1)], 1)
    R[:, 0] *= 1.0001
    # batched Levinson-Durbin: A(z) = 1 + a1 z^-1 + ... + ap z^-p
    nA = len(act)
    a = np.zeros((nA, order + 1)); a[:, 0] = 1.0
    err = R[:, 0].copy()
    for i in range(1, order + 1):
        acc = (a[:, :i] * R[:, i:0:-1]).sum(1)
        k = -acc / np.maximum(err, 1e-20)
        a_new = a.copy()
        a_new[:, 1:i + 1] = a[:, 1:i + 1] + k[:, None] * a[:, i - 1::-1][:, :i]
        a = a_new
        err = err * (1 - k ** 2)
    # roots of A(z) via batched companion-matrix eigenvalues
    Cm = np.zeros((nA, order, order))
    Cm[:, 0, :] = -a[:, 1:]
    Cm[:, np.arange(1, order), np.arange(order - 1)] = 1.0
    roots = np.linalg.eigvals(Cm)
    fr = np.angle(roots) * sr / (2 * np.pi)
    bw = -np.log(np.abs(roots) + 1e-12) * sr / np.pi
    ok = (np.imag(roots) > 0) & (fr > 150) & (fr < 4800) & (bw < 500)
    fr = np.where(ok, fr, np.inf)
    fr = np.sort(fr, 1)[:, :nf]
    fr[np.isinf(fr)] = np.nan
    F[act] = fr
    return F, E


def _sine_tracks(f, P, nf=3):
    A = np.sqrt(P)
    df = f[1] - f[0]
    T = A.shape[1]
    F = np.full((T, nf), np.nan)
    amax = A.max(0)
    is_pk = np.zeros_like(A, dtype=bool)
    is_pk[1:-1] = (A[1:-1] > A[:-2]) & (A[1:-1] >= A[2:]) & (A[1:-1] > 0.03 * amax)
    for t in range(T):
        pk = np.where(is_pk[:, t])[0]
        if len(pk) == 0:
            continue
        c = A[:, t]
        pk = pk[np.argsort(c[pk])[::-1]]
        sel = []
        for k in pk:
            if all(abs(k - j) * df > 250 for j in sel):
                sel.append(k)
                if len(sel) == nf:
                    break
        fr = []
        for k in sel:
            a, b, g = np.log(c[k - 1] + 1e-12), np.log(c[k] + 1e-12), np.log(c[k + 1] + 1e-12)
            den = a - 2 * b + g
            d = 0.5 * (a - g) / den if den != 0 else 0.0
            fr.append((k + d) * df)
        fr = np.sort(fr)
        F[t, :len(fr)] = fr
    band = (f >= 100) & (f <= 4000)
    return F, P[band].sum(0)


def _resynth(F, E):
    """Sine-wave-speech re-synthesis of the reference from its LPC formant tracks
    (3 tones, amplitudes 1, .5, .25), so that it can be compared sine-vs-sine."""
    F = _fill(F)
    hop = HOP  # LPC frames are HOP/2 samples at SR/2 == HOP samples at SR
    n = len(F) * hop
    t = np.arange(n) / hop
    fi = np.arange(len(F))
    e = 10 * np.log10(E / (E.max() + 1e-20) + 1e-12)
    amp = np.sqrt(E / (E.max() + 1e-20))
    amp[e < _thr(e)] = 0.0
    a = np.interp(t, fi, amp)
    y = np.zeros(n)
    for k, g in enumerate([1.0, 0.5, 0.25]):
        fk = np.interp(t, fi, F[:, k])
        y += g * a * np.sin(2 * np.pi * np.cumsum(fk) / SR)
    return y / (np.abs(y).max() + 1e-12)


# ---------------------------------------------------------------- scoring
def _z(v):
    v = np.asarray(v, dtype=np.float64)
    return (v - v.mean()) / (v.std() + 1e-12)


def scores(ref_wav, option_wavs):
    """Return dict of per-method DTW costs (lower = more similar) and combined z-score."""
    xr = _read(ref_wav)
    xo = [_read(b) for b in option_wavs]

    Cr, Mr = _mel_and_mfcc(*_spec(xr))
    Fr, Er = _lpc_formants(xr)
    Rf = _formant_feat(Fr, Er)
    _, Sr = _mel_and_mfcc(*_spec(_resynth(Fr, Er)))
    s_mfcc, s_mel, s_form, s_syn = [], [], [], []
    for x in xo:
        f, P = _spec(x)
        C, M = _mel_and_mfcc(f, P)
        s_mfcc.append(_dtw(cdist(Cr, C)))
        s_mel.append(_dtw(1.0 - Mr @ M.T))
        Of = _formant_feat(*_sine_tracks(f, P))
        s_form.append(_dtw(cdist(Rf, Of, 'cityblock')))
        s_syn.append(_dtw(1.0 - Sr @ M.T))
    comb = _z(s_mfcc) + _z(s_mel) + _z(s_form) + _z(s_syn)
    return {'mfcc': np.array(s_mfcc), 'mel': np.array(s_mel), 'formant': np.array(s_form),
            'resynth': np.array(s_syn), 'combined': comb}


def solve(ref_wav: bytes, option_wavs: list) -> int:
    sc = scores(ref_wav, option_wavs)['combined']
    return int(np.argmin(sc)) + 1
