"""미션 3 POV 영상 (소리 착시 캡차 전용 봇). 실제 데이터: 시험과 다른 시드로 새로 만든 문제(원본 + 사인파 4개),
AI 전용 봇의 실제 특징·학습된 인코더·DTW 경로, 학습 전(무작위 초기화) 인코더와 비교, 실제 학습 기록. 소리 포함.
실행: python pov/m3.py <작업 폴더> <출력 mp4>"""
import json, random, sys
from pathlib import Path
import numpy as np, torch
import scipy.io.wavfile as wavfile
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hud import *  # noqa

D = Path(sys.argv[1]); D.mkdir(parents=True, exist_ok=True); OUT = Path(sys.argv[2])
M3 = ROOT / "ai_solutions" / "m3_B"
sys.path.insert(0, str(M3)); sys.path.insert(0, str(ROOT))
import solver as S
from feats import read_wav, logmel
from dtw import dtw_path
from model import Metric, prep
from missions.m3_sinewave import generate as g

cfg, _ = g.load_cfg_and_seed()
cfg = dict(cfg, pool_size=30, fixed_q5_sentence=None)
originals = [g.load_original(i) for i in range(len(g.SENTENCES))]
pick = None
for q, target, opts, sd in g.iter_problems(31337, cfg):
    if g._group(target) != "basic":
        continue
    d = D / f"q{q}"
    if d.exists():
        import shutil; shutil.rmtree(d)
    ans = g.write_question(d, target, opts, sd, originals, cfg)
    ref = (d / "ref.wav").read_bytes(); ob = [(d / f"opt{n}.wav").read_bytes() for n in range(1, 5)]
    if S.solve(ref, ob) == ans:
        pick = (d, ans); break
d, ans = pick
ref = (d / "ref.wav").read_bytes(); ob = [(d / f"opt{n}.wav").read_bytes() for n in range(1, 5)]
R = logmel(read_wav(ref)); O = [logmel(read_wav(b)) for b in ob]
def costs(net):
    out = []
    with torch.no_grad():
        er = net.er(torch.from_numpy(prep(R)))
        for o in O:
            C = (1 - er @ net.eo(torch.from_numpy(prep(o))).t()).numpy().astype(np.float64)
            c, ii, jj = dtw_path(C)
            out.append((C, c, ii, jj))
    return out
TR = costs(S._NET)
torch.manual_seed(0); UN = costs(Metric().eval())
print("정답", ans, "학습 후", [round(x[1], 4) for x in TR], "학습 전", [round(x[1], 4) for x in UN])

# 소리 트랙: 원본 전체 → 소리 1~4 앞 1.3초씩
SR = 22050
def wav(b):
    sr, x = wavfile.read(d / b); return x.astype(np.float32) / 32768
CLIPS = [("ref.wav", 1.2, None)] + [(f"opt{n}.wav", None, 1.3) for n in range(1, 5)]
track = np.zeros(int(SR * 27)); sched = []; t = 1.2
for name, st, dur in CLIPS:
    x = wav(name); x = x[np.argmax(np.abs(x) > 0.02):]          # 앞 무음 건너뜀
    if dur: x = x[: int(SR * dur)]
    a = int(SR * t); track[a:a + len(x)] += x; sched.append((name, t, t + len(x) / SR)); t += len(x) / SR + 0.25
wavfile.write(D / "track.wav", SR, (np.clip(track, -1, 1) * 32767).astype(np.int16))
print("소리 일정", [(n, round(a, 2), round(b, 2)) for n, a, b in sched])

def spec_img(X, c=CY):
    X = (X - X.min()) / (X.max() - X.min() + 1e-6)
    return Image.fromarray((X.T[::-1, :, None] ** 1.4 * np.array(c)).clip(0, 255).astype(np.uint8))
def cost_img(C, ii=None, jj=None, upto=1.0):
    A = 1 - (C - C.min()) / (C.max() - C.min() + 1e-6)
    rgb = (A[..., None] ** 2.2 * np.array([30, 120, 160])).clip(0, 255).astype(np.uint8)
    if ii is not None:
        n = int(len(ii) * upto)
        for a, b in zip(ii[:n], jj[:n]):
            rgb[a, b] = AMB
    return Image.fromarray(rgb[::-1])  # 아래쪽이 시작
