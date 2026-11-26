"""미션 4 POV 영상용 실제 데이터 계산: 새 문제(시험 문제 아님) 하나를 공식 생성기로 만들고,
AI 전용 봇(ai_solutions/m4_B)의 특징 계산과 모델로 프레임을 쌓을 때마다 무엇을 보는지 기록한다."""
import json, random, sys, tempfile
from pathlib import Path
import numpy as np, torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "third_party" / "mvcap"))
sys.path.insert(0, str(ROOT / "ai_solutions" / "m4_B"))
from MVCAP_code.L1.generate_l1_dataset_rigid_drift import L1TextCaptchaGenerator, sample_text, sample_distractors
from feat import decode_mp4, motion_feature
from model import Net, prep, ALPHABET
import torch.nn.functional as Fn

SEED = 515151  # 시험 문제(secrets)와 다른 시드
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
np.random.seed(SEED); rng = random.Random(SEED)
text = sample_text(rng); opts = [text] + sample_distractors(rng, text); rng.shuffle(opts)
g = L1TextCaptchaGenerator()
with tempfile.TemporaryDirectory() as t:
    g.generate_single(text, out / "sample.mp4", Path(t) / "a.png")
frames = decode_mp4(str(out / "sample.mp4"))           # (90, 488, 488)
np.save(out / "frames.npy", frames.astype(np.uint8))
# 프레임을 k장까지 쌓았을 때의 잔차 지도 (가설: 배경 +2px / 글자 −2px)
F = frames
rb_cum = np.cumsum(np.abs(F[1:] - np.roll(F[:-1], 2, axis=2)), 0)
rf_cum = np.cumsum(np.abs(F[1:] - np.roll(F[:-1], -2, axis=2)), 0)
np.save(out / "rb_cum.npy", rb_cum.astype(np.float32)); np.save(out / "rf_cum.npy", rf_cum.astype(np.float32))
ck = torch.load(ROOT / "ai_solutions" / "m4_B" / "model.pt", map_location="cpu")
net = Net(w=ck["width"]); net.load_state_dict(ck["state"]); net.eval()
probs = []
with torch.no_grad():
    for k in range(2, 91):
        x = torch.from_numpy(prep(motion_feature(F[:k], out=244)[None]))
        probs.append(Fn.softmax(net(x)[0], -1).numpy())
probs = np.stack(probs)                                 # (89, 4, 32)
np.save(out / "probs.npy", probs)
lp = np.log(probs[-1] + 1e-12)
scores = [float(sum(lp[i, ALPHABET.index(c)] for i, c in enumerate(o))) for o in opts]
# 실제 학습 기록 (dev 글자 정답률)
def parse(f):
    return [float(l.split("dev_char ")[1].split()[0]) for l in open(f) if l.startswith("ep ")]
meta = {"text": text, "options": opts, "scores": scores, "alphabet": ALPHABET,
        "pilot_dev_char": parse(ROOT / "ai_solutions/m4_B/logs/pilot.log"),
        "final_dev_char": parse(ROOT / "ai_solutions/m4_B/logs/train_v2.log")}
(out / "meta.json").write_text(json.dumps(meta))
print(text, opts, [round(s, 2) for s in scores], "최종 자리별 최고 확률", probs[-1].max(1).round(3))
print("k=2,10,30 자리별 예측", ["".join(ALPHABET[i] for i in probs[j].argmax(1)) for j in (0, 8, 28)])
