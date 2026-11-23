import torch, torch.nn as nn

CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
NC = len(CHARS) + 1  # +blank (index 36)
BLANK = len(CHARS)

def cbr(i, o):
    return [nn.Conv2d(i, o, 3, padding=1, bias=False), nn.BatchNorm2d(o), nn.ReLU(inplace=True)]

class CRNN(nn.Module):
    """입력 (B,1,48,144) -> (T=36,B,NC) 로그확률 (CTC).
    GRU 는 CPU 학습에서 너무 느려서(스텝시간 ~40%) 1D 합성곱 시퀀스 헤드로 대체."""
    def __init__(self, w=(32, 64, 128, 160), hid=256):
        super().__init__()
        a, b, c, d = w
        self.cnn = nn.Sequential(
            *cbr(1, a), nn.MaxPool2d(2),                      # 24x72
            *cbr(a, b), nn.MaxPool2d(2),                      # 12x36
            *cbr(b, c), *cbr(c, c), nn.MaxPool2d((2, 1)),     # 6x36
            *cbr(c, d), *cbr(d, d), nn.MaxPool2d((2, 1)),     # 3x36
        )
        self.seq = nn.Sequential(
            nn.Conv1d(d * 3, hid, 1), nn.BatchNorm1d(hid), nn.ReLU(inplace=True),
            nn.Conv1d(hid, hid, 5, padding=2), nn.BatchNorm1d(hid), nn.ReLU(inplace=True),
            nn.Conv1d(hid, hid, 5, padding=2), nn.BatchNorm1d(hid), nn.ReLU(inplace=True),
            nn.Dropout(0.1),
            nn.Conv1d(hid, NC, 1),
        )

    def forward(self, x):
        f = self.cnn(x)                       # B,C,3,T
        B, C, Hh, T = f.shape
        f = f.reshape(B, C * Hh, T)
        f = self.seq(f)                       # B,NC,T
        return f.permute(2, 0, 1).float().log_softmax(-1)     # T,B,NC

def greedy_decode(logp):
    """logp (T,B,NC) -> list of index lists"""
    best = logp.argmax(-1).T.tolist()
    out = []
    for seq in best:
        r, prev = [], BLANK
        for k in seq:
            if k != prev and k != BLANK:
                r.append(k)
            prev = k
        out.append(r)
    return out