REF_IMG = spec_img(R, WHT); OPT_IMG = [spec_img(o) for o in O]
listen_end = sched[-1][2]
L0 = int(listen_end * FPS) + 20
T = dict(lis=(60, L0), dtw=(L0, L0 + 420), learn=(L0 + 420, L0 + 720), res=(L0 + 720, L0 + 960))
T["end"] = (T["res"][1], T["res"][1] + 60)
base = make_base()
wr = Writer(OUT, audio=D / "track.wav")
for f in range(T["end"][1]):
    im, dr = chrome(base, f, "M3 // SINE-WAVE SPEECH", "CLEAN REF -> 4 SINE-WAVE CLIPS  22.05KHZ  4-CHOICE")
    sec = f / FPS
    a = ease((f - 60) / 30)
    dr.text((W - 470, 120), "ZERO-SHOT  N/A  (NO EARS)", font=F12, fill=fade(MID, a))
    # 1) 듣기: 원본 → 소리 1~4 (소리와 맞춤)
    if f < T["dtw"][0] + 20:
        al = ease((f - 60) / 20) * (1 - max(0, (f - T["dtw"][0]) / 20))
        nm, s0, s1 = sched[0]
        panel(im, dr, REF_IMG, 120, 200, 760, 300, c=WHT, label="REF  LOG-MEL 64", alpha=al, resample=Image.BILINEAR)
        if s0 <= sec <= s1 + 0.3:
            # 재생 위치 (앞 무음은 건너뛰었으므로 비율로)
            px = 120 + int(760 * min(1, (sec - s0) / (s1 - s0)))
            dr.line([(px, 200), (px, 500)], fill=AMB, width=2)
        for i in range(4):
            y = 560 + i * 140; nm, a0, a1 = sched[i + 1]
            on = a0 <= sec <= a1
            panel(im, dr, OPT_IMG[i], 120, y, 760, 110, c=AMB if on else CY, label=f"SINE {i + 1}", alpha=al * (1 if sec >= a0 - 0.2 else 0.35), resample=Image.BILINEAR)
            if on:
                px = 120 + int(760 * (sec - a0) / 1.3 * (1.3 / max(1.3, (a1 - a0))))
                dr.line([(px, y), (px, y + 110)], fill=AMB, width=2)
        # 오른쪽: 실시간 음량
        dr.text((1000, 200), "INPUT LEVEL", font=F12, fill=fade(CY, al))
        k = int(sec * SR)
        if 0 <= k < len(track) - 512:
            lv = float(np.sqrt(np.mean(track[k:k + 512] ** 2)))
            dr.rectangle([1000, 230, 1000 + int(700 * min(1, lv * 6)), 250], fill=fade(AMB, al))
    # 2) DTW 정렬
    if T["dtw"][0] <= f < T["learn"][0] + 20:
        t = (f - T["dtw"][0]) / (T["dtw"][1] - T["dtw"][0]); al = ease((f - T["dtw"][0]) / 20) * (1 - max(0, (f - T["learn"][0]) / 20))
        for i in range(4):
            ti = ease((t - i * 0.18) * 3.5)
            C, c, ii, jj = TR[i]
            x0, y0 = 120 + (i % 2) * 460, 200 + (i // 2) * 460
            panel(im, dr, cost_img(C, ii, jj, ti), x0, y0, 400, 400, c=AMB if (i + 1 == ans and t > 0.85) else CY,
                  label=f"REF x SINE {i + 1}   DTW", alpha=al * (0.3 + 0.7 * min(1, ti * 2)), resample=Image.NEAREST)
        dr.text((1100, 200), "DTW COST  (LOWER = SAME)", font=F12, fill=fade(CY, al))
        mx = max(x[1] for x in TR)
        for i in range(4):
            ti = ease((t - i * 0.18) * 3.5); y = 250 + i * 70
            c = TR[i][1]; hi = (i + 1 == ans and t > 0.85)
            dr.text((1100, y), f"SINE {i + 1}", font=F20, fill=fade(AMB if hi else MID, al))
            dr.rectangle([1260, y + 6, 1260 + int(420 * c / mx * ti), y + 22], fill=fade(AMB if hi else CY, al))
            if ti > 0.95: dr.text((1700, y), f"{c:.3f}", font=F20, fill=fade(AMB if hi else WHT, al))
    # 3) 학습: 학습 전 vs 후
    if T["learn"][0] <= f < T["res"][0] + 20:
        t = (f - T["learn"][0]) / (T["learn"][1] - T["learn"][0]); al = ease((f - T["learn"][0]) / 20) * (1 - max(0, (f - T["res"][0]) / 20))
        Cu, cu, iu, ju = UN[ans - 1]; Ct, ct, it, jt = TR[ans - 1]
        panel(im, dr, cost_img(Cu, iu, ju), 120, 240, 520, 520, c=MID, label="ENCODER  INIT (RANDOM)", alpha=al)
        panel(im, dr, cost_img(Ct, it, jt), 720, 240, 520, 520, c=AMB, label="ENCODER  TRAINED", alpha=al * ease(t * 2.5))
        # 네 보기의 DTW 비용: 학습 전에는 정답을 못 고르고, 학습 후에는 정답이 가장 낮음 (실제 값)
        for col, (res, lab, x0) in enumerate(((UN, "INIT", 120), (TR, "TRAINED", 720))):
            aa = al * (1 if col == 0 else ease(t * 2.5)); best = int(np.argmin([r[1] for r in res]))
            lo, hi = min(r[1] for r in res), max(r[1] for r in res)
            for i, r in enumerate(res):
                y = 800 + i * 44; hl = i == best
                c = (GRN if i + 1 == ans else RED) if hl else MID
                dr.text((x0, y), f"SINE {i + 1}", font=F16, fill=fade(c, aa))
                dr.rectangle([x0 + 110, y + 4, x0 + 110 + int(40 + 300 * (r[1] - lo) / (hi - lo + 1e-9)), y + 16], fill=fade(c, aa))
                dr.text((x0 + 470, y), f"{r[1]:.4f}" + ("  <" if hl else ""), font=F16, fill=fade(c, aa))
        dr.text((1340, 260), "INNER-VAL", font=F16, fill=fade(CY, al))
        v = 153 if t < 0.4 else 320
        dr.text((1340, 290), f"{v}/320", font=F64, fill=fade(WHT if v == 320 else RED, al))
        dr.text((1340, 390), "EPOCH 0" if t >= 0.4 else "INIT", font=F20, fill=fade(MID, al))
        dr.text((1340, 460), "LABELED  2,000", font=F20, fill=fade(MID, al))
        dr.text((1340, 500), "TRAIN 1,600 / HELD-OUT 400", font=F16, fill=fade(MID, al))
        s = int(390 * ease(t))
        dr.text((1340, 560), f"TRAIN {s // 60:02d}:{s % 60:02d}", font=F28, fill=fade(AMB, al))
    # 4) 결과
    if f >= T["res"][0]:
        t = (f - T["res"][0]) / (T["res"][1] - T["res"][0]); al = ease((f - T["res"][0]) / 20)
        dr.text((160, 300), "HELD-OUT", font=F16, fill=fade(CY, al))
        dr.text((160, 330), "400/400", font=F96, fill=fade(WHT, al))
        dr.text((900, 300), "TEST", font=F16, fill=fade(CY, ease((t - 0.25) * 4)))
        dr.text((900, 330), "24/24", font=F96, fill=fade(GRN, ease((t - 0.25) * 4)))
        dr.text((160, 560), "SOLVE  ~90 MS / QUESTION", font=F28, fill=fade(AMB, ease((t - 0.45) * 4)))
    im = fade_out(im, f, T["end"][0], T["end"][1])
    wr.write(im)
wr.close()
print("완료", OUT)
