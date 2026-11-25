"""Motion-defined text captcha solver.

solve(video_mp4, options) -> option string.
Method: decode frames -> estimate the two dominant per-frame dot shifts
(background / text) by block matching -> accumulate per-pixel residual
difference between the two motion hypotheses over all frame pairs -> text
mask -> render each option with bold sans fonts fitted to the mask's text
bounding box -> pick the option with the highest normalized correlation.
"""
import os
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]
_FONTS = None
_GLYPH_CACHE = {}


def _fonts():
    global _FONTS
    if _FONTS is None:
        _FONTS = [ImageFont.truetype(p, 120) for p in _FONT_PATHS if os.path.exists(p)]
    return _FONTS


MAX_FRAMES = 60


def _decode(video_mp4, max_frames=MAX_FRAMES):
    # temp file kept inside the solver folder (cv2.VideoCapture needs a path)
    fd, path = tempfile.mkstemp(suffix=".mp4", dir=os.path.dirname(os.path.abspath(__file__)))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(video_mp4)
        cap = cv2.VideoCapture(path)
        frames = []
        while len(frames) < max_frames:
            ok, fr = cap.read()
            if not ok:
                break
            frames.append(fr[..., 1])
        cap.release()
    finally:
        os.unlink(path)
    return np.asarray(frames, dtype=np.float32) / 255.0


def _shift(a, s):
    return np.roll(a, s, axis=(-2, -1))


def _estimate_shifts(F, R=4):
    """Two most frequent best-matching integer shifts between consecutive frames."""
    keys = [(dy, dx) for dy in range(-R, R + 1) for dx in range(-R, R + 1)]
    n = len(F)
    pairs = [n // 2]
    cnt = np.zeros(len(keys))
    for t in pairs:
        a, b = F[t, 40:-40], F[t + 1, 40:-40]
        E = np.stack([cv2.blur((b - _shift(a, k)) ** 2, (9, 9)) for k in keys])
        cnt += np.bincount(E.argmin(0).ravel(), minlength=len(keys))
    o = np.argsort(-cnt)
    return keys[o[0]], keys[o[1]], cnt[o[0]], cnt[o[1]]


def motion_map(F):
    s_bg, s_fg, c_bg, c_fg = _estimate_shifts(F)
    a, b = F[:-1], F[1:]
    e_bg = ((b - _shift(a, s_bg)) ** 2).sum(0)
    e_fg = ((b - _shift(a, s_fg)) ** 2).sum(0)
    D = cv2.GaussianBlur(e_bg - e_fg, (0, 0), 2.5)
    D = (D - np.median(D)) / (D.std() + 1e-6)
    return D


def _text_bbox(D):
    m = (D > 1.0).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    # group glyph pixels into one blob, keep the largest blob (drops stray streaks)
    g = cv2.dilate(m, np.ones((15, 31), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(g)
    if n > 1:
        k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        ky0 = stats[k, cv2.CC_STAT_TOP]
        ky1 = ky0 + stats[k, cv2.CC_STAT_HEIGHT]
        keep = np.zeros(n, bool)
        keep[k] = True
        bx0 = stats[k, cv2.CC_STAT_LEFT]
        bx1 = bx0 + stats[k, cv2.CC_STAT_WIDTH]
        kh = ky1 - ky0
        # grow along the text line: add blobs vertically aligned with the main
        # blob and horizontally close to the current extent
        changed = True
        while changed:
            changed = False
            for j in range(1, n):
                if keep[j]:
                    continue
                y0 = stats[j, cv2.CC_STAT_TOP]
                hj = stats[j, cv2.CC_STAT_HEIGHT]
                x0 = stats[j, cv2.CC_STAT_LEFT]
                x1 = x0 + stats[j, cv2.CC_STAT_WIDTH]
                ov = min(ky1, y0 + hj) - max(ky0, y0)
                gap = max(x0 - bx1, bx0 - x1, 0)
                if (ov > 0.6 * hj and hj > 0.5 * kh and gap < 0.6 * kh
                        and stats[j, cv2.CC_STAT_AREA] > 0.05 * stats[k, cv2.CC_STAT_AREA]):
                    keep[j] = True
                    bx0, bx1 = min(bx0, x0), max(bx1, x1)
                    changed = True
        m = m * keep[lab]
    # trim thin horizontal streaks glued to the text: keep columns whose
    # mask count is a reasonable fraction of the strongest one
    cols = m.sum(0)
    if cols.max() > 0:
        m = m * (cols > 0.08 * cols.max())[None, :]
    ys, xs = np.nonzero(m)
    if len(ys) == 0:
        H, W = D.shape
        return H // 3, 2 * H // 3, W // 10, 9 * W // 10
    return ys.min(), ys.max() + 1, xs.min(), xs.max() + 1


def _render(text, font):
    key = (text, font.path)
    if key in _GLYPH_CACHE:
        return _GLYPH_CACHE[key]
    img = Image.new("L", (900, 220), 0)
    ImageDraw.Draw(img).text((20, 20), text, font=font, fill=255)
    a = np.asarray(img, dtype=np.float32) / 255.0
    ys = np.where(a.max(1) > 0)[0]
    xs = np.where(a.max(0) > 0)[0]
    a = a[ys.min(): ys.max() + 1, xs.min(): xs.max() + 1]
    _GLYPH_CACHE[key] = a
    return a


def _ncc(a, b):
    a = a - a.mean()
    b = b - b.mean()
    return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))


def score_options(D, options):
    y0, y1, x0, x1 = _text_bbox(D)
    H, W = D.shape
    pad = 12
    Y0, Y1, X0, X1 = max(0, y0 - pad), min(H, y1 + pad), max(0, x0 - pad), min(W, x1 + pad)
    patch = D[Y0:Y1, X0:X1]
    scores = []
    for opt in options:
        best = -1.0
        for font in _fonts():
            g = _render(opt, font)
            for dh in (-6, -3, 0, 3, 6):
                for dw in (-12, -6, 0, 6, 12):
                    h, w = (y1 - y0) + dh, (x1 - x0) + dw
                    if h < 5 or w < 5:
                        continue
                    t = np.zeros_like(patch)
                    r = cv2.resize(g, (w, h), interpolation=cv2.INTER_AREA)
                    oy = (y0 - Y0) - dh // 2
                    ox = (x0 - X0) - dw // 2
                    ty0, tx0 = max(oy, 0), max(ox, 0)
                    ty1, tx1 = min(oy + h, t.shape[0]), min(ox + w, t.shape[1])
                    if ty1 <= ty0 or tx1 <= tx0:
                        continue
                    t[ty0:ty1, tx0:tx1] = r[ty0 - oy: ty1 - oy, tx0 - ox: tx1 - ox]
                    t = cv2.GaussianBlur(t, (0, 0), 2.5)
                    best = max(best, _ncc(patch, t))
        scores.append(best)
    return scores


def solve(video_mp4: bytes, options: list) -> str:
    F = _decode(video_mp4)
    D = motion_map(F)
    scores = score_options(D, options)
    return options[int(np.argmax(scores))]
