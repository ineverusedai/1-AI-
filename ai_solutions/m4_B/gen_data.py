"""Generate labeled training data with the OFFICIAL MVCAP L1 generator (real mp4 path),
then store only motion features (mp4 deleted to save disk).
usage: python gen_data.py OUT_PREFIX SEED N [CHUNK]"""
import sys, time, random, os, json
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mvcap"))
from pathlib import Path
from MVCAP_code.L1.generate_l1_dataset_rigid_drift import L1TextCaptchaGenerator, sample_text, sample_distractors
from feat import decode_mp4, motion_feature

prefix, seed, N = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
chunk = int(sys.argv[4]) if len(sys.argv) > 4 else 250
np.random.seed(seed)
rng = random.Random(seed)
g = L1TextCaptchaGenerator()
tmpdir = Path(prefix + "_tmp"); tmpdir.mkdir(parents=True, exist_ok=True)
X, Y = [], []
t0 = time.time(); ci = 0
for i in range(N):
    text = sample_text(rng); sample_distractors(rng, text)  # same RNG consumption as official main()
    vp, pp = tmpdir / "v.mp4", tmpdir / "v.png"
    g.generate_single(text, vp, pp)
    F = decode_mp4(str(vp))
    X.append(motion_feature(F, out=244).astype(np.float16)); Y.append(text)
    if len(X) == chunk or i == N - 1:
        np.savez(f"{prefix}_{ci:03d}.npz", X=np.stack(X), Y=np.array(Y))
        ci += 1; X, Y = [], []
        print(f"{i+1}/{N} {time.time()-t0:.0f}s", flush=True)
for p in (vp, pp):
    if p.exists(): p.unlink()
print("done", time.time() - t0, flush=True)
