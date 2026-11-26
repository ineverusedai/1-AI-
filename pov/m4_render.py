"""미션 4 POV(AI 시점 HUD) 시험 영상 그리기. 자막 없음, 숫자·기호만. 1920×1200 60fps.

데이터는 pov/m4_data.py 가 만든 실제 계산 결과(새 문제, 실제 전용 봇 모델 출력, 실제 학습 기록)만 쓴다.
실행: python pov/m4_render.py <데이터 폴더> <출력 mp4>
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
D = Path(sys.argv[1]); OUTMP4 = Path(sys.argv[2])
W, H, FPS = 1920, 1200, 60
CY = (76, 201, 240); AMB = (255, 183, 3); DIM = (40, 70, 90); BG = (5, 8, 12); WHT = (225, 240, 248); RED = (255, 77, 94)

def font(sz, w=500, mono=True):
    f = ImageFont.truetype(str(ROOT / "common/web/fonts" / ("JetBrainsMono-latin.woff2" if mono else "PretendardVariable.woff2")), sz)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
F12, F16, F20, F28, F44, F96 = font(13), font(16), font(20, 600), font(28, 700), font(44, 700), font(110, 800)

frames = np.load(D / "frames.npy")            # (90,488,488) uint8
rb = np.load(D / "rb_cum.npy"); rf = np.load(D / "rf_cum.npy")   # (89,488,488) 누적
probs = np.load(D / "probs.npy")              # (89,4,32): 프레임 k+2 장까지 쌓았을 때
meta = json.loads((D / "meta.json").read_text())
AL = meta["alphabet"]; TEXT = meta["text"]; OPTS = meta["options"]; SC = meta["scores"]

# ---------- 바탕 (격자 + 비네트) ----------
base = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(base)
for x in range(0, W, 40): d.line([(x, 0), (x, H)], fill=(10, 18, 24))
for y in range(0, H, 40): d.line([(0, y), (W, y)], fill=(10, 18, 24))
vig = np.zeros((H, W), np.float32)
yy, xx = np.mgrid[0:H, 0:W]; vig = 1 - 0.55 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 2
base = Image.fromarray((np.asarray(base, np.float32) * vig[..., None]).clip(0, 255).astype(np.uint8))

def ease(t): t = min(1, max(0, t)); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t

def bracket(dr, x0, y0, x1, y1, c=CY, L=22, w=2):
    for (x, y, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        dr.line([(x, y), (x + sx * L, y)], fill=c, width=w); dr.line([(x, y), (x, y + sy * L)], fill=c, width=w)

def smap(k):  # 프레임 쌍 k개 누적 → s 지도 (−1..1)
    a, b = rb[k - 1], rf[k - 1]
    return (a - b) / (a + b + 1e-3 * k)

def colorize_s(s, alpha=1.0):  # + 쪽(글자) 하늘색, − 쪽 어둡게
    p = np.clip(s, 0, 1)[..., None]; n = np.clip(-s, 0, 1)[..., None]
    rgb = p * np.array(CY) * 1.15 + (1 - p) * (1 - n * 0.85) * np.array([14, 26, 34])
    return Image.fromarray((rgb * alpha).clip(0, 255).astype(np.uint8))

def gray(a, tint=WHT):
    a = a.astype(np.float32)[..., None] / 255.0
    return Image.fromarray((a * np.array(tint)).clip(0, 255).astype(np.uint8))

def heat(a, c):
    a = a / (a.max() + 1e-6)
    return Image.fromarray((a[..., None] ** 0.8 * np.array(c)).clip(0, 255).astype(np.uint8))

PX, PY, PS = 130, 250, 760      # 큰 화면 위치·크기
T = {"boot": (0, 60), "raw": (60, 300), "acc": (300, 780), "read": (780, 1080), "opt": (1080, 1320), "train": (1320, 1620), "end": (1620, 1680)}
N = 1680

def kfor(t):  # 누적 장면: 프레임 쌍 1→89, 처음엔 천천히
    return int(round(1 + 88 * (ease(t) ** 1.6)))

out_dir = D / "render"; out_dir.mkdir(exist_ok=True)
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                       "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUTMP4)], stdin=subprocess.PIPE)

for f in range(N):
    sec = f / FPS
    im = base.copy(); dr = ImageDraw.Draw(im)
    a0 = ease(f / 60)
    # 상단 HUD
    dr.text((60, 40), "M4 // MOTION-DEFINED TEXT", font=F16, fill=tuple(int(c * a0) for c in CY))
    dr.text((60, 64), "MVCAP-L1  488x488  30FPS  90F", font=F12, fill=tuple(int(c * a0) for c in DIM))
    dr.text((W - 330, 40), f"T+{int(sec // 60):02d}:{sec % 60:05.2f}", font=F20, fill=tuple(int(c * a0) for c in CY))
    dr.line([(60, 96), (60 + int((W - 120) * a0), 96)], fill=DIM, width=1)
    bracket(dr, 40, 24, W - 40, H - 24, c=tuple(int(c * a0) for c in DIM), L=40)
    if f < T["boot"][1]:  # 부팅: 훑는 선
        y = int(H * (f / 60)); dr.line([(0, y), (W, y)], fill=CY, width=2)

    vf = (f // 2) % 90  # 영상 프레임 (30fps)
    # ---------- 큰 화면 ----------
    if f >= T["raw"][0]:
        if f < T["acc"][0] + 60:
            raw = gray(frames[vf]).resize((PS, PS), Image.NEAREST)
            im.paste(raw, (PX, PY))
        if f >= T["acc"][0]:
            t = (f - T["acc"][0]) / (T["acc"][1] - T["acc"][0]); k = kfor(t) if f < T["acc"][1] else 89
            sm = colorize_s(smap(k)).resize((PS, PS), Image.BILINEAR)
            if f < T["acc"][0] + 60:
                sm = Image.blend(im.crop((PX, PY, PX + PS, PY + PS)), sm, (f - T["acc"][0]) / 60)
            im.paste(sm, (PX, PY))
        bracket(dr, PX - 10, PY - 10, PX + PS + 10, PY + PS + 10)
        lab = "INPUT" if f < T["acc"][0] else "S = (Rb - Rf) / (Rb + Rf)"
        dr.text((PX, PY - 40), lab, font=F16, fill=CY)
        if f < T["acc"][0]:
            dr.text((PX + PS - 120, PY - 40), f"F {vf + 1:02d}/90", font=F16, fill=AMB)
            # 정지 화면 판독: 아무것도 없음
            dr.text((PX, PY + PS + 24), "STATIC FRAME  ->  TEXT: NONE", font=F16, fill=DIM)
            # 훑는 십자선
            cx = PX + int(PS * (0.5 + 0.45 * np.sin(sec * 2.1))); cy = PY + int(PS * (0.5 + 0.4 * np.sin(sec * 1.3 + 1)))
            dr.line([(cx, PY), (cx, PY + PS)], fill=(30, 90, 110)); dr.line([(PX, cy), (PX + PS, cy)], fill=(30, 90, 110))
            dr.rectangle([cx - 14, cy - 14, cx + 14, cy + 14], outline=AMB)
    # ---------- 오른쪽: 필름 띠 (원본) ----------
    if T["raw"][0] <= f < T["acc"][0] + 120:
        al = min(1, (f - T["raw"][0]) / 30) * (1 - max(0, (f - T["acc"][0]) / 120))
        for i in range(6):
            fi = (vf + i * 3) % 90
            th = gray(frames[fi]).resize((112, 112), Image.BILINEAR)
            x, y = 1000, 250 + i * 130 - int((sec * 40) % 130)
            if 230 < y < 1000:
                im.paste(Image.blend(Image.new("RGB", th.size, BG), th, al * 0.8), (x, y))
                dr.text((x + 122, y + 4), f"F{fi + 1:02d}", font=F12, fill=DIM)
    # ---------- 누적: 두 가설 ----------
    if T["acc"][0] <= f < T["read"][1]:
        t = (f - T["acc"][0]) / (T["acc"][1] - T["acc"][0]); k = kfor(t) if f < T["acc"][1] else 89
        al = min(1, (f - T["acc"][0] - 60) / 40) if f < T["acc"][0] + 100 else 1
        if al > 0:
            for j, (arr, c, lab) in enumerate(((rb[k - 1], AMB, "H1  BG +2PX  ->  Rb"), (rf[k - 1], CY, "H2  FG -2PX  ->  Rf"))):
                x, y = 1000, 250 + j * 380
                p = heat(arr, c).resize((330, 330), Image.BILINEAR)
                im.paste(Image.blend(Image.new("RGB", p.size, BG), p, al), (x, y))
                bracket(dr, x - 6, y - 6, x + 336, y + 336, c=c, L=14)
                dr.text((x, y - 30), lab, font=F12, fill=c)
            # 누적 카운터
            dr.text((1380, 250), "PAIRS", font=F12, fill=DIM)
            dr.text((1380, 270), f"{k:02d}", font=F96, fill=WHT)
            dr.text((1380, 400), "/ 89", font=F28, fill=DIM)
            # 대비 막대 (글자 줄 평균 - 나머지)
            s = smap(k); con = float(s[165:352].mean() - np.concatenate([s[:150], s[370:]]).mean())
            dr.text((1380, 470), "CONTRAST", font=F12, fill=DIM)
            dr.rectangle([1380, 492, 1380 + 420, 506], outline=DIM)
            dr.rectangle([1380, 492, 1380 + int(420 * min(1, max(0, con) / 0.35)), 506], fill=CY)
            dr.text((1380, 512), f"{con:+.3f}", font=F16, fill=CY)
    # ---------- 읽기: 네 자리 확률 ----------
    if T["read"][0] <= f < T["opt"][1]:
        t = (f - T["read"][0]) / 200; j = int(round(88 * ease(t)))  # 프레임 쌍 2→90장 기준 모델 출력
        pr = probs[j]
        al = min(1, (f - T["read"][0]) / 30)
        y0 = 640
        dr.text((1380, y0 - 40), f"CNN  4x{len(AL)}   INPUT PAIRS {j + 1:02d}", font=F12, fill=tuple(int(c * al) for c in CY))
        for pos in range(4):
            x = 1380 + pos * 118
            top = np.argsort(-pr[pos])[:5]
            ch = AL[top[0]]; ok = ch == TEXT[pos]
            dr.text((x + 18, y0), ch, font=F44, fill=tuple(int(c * al) for c in (WHT if ok else RED)))
            for r, idx in enumerate(top):
                yy2 = y0 + 70 + r * 30
                dr.text((x, yy2), AL[idx], font=F16, fill=tuple(int(c * al) for c in DIM if False) or (120, 150, 165))
                dr.rectangle([x + 20, yy2 + 4, x + 20 + int(80 * pr[pos][idx]), yy2 + 16], fill=CY if r == 0 else (30, 70, 90))
        if f >= T["read"][0] + 200:
            dr.rectangle([1370, y0 - 6, 1370 + 4 * 118, y0 + 60], outline=AMB, width=2)
    # ---------- 선택지 점수 ----------
    if T["opt"][0] <= f < T["train"][0] + 30:
        al = min(1, (f - T["opt"][0]) / 30) * (1 - max(0, (f - T["train"][0]) / 30))
        best = int(np.argmax(SC)); y0 = 900
        dr.text((1380, y0 - 30), "OPTIONS  SUM LOG P", font=F12, fill=tuple(int(c * al) for c in CY))
        for i, (o, s) in enumerate(zip(OPTS, SC)):
            y = y0 + i * 40; prog = ease((f - T["opt"][0] - i * 12) / 40)
            c = AMB if i == best else (90, 120, 135)
            dr.text((1380, y), "ABCDEF"[i], font=F16, fill=tuple(int(v * al) for v in DIM))
            dr.text((1410, y), o, font=F20, fill=tuple(int(v * al) for v in c))
            L = int(260 * prog * (1 - min(1, -s / 32)) + (0 if i != best else 0))
            dr.rectangle([1490, y + 6, 1490 + max(2, L), y + 18], fill=tuple(int(v * al) for v in c))
            dr.text((1770, y), f"{s:7.2f}", font=F16, fill=tuple(int(v * al) for v in c))
    # ---------- 학습 기록 그래프 ----------
    if f >= T["train"][0]:
        t = (f - T["train"][0]) / (T["train"][1] - T["train"][0]); al = min(1, (f - T["train"][0]) / 30)
        gx, gy, gw, gh = 1000, 640, 840, 440
        im.paste(Image.new("RGB", (gw + 40, gh + 120), BG), (gx - 20, gy - 70))
        dr.text((gx, gy - 50), "TRAINING  DEV CHAR ACC", font=F12, fill=CY)
        dr.rectangle([gx, gy, gx + gw, gy + gh], outline=DIM)
        for v in (0.25, 0.5, 0.75, 1.0):
            yv = gy + gh - int(gh * v); dr.line([(gx, yv), (gx + gw, yv)], fill=(16, 30, 40)); dr.text((gx - 46, yv - 8), f"{v:.2f}", font=F12, fill=DIM)
        def curve(vals, epochs_max, c, frac, dash=False):
            n = max(1, int(len(vals) * frac)); pts = [(gx + int(gw * i / (epochs_max - 1)), gy + gh - int(gh * v)) for i, v in enumerate(vals[:n])]
            for a, b in zip(pts, pts[1:]):
                if not dash or (pts.index(a) % 2 == 0): dr.line([a, b], fill=c, width=3)
            return pts[-1]
        pe = curve(meta["pilot_dev_char"], 40, (90, 90, 100), ease(t * 1.4))
        fe = curve(meta["final_dev_char"], 40, CY, ease(max(0, t * 1.4 - 0.25)))
        dr.text((pe[0] - 160, pe[1] - 30), "PILOT  N=500", font=F12, fill=(150, 150, 160))
        if t > 0.2:
            dr.text((fe[0] + 10, fe[1] + 8), "N=5750", font=F12, fill=CY)
        dr.text((gx, gy + gh + 14), "EPOCH", font=F12, fill=DIM)
        tt = int(1694 * ease(t))
        dr.text((gx + gw - 260, gy + gh + 14), f"TRAIN {tt // 60:02d}:{tt % 60:02d} / 28:14", font=F12, fill=AMB)
        if t > 0.75:
            dr.text((gx + 20, gy + 20), "VAL 300/300", font=F28, fill=WHT)
    # 끝: 어둡게
    if f >= T["end"][0]:
        a = (f - T["end"][0]) / (T["end"][1] - T["end"][0])
        im = Image.blend(im, Image.new("RGB", (W, H), BG), a)
    ff.stdin.write(im.tobytes())
    if f % 300 == 0: print(f"  {f}/{N}", flush=True)
ff.stdin.close(); ff.wait()
print("완료", OUTMP4)
