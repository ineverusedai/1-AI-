"""O/0 전문 분류기 (전체 해상도 잘라낸 조각 사용)"""
import numpy as np, torch, torch.nn as nn
from PIL import Image
from model import BLANK

CW = 96          # 잘라낼 폭 (전체 해상도 픽셀)
T_FRAMES = 36

def cbr(i, o):
    return [nn.Conv2d(i, o, 3, padding=1, bias=False), nn.BatchNorm2d(o), nn.ReLU(inplace=True)]

class Spec(nn.Module):
    def __init__(self):
        super().__init__()
        self.f = nn.Sequential(*cbr(1, 24), nn.MaxPool2d(2),          # 45x48
                               *cbr(24, 48), nn.MaxPool2d(2),         # 22x24
                               *cbr(48, 64), *cbr(64, 64), nn.MaxPool2d(2),  # 11x12
                               *cbr(64, 96), *cbr(96, 96),
                               nn.AdaptiveAvgPool2d(1), nn.Flatten(),
                               nn.Dropout(0.2), nn.Linear(96, 2))
    def forward(self, x):
        return self.f(x)

def char_centers(lp_tb):
    """lp (T,NC) -> 탐욕 경로에서 각 출력 글자의 (글자, 중심 프레임) 리스트"""
    best = lp_tb.argmax(-1).tolist()
    out, prev = [], BLANK
    for t, k in enumerate(best):
        if k != BLANK and k == prev:
            out[-1][2].append(t)
        elif k != BLANK:
            out.append([k, None, [t]])
        prev = k
    return [(k, float(np.mean(ts))) for k, _, ts in out]

def crop(full_gray, tc):
    """full_gray (90,280) uint8, tc 중심프레임 -> (90,CW) uint8"""
    x = int(round((tc + 0.5) * 280 / T_FRAMES))
    pad = np.pad(full_gray, ((0, 0), (CW, CW)), mode="edge")
    return pad[:, x + CW - CW // 2: x + CW + CW // 2]

def to_in(c):
    return (torch.as_tensor(c).float().unsqueeze(-3) / 255.0 - 0.5) / 0.5
