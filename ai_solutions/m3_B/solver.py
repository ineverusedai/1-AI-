"""Sine-wave-speech CAPTCHA solver (learned asymmetric siamese frame metric + DTW).

solve(ref_wav: bytes, option_wavs: list[bytes]) -> int  (1..4)
Model (models/metric.pt) is trained on the labeled training split only (see notes_B.md).
"""
import os, sys
import numpy as np
import torch

torch.set_num_threads(2)
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from feats import read_wav, logmel  # noqa: E402
from dtw import dtw_cost  # noqa: E402
from model import Metric, prep  # noqa: E402

_NET = Metric()
_NET.load_state_dict(torch.load(os.path.join(_HERE, 'models', 'metric.pt'), map_location='cpu'))
_NET.eval()


def _fit_len(X, n):
    idx = np.linspace(0, len(X) - 1, n)
    lo = np.floor(idx).astype(int); hi = np.minimum(lo + 1, len(X) - 1); w = (idx - lo)[:, None]
    return (X[lo] * (1 - w) + X[hi] * w).astype(np.float32)


def _feat(b):
    return prep(logmel(read_wav(b)))


@torch.no_grad()
def scores(ref_wav, option_wavs):
    r = _feat(ref_wav)
    er = _NET.er(torch.from_numpy(r))
    out = []
    for ob in option_wavs:
        o = _feat(ob)
        n, m = len(r), len(o)
        if m > 1.9 * n:
            o = _fit_len(o, int(1.9 * n))
        elif n > 1.9 * m:
            o = _fit_len(o, int(n / 1.9) + 1)
        C = (1 - er @ _NET.eo(torch.from_numpy(o)).t()).numpy().astype(np.float64)
        out.append(dtw_cost(C))
    return np.array(out)


def solve(ref_wav: bytes, option_wavs: list) -> int:
    return int(np.argmin(scores(ref_wav, option_wavs))) + 1
