"""착시 캡차 전용 풀이기.  solve(image_bytes, choices) -> choice"""
import os, numpy as np, cv2, torch, torch.nn.functional as F
from PIL import Image, ImageDraw, ImageFont
_D = os.path.dirname(os.path.abspath(__file__))
import sys; sys.path.insert(0, _D)
from prep import preprocess, decode
from model import Net

torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
_ck = torch.load(os.path.join(_D, 'model.pt'), map_location='cpu')
_SYL = _ck['syl']; _V = {c: k for k, c in enumerate(_SYL)}
_NETS = []
for sd in _ck['sds']:
    n = Net(len(_SYL), cin=2); n.load_state_dict(sd); n.eval(); _NETS.append(n)

# --- 학습 없이 쓰는 대비책: 글꼴 템플릿 매칭 (모르는 음절이 선택지에 있을 때) ---
_FONT = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
_tc = {}
def _tmpl(word, h):
    k = (word, h)
    if k not in _tc:
        f = ImageFont.truetype(_FONT, h * 4)
        bb = f.getbbox(word); w = bb[2] - bb[0] + 8; hh = bb[3] - bb[1] + 8
        im = Image.new('L', (w, hh), 0)
        ImageDraw.Draw(im).text((4 - bb[0], 4 - bb[1]), word, font=f, fill=255)
        a = cv2.resize(np.asarray(im, np.float32), (max(1, w // 4), max(1, hh // 4)), interpolation=cv2.INTER_AREA)
        _tc[k] = cv2.GaussianBlur(a, (0, 0), 1.5)
    return _tc[k]
def _tscore(img, word):
    best = -1.0
    for h in range(26, 46, 2):
        t = _tmpl(word, h)
        if t.shape[0] >= img.shape[1] or t.shape[1] >= img.shape[2]: continue
        best = max(best, float(cv2.matchTemplate(-img[0], t, cv2.TM_CCOEFF_NORMED).max()))
    return best

def solve(image_bytes: bytes, choices: list) -> str:
    choices = list(choices)
    try:
        x = preprocess(decode(image_bytes))
    except Exception:
        return choices[0]
    # 배경 설명 선택지(띄어쓰기 포함, 예: '꽃이 핀 풀밭')는 정답이 아님
    cand = [i for i, w in enumerate(choices) if ' ' not in w.strip()] or list(range(len(choices)))
    words = [choices[i].strip() for i in cand]
    # 모든 후보에서 같은 자리의 같은 음절은 점수에 영향이 없으므로 빼고, 서로 다른 자리만 CNN으로 비교
    ok = all(len(w) == 2 for w in words)
    pos = [p for p in (0, 1) if ok and len({w[p] for w in words}) > 1]
    known = [ok and all(w[p] in _V for p in pos) for w in words]
    if any(known) and pos:
        with torch.no_grad():
            t = torch.from_numpy(x[None])
            lp = [0, 0]
            for n in _NETS:
                l1, l2 = n(t); lp[0] = lp[0] + F.log_softmax(l1, 1)[0]; lp[1] = lp[1] + F.log_softmax(l2, 1)[0]
        lp = [v / len(_NETS) for v in lp]
        s = [sum(float(lp[p][_V[w[p]]]) for p in pos) if k else -1e9 for w, k in zip(words, known)]
        b = int(np.argmax(s))
        # 모든 후보를 아는 음절로 비교 가능하면 그대로, 아니면 CNN이 확신(자리당 평균 확률>0.5)할 때만 채택
        if all(known) or s[b] / len(pos) > np.log(0.5):
            return choices[cand[b]]
    elif not pos:
        return choices[cand[0]]
    s = [_tscore(x, w) for w in words]   # 모르는 음절이 있을 때: 글꼴 템플릿 매칭
    return choices[cand[int(np.argmax(s))]]
