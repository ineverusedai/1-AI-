"""캡차 데이터 생성: README 공개 사양대로 captcha 0.7.1 ImageCaptcha(280x90) 로 직접 생성.
사용: python gen.py OUT_PREFIX N SEED [P_CONFUSABLE]
저장: OUT_PREFIX_x.npy (N,H,W uint8 회색조, 전처리 후), OUT_PREFIX_y.npy (N,5 int64)
"""
import sys, io, random, multiprocessing as mp
import numpy as np
from PIL import Image

CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
CONF = "0O1I"
MAIN = [c for c in CHARS if c not in CONF]  # 32
H, W = 48, 144

def preprocess(img):
    """PIL RGB 이미지 -> (H,W) uint8 회색조. solver.py 와 동일해야 함."""
    g = img.convert("L").resize((W, H), Image.BILINEAR)
    return np.asarray(g, dtype=np.uint8)

def sample_text(rng, p_conf):
    t = [rng.choice(MAIN) for _ in range(5)]
    if rng.random() < p_conf:
        t[rng.randrange(5)] = rng.choice(CONF)
    return "".join(t)

def work(args):
    seed, n, p_conf, via_png = args
    random.seed(seed)  # captcha 라이브러리는 전역 random 사용
    rng = random.Random(seed * 7919 + 1)
    from captcha.image import ImageCaptcha
    gen = ImageCaptcha(width=280, height=90)
    xs = np.empty((n, H, W), np.uint8); ys = np.empty((n, 5), np.int64)
    for i in range(n):
        text = sample_text(rng, p_conf)
        img = gen.generate_image(text)
        if via_png:
            buf = io.BytesIO(); img.save(buf, format="png")
            img = Image.open(io.BytesIO(buf.getvalue())).convert("RGB")
        xs[i] = preprocess(img)
        ys[i] = [CHARS.index(c) for c in text]
    return xs, ys

if __name__ == "__main__":
    out, N, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    p_conf = float(sys.argv[4]) if len(sys.argv) > 4 else 1/3
    via_png = len(sys.argv) > 5 and sys.argv[5] == "png"
    chunk = 5000
    jobs = [(seed * 100000 + k, min(chunk, N - k * chunk), p_conf, via_png) for k in range((N + chunk - 1) // chunk)]
    X = np.empty((N, H, W), np.uint8); Y = np.empty((N, 5), np.int64)
    pos = 0
    with mp.Pool(4) as pool:
        for xs, ys in pool.imap(work, jobs):
            X[pos:pos+len(xs)] = xs; Y[pos:pos+len(ys)] = ys; pos += len(xs)
            print(pos, flush=True)
    np.save(out + "_x.npy", X); np.save(out + "_y.npy", Y)
