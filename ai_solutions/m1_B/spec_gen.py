"""O/0 전문 분류기용 데이터: 정확히 한 위치 k 에 O 또는 0 (50:50), 나머지는 32글자.
전체 해상도 회색조(90x280) 이미지를 저장. 사용: python spec_gen.py OUT N SEED"""
import sys, random, multiprocessing as mp, numpy as np
from gen import MAIN, CHARS

def work(args):
    seed, n = args
    random.seed(seed); rng = random.Random(seed * 13 + 7)
    from captcha.image import ImageCaptcha
    g = ImageCaptcha(width=280, height=90)
    xs = np.empty((n, 90, 280), np.uint8); ys = np.empty((n, 5), np.int64); ks = np.empty(n, np.int64)
    for i in range(n):
        t = [rng.choice(MAIN) for _ in range(5)]; k = rng.randrange(5); t[k] = rng.choice("O0")
        xs[i] = np.asarray(g.generate_image("".join(t)).convert("L"))
        ys[i] = [CHARS.index(c) for c in t]; ks[i] = k
    return xs, ys, ks

if __name__ == "__main__":
    out, N, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    jobs = [(seed * 100000 + j, 2000) for j in range(N // 2000)]
    with mp.Pool(int(sys.argv[4]) if len(sys.argv) > 4 else 2) as p:
        res = p.map(work, jobs)
    np.save(out + "_x.npy", np.concatenate([r[0] for r in res]))
    np.save(out + "_y.npy", np.concatenate([r[1] for r in res]))
    np.save(out + "_k.npy", np.concatenate([r[2] for r in res]))
    print("done", N)
