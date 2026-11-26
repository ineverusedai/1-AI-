"""미션 1 POV 영상 (글자 캡차 전용 봇). 실제 데이터: 새로 만든 캡차(시험 문제 아님), 실제 학습 체크포인트(에폭 0·1·4·최종),
실제 0/O 전문 분류기, 실제 학습 기록. 실행: python pov/m1.py <작업 폴더> <출력 mp4>"""
import io, json, random, sys, time
from pathlib import Path
import numpy as np, torch
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hud import *  # noqa

D = Path(sys.argv[1]); D.mkdir(parents=True, exist_ok=True); OUT = Path(sys.argv[2])
M1 = ROOT / "ai_solutions" / "m1_B"
OLD = Path("/tmp/claude-0/-home-user/1b622cd5-ff31-5d6c-a949-2a489d6c2348/scratchpad/ai_sandbox_m1")
sys.path.insert(0, str(M1)); sys.path.insert(0, str(ROOT))
import captcha.image as ci
from captcha.image import ImageCaptcha
from missions.m1_captcha.generate import SeededSecrets, make_text
import solver as S
from model import CRNN, CHARS, BLANK, greedy_decode
from spec import char_centers, crop, to_in

# ---------- 데이터 (새 캡차, 시험 문제 아님) ----------
cfg = json.loads((ROOT / "config.json").read_text())["m1"]
gen = ImageCaptcha(width=cfg["width"], height=cfg["height"])
trng = random.Random("pov-m1-text")
caps = []
orig = ci.secrets
for i in range(260):
    t = make_text(trng, 5, cfg["confusable_rate"], cfg["max_confusables"])
    ci.secrets = SeededSecrets(random.Random(f"pov-m1-img-{i}"))
    caps.append((t, gen.generate(t).getvalue()))
ci.secrets = orig
hero_t, hero_b = next((t, b) for t, b in caps if ("O" in t or "0" in t) and S.solve(b) == t)
x, full = S._prep(hero_b)
ck = {}
for name, f in (("EP0", OLD / "model_a_ep0.pt"), ("EP1", OLD / "model_a_ep1.pt"), ("EP4", OLD / "model_a_ep4.pt"), ("FINAL", M1 / "model_final.pt")):
    m = CRNN(); m.load_state_dict(torch.load(f, map_location="cpu")); m.eval()
    with torch.no_grad():
        lp = m(x)
    ck[name] = "".join(CHARS[k] for k in greedy_decode(lp)[0])
    if name == "FINAL":
        LP = lp[:, 0].numpy()
cc = char_centers(torch.from_numpy(LP))
oz = next(i for i, (k, _) in enumerate(cc) if CHARS[k] in "O0")
crops = np.stack([crop(full, cc[oz][1] + dd) for dd in S._TTA])
with torch.no_grad():
    sp = torch.softmax(S._SPEC(to_in(torch.from_numpy(crops))).mean(0), -1).numpy()  # [P(O), P(0)]
# 처리량: 새 캡차 200개를 실제 풀이기로
tp = []
t0 = time.perf_counter()
for t, b in caps[:200]:
    tp.append((t, b, S.solve(b)))
tp_ms = (time.perf_counter() - t0) * 1000
ok200 = sum(a == p for a, _, p in tp)
VAL = [0.9237, 0.9768, 0.9839, 0.9826, 0.9916, 0.9925]  # train_a.log 에폭별 5글자 전체 정답률
print("hero", hero_t, ck, "spec P(O),P(0)", sp.round(3), "200개", ok200, round(tp_ms), "ms")

