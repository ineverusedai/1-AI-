import torch, torch.nn as nn, torch.nn.functional as Fn
import numpy as np
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
C2I = {c: i for i, c in enumerate(ALPHABET)}
R0, R1 = 72, 184   # text rows (at 244 scale); measured text bbox rows 165..352 of 488

def prep(x244, half=True):
    """x244: (N,3,244,244) motion feature -> cropped network input."""
    x = np.asarray(x244, dtype=np.float32)[:, :, R0:R1, :]
    if half:
        n, c, h, w = x.shape
        x = x.reshape(n, c, h // 2, 2, w // 2, 2).mean((3, 5))
    # per-sample, per-channel standardization (removes codec-induced offset/scale gap
    # between real-mp4 features and in-memory synthetic features)
    x = (x - x.mean((2, 3), keepdims=True)) / (x.std((2, 3), keepdims=True) + 1e-5)
    return x.astype(np.float32)

def block(i, o):
    return nn.Sequential(nn.Conv2d(i, o, 3, padding=1, bias=False), nn.BatchNorm2d(o), nn.ReLU(inplace=True),
                         nn.Conv2d(o, o, 3, padding=1, bias=False), nn.BatchNorm2d(o), nn.ReLU(inplace=True))

class Net(nn.Module):
    def __init__(self, nc=len(ALPHABET), L=4, w=32):
        super().__init__()
        self.f = nn.Sequential(block(3, w), nn.MaxPool2d(2), block(w, 2 * w), nn.MaxPool2d(2),
                               block(2 * w, 4 * w), nn.MaxPool2d(2), block(4 * w, 6 * w))
        self.pool = nn.AdaptiveAvgPool2d((2, 8))
        self.head = nn.Sequential(nn.Flatten(), nn.Dropout(0.3), nn.Linear(6 * w * 16, 512), nn.ReLU(inplace=True),
                                  nn.Dropout(0.3), nn.Linear(512, L * nc))
        self.L, self.nc = L, nc
    def forward(self, x):
        return self.head(self.pool(self.f(x))).view(-1, self.L, self.nc)

def score_options(logits, options):
    """logits (L,nc) -> sum of per-position log-probs for each option."""
    lp = Fn.log_softmax(logits, -1)
    return [sum(lp[k, C2I[c]].item() if c in C2I else -1e9 for k, c in enumerate(o)) for o in options]
