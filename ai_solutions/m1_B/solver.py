"""미션 1 글자 캡차 풀이기: solve(png_bytes) -> 5글자 대문자/숫자.
모델(model_final.pt)은 import 시 한 번만 로드한다."""
import io, os
import numpy as np
import torch
from PIL import Image
from model import CRNN, CHARS, BLANK
from spec import Spec, char_centers, crop, to_in

_DIR = os.path.dirname(os.path.abspath(__file__))
_H, _W = 48, 144
torch.set_num_threads(int(os.environ.get("SOLVER_THREADS", "1")))
_MODEL = CRNN()
_MODEL.load_state_dict(torch.load(os.path.join(_DIR, "model_final.pt"), map_location="cpu"))
_MODEL.eval()
# O/0 전문 분류기: 축소 이미지에서는 O 와 0 구별이 어려워, 전체 해상도 조각으로 다시 판정한다.
_SPEC = None
if os.path.exists(os.path.join(_DIR, "spec_final.pt")) and not os.environ.get("SOLVER_NO_SPEC"):
    _SPEC = Spec()
    _SPEC.load_state_dict(torch.load(os.path.join(_DIR, "spec_final.pt"), map_location="cpu"))
    _SPEC.eval()
_O, _Z = CHARS.index("O"), CHARS.index("0")
_TTA = [float(v) for v in os.environ.get("SOLVER_TTA", "-0.5,0,0.5").split(",")]  # 프레임 단위 이동량

def _prep(png_bytes):
    full = Image.open(io.BytesIO(png_bytes)).convert("RGB").convert("L")
    g = np.asarray(full.resize((_W, _H), Image.BILINEAR), dtype=np.float32)
    x = torch.from_numpy((g / 255.0 - 0.5) / 0.5)
    return x[None, None], np.asarray(full, dtype=np.uint8)

def _decode5(lp):
    """lp: (T,NC) 로그확률. 탐욕 디코딩; 길이가 5가 아니면 길이 5로 제한한 최적 경로(Viterbi)를 쓴다."""
    best = lp.argmax(-1).tolist()
    out, prev = [], BLANK
    for k in best:
        if k != prev and k != BLANK:
            out.append(k)
        prev = k
    if len(out) == 5:
        return out
    return _viterbi_len5(lp)

def _viterbi_len5(lp):
    # 상태: (출력된 글자 수 n, 현재 프레임이 blank 인지/어떤 글자인지). 글자 수 정확히 5개인 최대확률 정렬 경로.
    lp = lp.numpy().astype(np.float64)
    T, NC = lp.shape
    L = 5
    NEG = -1e18
    # dp_b[n]: n글자 출력 후 현재 blank;  dp_c[n, k]: n글자 출력, 현재 프레임이 글자 k(n번째 글자)
    dp_b = np.full(L + 1, NEG); dp_c = np.full((L + 1, NC), NEG)
    bp = []
    dp_b[0] = lp[0, BLANK]; dp_c[1, :BLANK] = lp[0, :BLANK]
    for t in range(1, T):
        nb = np.full(L + 1, NEG); nc = np.full((L + 1, NC), NEG)
        bb = np.zeros(L + 1, np.int64); bc = np.zeros((L + 1, NC, 2), np.int64)
        for n in range(L + 1):
            # -> blank
            cands = [dp_b[n], dp_c[n, :BLANK].max()]
            j = int(np.argmax(cands)); nb[n] = cands[j] + lp[t, BLANK]
            bb[n] = -1 if j == 0 else int(dp_c[n, :BLANK].argmax())
            # 같은 글자 유지 (n 그대로)
            stay = dp_c[n, :BLANK]
            # 새 글자 (n-1 -> n): blank 에서 오거나, 다른 글자에서 옴
            if n >= 1:
                from_b = np.full(BLANK, dp_b[n - 1])
                prevc = dp_c[n - 1, :BLANK]
                # 다른 글자에서 오는 최댓값 (자기 자신 제외): top-2 트릭
                order = np.argsort(prevc)[::-1]
                m1, m2 = prevc[order[0]], prevc[order[1]]
                from_c = np.where(np.arange(BLANK) == order[0], m2, m1)
                src_c = np.where(np.arange(BLANK) == order[0], order[1], order[0])
            else:
                from_b = np.full(BLANK, NEG); from_c = np.full(BLANK, NEG); src_c = np.zeros(BLANK, np.int64)
            allc = np.stack([stay, from_b, from_c])
            j = allc.argmax(0)
            nc[n, :BLANK] = allc.max(0) + lp[t, :BLANK]
            bc[n, :BLANK, 0] = j
            bc[n, :BLANK, 1] = src_c
        bp.append((bb, bc)); dp_b, dp_c = nb, nc
    # 역추적
    if dp_b[L] >= dp_c[L, :BLANK].max():
        state = (L, -1)
    else:
        state = (L, int(dp_c[L, :BLANK].argmax()))
    seq = []
    for t in range(T - 1, 0, -1):
        bb, bc = bp[t - 1]
        n, k = state
        if k == -1:
            pk = int(bb[n]); state = (n, pk if pk >= 0 else -1)
        else:
            j = int(bc[n, k, 0])
            if j == 0: state = (n, k)
            elif j == 1: seq.append(k); state = (n - 1, -1)
            else: seq.append(k); state = (n - 1, int(bc[n, k, 1]))
    n, k = state
    if k != -1: seq.append(k)
    return seq[::-1]

@torch.no_grad()
def solve(png_bytes: bytes) -> str:
    x, full = _prep(png_bytes)
    lp = _MODEL(x)[:, 0]
    cc = char_centers(lp)
    if len(cc) == 5:
        out = [k for k, _ in cc]
        if _SPEC is not None:
            idx = [i for i, k in enumerate(out) if k in (_O, _Z)]
            if idx:
                # 시험시 증강: 중심을 조금씩 옮긴 조각들의 로짓 평균
                crops = np.stack([crop(full, cc[i][1] + d) for i in idx for d in _TTA])
                lg = _SPEC(to_in(torch.from_numpy(crops))).reshape(len(idx), len(_TTA), 2).mean(1)
                pz = lg.argmax(1).tolist()
                for i, z in zip(idx, pz):
                    out[i] = _Z if z == 1 else _O
    else:
        out = _viterbi_len5(lp)
    return "".join(CHARS[k] for k in out)
