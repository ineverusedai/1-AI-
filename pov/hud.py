"""AI 시점(POV) 연출 영상 공통 부품: 1920×1200 60fps, 어두운 HUD. 자막 없음 (숫자·짧은 기술 표시만)."""
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H, FPS = 1920, 1200, 60
CY = (76, 201, 240); AMB = (255, 183, 3); DIM = (40, 70, 90); MID = (110, 140, 155)
BG = (5, 8, 12); WHT = (225, 240, 248); RED = (255, 77, 94); GRN = (60, 220, 140)


def font(sz, w=500, mono=True):
    f = ImageFont.truetype(str(ROOT / "common/web/fonts" / ("JetBrainsMono-latin.woff2" if mono else "PretendardVariable.woff2")), sz)
    try:
        f.set_variation_by_axes([w])
    except Exception:
        pass
    return f


F12, F16, F20, F28, F44, F64, F96 = font(13), font(16), font(20, 600), font(28, 700), font(44, 700), font(64, 700), font(110, 800)


def make_base():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    for x in range(0, W, 40):
        d.line([(x, 0), (x, H)], fill=(10, 18, 24))
    for y in range(0, H, 40):
        d.line([(0, y), (W, y)], fill=(10, 18, 24))
    yy, xx = np.mgrid[0:H, 0:W]
    vig = 1 - 0.55 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 2
    return Image.fromarray((np.asarray(im, np.float32) * vig[..., None]).clip(0, 255).astype(np.uint8))


def ease(t):
    t = min(1, max(0, t))
    return t * t * (3 - 2 * t)


def fade(c, a):
    return tuple(int(v * max(0, min(1, a))) for v in c)


def bracket(dr, x0, y0, x1, y1, c=CY, L=22, w=2):
    for (x, y, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        dr.line([(x, y), (x + sx * L, y)], fill=c, width=w)
        dr.line([(x, y), (x, y + sy * L)], fill=c, width=w)


def chrome(base, f, title, sub):
    """공통 틀: 제목 표시, 경과 시계, 테두리, 부팅 스캔 선."""
    im = base.copy()
    dr = ImageDraw.Draw(im)
    sec = f / FPS
    a0 = ease(f / 60)
    dr.text((60, 40), title, font=F16, fill=fade(CY, a0))
    dr.text((60, 64), sub, font=F12, fill=fade(DIM, a0))
    dr.text((W - 330, 40), f"T+{int(sec // 60):02d}:{sec % 60:05.2f}", font=F20, fill=fade(CY, a0))
    dr.line([(60, 96), (60 + int((W - 120) * a0), 96)], fill=DIM, width=1)
    bracket(dr, 40, 24, W - 40, H - 24, c=fade(DIM, a0), L=40)
    if f < 60:
        y = int(H * (f / 60))
        dr.line([(0, y), (W, y)], fill=CY, width=2)
    return im, dr


def panel(im, dr, img, x, y, w, h, c=CY, label=None, alpha=1.0, resample=Image.NEAREST):
    p = img.resize((w, h), resample)
    if alpha < 1:
        p = Image.blend(Image.new("RGB", p.size, BG), p.convert("RGB"), max(0, alpha))
    im.paste(p, (x, y))
    bracket(dr, x - 8, y - 8, x + w + 8, y + h + 8, c=fade(c, alpha), L=16)
    if label:
        dr.text((x, y - 32), label, font=F12, fill=fade(c, alpha))


def bars(dr, x, y, items, width=260, rowh=30, alpha=1.0, hi=None, fmt="{:.2f}", label_font=None):
    """items: [(이름, 값 0~1, 표시값)]"""
    lf = label_font or F16
    for i, (name, v, shown) in enumerate(items):
        yy = y + i * rowh
        c = AMB if i == hi else (CY if hi is None else MID)
        dr.text((x, yy), str(name), font=lf, fill=fade(c, alpha))
        dr.rectangle([x + 110, yy + 5, x + 110 + max(2, int(width * max(0, min(1, v)))), yy + 17], fill=fade(c, alpha))
        dr.text((x + 120 + width, yy), fmt.format(shown) if not isinstance(shown, str) else shown, font=F16, fill=fade(c, alpha))


def line_chart(dr, gx, gy, gw, gh, series, xmax, ymin=0.0, ymax=1.0, alpha=1.0, ticks=(0.25, 0.5, 0.75, 1.0), tickfmt="{:.2f}"):
    """series: [(값 목록, 색, 진행 0~1, 끝 표시)]"""
    dr.rectangle([gx, gy, gx + gw, gy + gh], outline=fade(DIM, alpha))
    for v in ticks:
        yv = gy + gh - int(gh * (v - ymin) / (ymax - ymin))
        dr.line([(gx, yv), (gx + gw, yv)], fill=fade((16, 30, 40), alpha))
        dr.text((gx - 58, yv - 8), tickfmt.format(v), font=F12, fill=fade(DIM, alpha))
    ends = []
    for vals, c, prog, tag in series:
        n = max(1, int(round(len(vals) * prog)))
        pts = [(gx + int(gw * i / max(1, xmax - 1)), gy + gh - int(gh * (min(ymax, max(ymin, v)) - ymin) / (ymax - ymin))) for i, v in enumerate(vals[:n])]
        for a, b in zip(pts, pts[1:]):
            dr.line([a, b], fill=fade(c, alpha), width=3)
        for p in pts:
            dr.ellipse([p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3], fill=fade(c, alpha))
        if tag and pts:
            dr.text((pts[-1][0] + 10, pts[-1][1] - 22), tag, font=F12, fill=fade(c, alpha))
        ends.append(pts[-1] if pts else None)
    return ends


class Writer:
    def __init__(self, out, audio=None):
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
        if audio:
            cmd += ["-i", str(audio), "-c:a", "aac", "-b:a", "192k", "-shortest"]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
        self.p = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def write(self, im):
        self.p.stdin.write(im.tobytes())

    def close(self):
        self.p.stdin.close()
        self.p.wait()


def fade_out(im, f, start, end):
    if f >= start:
        return Image.blend(im, Image.new("RGB", (W, H), BG), min(1, (f - start) / max(1, end - start)))
    return im
