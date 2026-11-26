"""미션 2 POV 영상 (착시 캡차 전용 봇). 실제 데이터: 시험과 다른 시드로 새로 만든 문제, AI 전용 봇의 실제 전처리·모델 출력,
실제 정답 달린 자료 통계(3,000장), 실제 학습 기록. 실행: python pov/m2.py <작업 폴더> <출력 mp4>"""
import json, random, re, sys
from pathlib import Path
import cv2, numpy as np, torch, torch.nn.functional as Fn
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hud import *  # noqa

D = Path(sys.argv[1]); D.mkdir(parents=True, exist_ok=True); OUT = Path(sys.argv[2])
M2 = ROOT / "ai_solutions" / "m2_B"
sys.path.insert(0, str(M2)); sys.path.insert(0, str(ROOT))
import solver as S
from prep import _hp
from missions.m2_illusion import generate as g

KF = {sz: font(sz, 700, mono=False) for sz in (20, 28, 44, 64)}
cfg, test_seed = g.load_cfg_and_seed()
pick = None
for q, word, scene, choices, sd in g.iter_problems(4040, dict(cfg, pool_size=40)):
    if scene != "leaves":
        continue
    img, _ = g.make_image(word, scene, random.Random(sd), cfg)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, cfg["jpeg_quality"]])
    if S.solve(buf.tobytes(), choices) == word:
        pick = (word, scene, choices, img, buf.tobytes()); break
word, scene, choices, img, jb = pick
bgr = cv2.imdecode(np.frombuffer(jb, np.uint8), cv2.IMREAD_COLOR)
gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
s320 = cv2.resize(gray, (320, 200), interpolation=cv2.INTER_AREA)
a160 = cv2.resize(s320.astype(np.float32), (160, 100), interpolation=cv2.INTER_AREA)
blur1 = cv2.GaussianBlur(a160, (0, 0), 1.0)
hp_a = _hp(a160)
m160 = cv2.resize(cv2.medianBlur(s320, 9).astype(np.float32), (160, 100), interpolation=cv2.INTER_AREA)
hp_m = _hp(m160)
x = np.stack([hp_a, hp_m]).astype(np.float32)
with torch.no_grad():
    lp1 = lp2 = 0
    for n in S._NETS:
        l1, l2 = n(torch.from_numpy(x[None])); lp1 = lp1 + Fn.softmax(l1, 1)[0]; lp2 = lp2 + Fn.softmax(l2, 1)[0]
p1, p2 = (lp1 / len(S._NETS)).numpy(), (lp2 / len(S._NETS)).numpy()
SYL = S._SYL
words = [c for c in choices if " " not in c]
score = {w: float(np.log(p1[S._V[w[0]]] + 1e-9) + np.log(p2[S._V[w[1]]] + 1e-9)) for w in words}
# 정답 달린 자료 통계 (AI가 받은 3,000장)
lab = json.loads((Path("/tmp/claude-0/-home-user-1-ai-/1b622cd5-ff31-5d6c-a949-2a489d6c2348/scratchpad/ai_sandbox_m2/labeled/labels.json")).read_text())
n_scene = sum(1 for r in lab if " " in r["answer"])
n_same = sum(1 for r in lab if len({c[0] for c in r["choices"] if " " not in c}) == 1)
thumbs = []
for r in lab[:60]:
    im0 = cv2.imread(str(Path("/tmp/claude-0/-home-user-1-ai-/1b622cd5-ff31-5d6c-a949-2a489d6c2348/scratchpad/ai_sandbox_m2/labeled") / r["file"]))
    thumbs.append(Image.fromarray(cv2.cvtColor(cv2.resize(im0, (192, 120)), cv2.COLOR_BGR2RGB)))
def parse(f):
    return [int(re.search(r"val (\d+)", l).group(1)) / 300 for l in open(f) if l.startswith("ep")]
V1, V3 = parse(M2 / "work/train1.log"), parse(M2 / "work/train3.log")
print(word, scene, choices, {k: round(v, 2) for k, v in score.items()}, "scene", n_scene, "same", n_same, len(V1), len(V3))

def toimg(a, c=WHT):
    a = (a - a.min()) / (a.max() - a.min() + 1e-6)
    return Image.fromarray((a[..., None] * np.array(c)).clip(0, 255).astype(np.uint8))
