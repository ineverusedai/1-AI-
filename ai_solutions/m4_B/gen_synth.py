"""Fast labeled data: official generator's mask/texture functions + same frame composition
in memory (no mp4 encode). usage: python gen_synth.py OUT_PREFIX SEED N [CHUNK]"""
import sys, os, time, random, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mvcap"))
import cv2; cv2.setNumThreads(1)
from MVCAP_code.L1.generate_l1_dataset_rigid_drift import L1TextCaptchaGenerator, sample_text, sample_distractors
from synth import synth_frames
from feat import motion_feature
prefix, seed, N = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
chunk = int(sys.argv[4]) if len(sys.argv) > 4 else 500
np.random.seed(seed); rng = random.Random(seed); g = L1TextCaptchaGenerator()
X, Y = [], []; t0 = time.time(); ci = 0
for i in range(N):
    text = sample_text(rng); sample_distractors(rng, text)
    X.append(motion_feature(synth_frames(g, text), out=244).astype(np.float16)); Y.append(text)
    if len(X) == chunk or i == N - 1:
        np.savez(f"{prefix}_{ci:03d}.npz", X=np.stack(X), Y=np.array(Y)); ci += 1; X, Y = [], []
        print(f"{i+1}/{N} {time.time()-t0:.0f}s", flush=True)
print("done", time.time() - t0, flush=True)
