"""MVCAP L1 solver (approach B): motion-compensated residual features + CNN trained on
self-generated labeled data from the official generator. solve() picks the option with the
highest sum of per-position character log-likelihoods."""
import os, sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import numpy as np, torch
torch.set_num_threads(2)
from feat import decode_mp4_bytes, motion_feature
from model import Net, prep, score_options

_ck = torch.load(os.path.join(_HERE, "model.pt"), map_location="cpu")
_NET = Net(w=_ck["width"]); _NET.load_state_dict(_ck["state"]); _NET.eval()

def solve(video_mp4: bytes, options: list[str]) -> str:
    frames = decode_mp4_bytes(video_mp4)
    x = torch.from_numpy(prep(motion_feature(frames, out=244)[None]))
    with torch.no_grad():
        logits = _NET(x)[0]
    s = score_options(logits, [o.upper() for o in options])
    return options[int(np.argmax(s))]