def emph(a):  # 어두운 글자를 하늘색으로
    v = np.clip(-a / 2.5, 0, 1)[..., None]
    return Image.fromarray((v * np.array(CY) * 1.1 + (1 - v) * np.array([14, 26, 34])).clip(0, 255).astype(np.uint8))

base = make_base()
RAW = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
stages = [("GRAY", toimg(gray.astype(np.float32))), ("DOWN 160x100", toimg(a160)), ("BLUR s1", toimg(blur1)),
          ("- BLUR s20", toimg(hp_a)), ("MEDIAN 9", toimg(hp_m))]
T = dict(inp=(60, 330), sq=(330, 720), lab=(720, 960), cnn=(960, 1260), curve=(1260, 1500), end=(1500, 1560))
wr = Writer(OUT)
for f in range(T["end"][1]):
    im, dr = chrome(base, f, "M2 // HYBRID-IMAGE ILLUSION", "LOW-FREQ TEXT + HIGH-FREQ SCENE  960x600  4-CHOICE")
    a = ease((f - 60) / 30)
    dr.text((W - 470, 120), "ZERO-SHOT  ORIG 9/20  BLUR 18/20", font=F12, fill=fade(RED, a))
    sec = f / FPS
    # 1) 입력
    if T["inp"][0] <= f < T["sq"][0] + 30:
        al = ease((f - T["inp"][0]) / 20)
        panel(im, dr, RAW, 120, 200, 896, 560, label="INPUT 960x600", alpha=al, resample=Image.BILINEAR)
        cx = 120 + int(896 * (0.5 + 0.42 * np.sin(sec * 2.0))); cy = 200 + int(560 * (0.5 + 0.38 * np.sin(sec * 1.4 + 1)))
        dr.line([(cx, 200), (cx, 760)], fill=(30, 90, 110)); dr.line([(120, cy), (1016, cy)], fill=(30, 90, 110))
        dr.rectangle([cx - 16, cy - 16, cx + 16, cy + 16], outline=AMB)
        dr.text((120, 790), "TEXT: ?", font=F16, fill=fade(DIM, al))
    if T["inp"][0] <= f < T["cnn"][1]:
        al = ease((f - T["inp"][0] - 20) / 20)
        dr.text((1180, 200), "OPTIONS", font=F12, fill=fade(CY, al))
        for i, c in enumerate(choices):
            y = 240 + i * 64
            struck = " " in c and f >= T["lab"][0] + 120
            col = MID if struck else WHT
            if f >= T["cnn"][0] + 200 and c == word: col = AMB
            dr.text((1180, y), "ABCD"[i], font=F16, fill=fade(DIM, al))
            dr.text((1220, y - 6), c, font=KF[28], fill=fade(col, al))
            if struck:
                tw = dr.textlength(c, font=KF[28]); dr.line([(1220, y + 12), (1220 + tw, y + 12)], fill=RED, width=3)
            if c in score and f >= T["cnn"][0] + 160:
                dr.text((1600, y), f"{score[c]:7.2f}", font=F16, fill=fade(AMB if c == word else MID, al))
    # 2) 눈 가늘게 뜨기 (실제 전처리)
    if T["sq"][0] <= f < T["lab"][0] + 20:
        t = (f - T["sq"][0]) / (T["sq"][1] - T["sq"][0]); al = 1 - max(0, (f - T["lab"][0]) / 20)
        dr.rectangle([100, 180, 1040, 1100], fill=BG)
        k = min(len(stages) - 1, int(t * len(stages) * 1.15))
        for i in range(k + 1):
            ai = ease((t - i / (len(stages) * 1.15)) * 8) * al
            panel(im, dr, stages[i][1], 120 + i * 180, 220, 160, 100, label=stages[i][0], alpha=ai)
            if i < k:
                dr.text((120 + i * 180 + 164, 254), ">", font=F20, fill=fade(DIM, al))
        big = emph(hp_m) if k >= 4 else emph(hp_a) if k >= 3 else stages[k][1]
        panel(im, dr, big, 120, 400, 896, 560, c=AMB if k >= 3 else CY, label="FEATURE  2CH 160x100", alpha=al, resample=Image.BILINEAR)
    # 3) 정답 달린 자료 3,000장 통계
    if T["lab"][0] <= f < T["cnn"][0] + 20:
        t = (f - T["lab"][0]) / (T["lab"][1] - T["lab"][0]); al = ease((f - T["lab"][0]) / 20) * (1 - max(0, (f - T["cnn"][0]) / 20))
        dr.rectangle([100, 180, 1040, 1100], fill=BG)
        n = int(60 * ease(t * 2))
        for i in range(n):
            r, c = divmod(i, 5)
            if r < 12: im.paste(thumbs[i].resize((168, 70)), (120 + c * 180, 200 + r * 76))
        cnt = int(3000 * ease(t * 1.5))
        dr.rectangle([300, 640, 1000, 980], fill=BG)
        dr.text((320, 660), "LABELED", font=F16, fill=fade(CY, al))
        dr.text((320, 690), f"{cnt:,}", font=F96, fill=fade(WHT, al))
        dr.text((320, 830), f"ANSWER = SCENE TEXT   {n_scene}/{len(lab):,}", font=F20, fill=fade(RED, ease((t - 0.4) * 4) * al))
        dr.text((320, 870), f"SAME 1ST SYLLABLE     {n_same:,}/{len(lab):,}", font=F20, fill=fade(AMB, ease((t - 0.55) * 4) * al))
    # 4) CNN: 두 음절 확률
    if T["cnn"][0] <= f < T["curve"][0] + 20:
        t = (f - T["cnn"][0]) / (T["cnn"][1] - T["cnn"][0]); al = ease((f - T["cnn"][0]) / 20) * (1 - max(0, (f - T["curve"][0]) / 20))
        dr.rectangle([100, 180, 1040, 1100], fill=BG)
        panel(im, dr, emph(hp_m), 120, 220, 448, 280, c=AMB, label="FEATURE", alpha=al, resample=Image.BILINEAR)
        for j, p in enumerate((p1, p2)):
            x0 = 640 + j * 200; top = np.argsort(-p)[:5]
            dr.text((x0, 200), f"SYL {j + 1}", font=F12, fill=fade(CY, al))
            for r, idx in enumerate(top):
                y = 240 + r * 52; v = float(p[idx]) * ease(t * 2)
                dr.text((x0, y - 6), SYL[idx], font=KF[28], fill=fade(WHT if r == 0 else MID, al))
                dr.rectangle([x0 + 50, y + 6, x0 + 50 + int(110 * v), y + 18], fill=fade(CY if r == 0 else (30, 70, 90), al))
        dr.text((120, 560), "CNN x2  ENSEMBLE   2 HEADS x 110 SYLLABLES", font=F12, fill=fade(MID, al))
    # 5) 학습 곡선
    if f >= T["curve"][0]:
        t = (f - T["curve"][0]) / (T["curve"][1] - T["curve"][0]); al = ease((f - T["curve"][0]) / 20)
        dr.rectangle([100, 180, 1880, 1100], fill=BG)
        dr.text((160, 210), "VAL ACC  N=300", font=F12, fill=fade(CY, al))
        line_chart(dr, 200, 260, 1100, 560, [(V1, (110, 110, 120), ease(t * 1.3), "V1 120x75"), (V3, CY, ease(t * 1.3 - 0.15), "V3 160x100 +MEDIAN")],
                   max(len(V1), len(V3)), alpha=al)
        dr.text((1360, 300), "HELD-OUT", font=F16, fill=fade(CY, ease((t - 0.6) * 4)))
        dr.text((1360, 330), "600/600", font=F64, fill=fade(WHT, ease((t - 0.6) * 4)))
        dr.text((1360, 440), "TEST 200/200", font=F28, fill=fade(GRN, ease((t - 0.7) * 4)))
        s = int((1 * 3600 + 31 * 60) * ease(t))
        dr.text((1360, 520), f"TRAIN {s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}", font=F28, fill=fade(AMB, al))
        dr.text((1360, 570), "LABELED 3,000  (2,100 / 300 / 600)", font=F16, fill=fade(MID, al))
    im = fade_out(im, f, T["end"][0], T["end"][1])
    wr.write(im)
wr.close()
print("완료", OUT)