# ---------- 그리기 ----------
base = make_base()
thumbs = [Image.open(io.BytesIO(b)).convert("RGB") for _, b in caps]
hero = Image.open(io.BytesIO(hero_b)).convert("RGB")
T = dict(fac=(60, 330), read=(330, 750), oz=(750, 1020), curve=(1020, 1260), tp=(1260, 1500), end=(1500, 1560))
N = T["end"][1]
wr = Writer(OUT)
for f in range(N):
    im, dr = chrome(base, f, "M1 // DISTORTED TEXT", "LEPTURE/CAPTCHA  280x90  [A-Z0-9]x5")
    # 직접 보기 기록 (사실 수치)
    a = ease((f - 60) / 30)
    dr.text((W - 420, 120), "ZERO-SHOT  11/20   MAX STREAK 3", font=F12, fill=fade(RED, a))
    # 1) 연습 캡차 공장
    if T["fac"][0] <= f < T["read"][0] + 30:
        t = (f - T["fac"][0]) / (T["fac"][1] - T["fac"][0]); al = 1 - max(0, (f - T["fac"][1]) / 30)
        off = int(t * 900)
        for r in range(14):
            for c in range(8):
                y = 140 + r * 70 - off % 70; i = (r * 8 + c + (off // 70) * 8) % len(thumbs)
                if 120 < y < 1100:
                    th = thumbs[i].resize((180, 58))
                    im.paste(Image.blend(Image.new("RGB", th.size, BG), th, 0.55 * al), (90 + c * 200, y))
        n = int(300000 * ease(t) ** 1.3)
        dr.rectangle([1260, 450, 1840, 720], fill=BG)
        dr.text((1280, 470), "TRAIN SET", font=F16, fill=fade(CY, al))
        dr.text((1280, 500), f"{n:,}", font=F96, fill=fade(WHT, al))
        dr.text((1280, 640), "SEED != TEST", font=F12, fill=fade(DIM, al))
    # 2) 읽기: CTC + 체크포인트
    if T["read"][0] <= f < T["oz"][1]:
        t = (f - T["read"][0]) / (T["read"][1] - T["read"][0]); al = ease((f - T["read"][0]) / 30)
        panel(im, dr, hero, 120, 200, 840, 270, label="INPUT 280x90", alpha=al, resample=Image.BILINEAR)
        # CTC 히트맵 (36프레임 × 37글자)
        cols = int(36 * ease(min(1, t * 1.6)))
        P = np.exp(LP)  # (36,37)
        hm = np.zeros((37, 36, 3)); hm[:, :cols] = (P.T[:, :cols, None] ** 0.6) * np.array(CY)
        hmi = Image.fromarray(hm.clip(0, 255).astype(np.uint8)).resize((840, 340), Image.NEAREST)
        panel(im, dr, hmi, 120, 540, 840, 340, label="CTC  T=36 x 37", alpha=al)
        if cols < 36:
            xx = 120 + int(840 * cols / 36); dr.line([(xx, 540), (xx, 880)], fill=AMB, width=2)
        for k, tc in cc:
            if tc < cols:
                xx = 120 + int(840 * (tc + 0.5) / 36)
                dr.text((xx - 14, 900), CHARS[k], font=F44, fill=fade(WHT, al))
        # 체크포인트별 판독
        dr.text((1100, 200), "CHECKPOINT   READ      VAL", font=F12, fill=fade(CY, al))
        for j, (name, v) in enumerate((("EP0", VAL[0]), ("EP1", VAL[1]), ("EP4", VAL[4]), ("FINAL", VAL[5]))):
            aj = ease((f - T["read"][0] - 60 - j * 50) / 20)
            if aj <= 0: continue
            y = 240 + j * 70; pred = ck[name]
            dr.text((1100, y + 6), name, font=F20, fill=fade(MID, aj))
            for i in range(5):
                ch = pred[i] if i < len(pred) else "_"; good = i < len(pred) and ch == hero_t[i]
                dr.text((1240 + i * 40, y), ch, font=F28, fill=fade(GRN if good else RED, aj))
            dr.text((1480, y + 6), f"{v * 100:.2f}%", font=F20, fill=fade(WHT, aj))
    # 3) O / 0 판정
    if T["oz"][0] <= f < T["curve"][0] + 20:
        al = ease((f - T["oz"][0]) / 30) * (1 - max(0, (f - T["curve"][0]) / 20))
        cimg = Image.fromarray(crops[1]).convert("RGB")
        panel(im, dr, cimg, 1100, 560, 260, 360, c=AMB, label="FULL-RES CROP", alpha=al, resample=Image.BILINEAR)
        prog = ease((f - T["oz"][0] - 40) / 60)
        bars(dr, 1420, 600, [("LETTER O", sp[0] * prog, sp[0] * prog), ("DIGIT 0", sp[1] * prog, sp[1] * prog)], width=220, rowh=50, alpha=al, hi=int(np.argmax(sp)), label_font=F12)
        dr.text((1420, 740), "ERR 75  ->  O/0 67", font=F20, fill=fade(RED, al))
        dr.text((1420, 780), "SPEC NET  240,000", font=F16, fill=fade(MID, al))
        dr.text((1420, 840), "99.25%  ->  99.72%", font=F28, fill=fade(GRN, ease((f - T["oz"][0] - 140) / 30) * al))
    # 4) 학습 곡선
    if T["curve"][0] <= f < T["tp"][0] + 20:
        t = (f - T["curve"][0]) / (T["curve"][1] - T["curve"][0]); al = ease((f - T["curve"][0]) / 20) * (1 - max(0, (f - T["tp"][0]) / 20))
        dr.rectangle([1040, 180, 1880, 1120], fill=BG)
        dr.text((1100, 200), "VAL 5-CHAR ACC   N=10,000", font=F12, fill=fade(CY, al))
        line_chart(dr, 1120, 240, 700, 420, [(VAL + [0.9972], CY, ease(t * 1.3), "+SPEC 99.72")], 7, ymin=0.9, ymax=1.0,
                   ticks=(0.92, 0.94, 0.96, 0.98, 1.0), alpha=al)
        s = int((3 * 3600 + 16 * 60) * ease(t))
        dr.text((1120, 700), f"TRAIN  {s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}", font=F28, fill=fade(AMB, al))
        dr.text((1120, 750), "SAMPLES 300,000   EPOCHS 6   CPU x4", font=F16, fill=fade(MID, al))
    # 5) 처리량
    if f >= T["tp"][0]:
        t = (f - T["tp"][0]) / (T["tp"][1] - T["tp"][0]); al = ease((f - T["tp"][0]) / 20)
        dr.rectangle([60, 110, W - 60, H - 40], fill=BG)
        n = int(200 * ease(min(1, t * 1.25)))
        for i in range(n):
            tt, b, p = tp[i]; r, c = divmod(i, 20)
            x0, y0 = 90 + c * 88, 170 + r * 62
            im.paste(thumbs[i].resize((82, 27)), (x0, y0))
            dr.text((x0, y0 + 30), p, font=F12, fill=GRN if p == tt else RED)
        okn = sum(1 for i in range(n) if tp[i][0] == tp[i][2])
        dr.text((90, 830), f"SOLVED {n:3d}/200", font=F44, fill=fade(WHT, al))
        dr.text((90, 900), f"CORRECT {okn:3d}", font=F44, fill=fade(GRN, al))
        dr.text((800, 860), f"{tp_ms * n / 200 / 1000:4.2f} s", font=F96, fill=fade(AMB, al))
    im = fade_out(im, f, T["end"][0], T["end"][1])
    wr.write(im)
wr.close()
print("완료", OUT)
