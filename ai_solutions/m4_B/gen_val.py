"""Held-out validation set: real mp4 files + metadata exactly as official main() (different seed)."""
import sys, os, random, json, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mvcap"))
from pathlib import Path
from MVCAP_code.L1.generate_l1_dataset_rigid_drift import L1TextCaptchaGenerator, sample_text, sample_distractors
seed, N = int(sys.argv[1]), int(sys.argv[2])
out = Path("val_data"); out.mkdir(exist_ok=True)
np.random.seed(seed); rng = random.Random(seed); g = L1TextCaptchaGenerator()
meta = []; t0 = time.time()
for i in range(N):
    name = f"L1_{i:03d}"
    text = sample_text(rng); d = sample_distractors(rng, text)
    g.generate_single(text, out / f"{name}.mp4", out / f"{name}.png")
    meta.append({"id": name, "text": text, "video_path": f"val_data/{name}.mp4",
                 "target_option": {"id": name, "text": text},
                 "distractors": [{"id": f"{name}_d{k}", "text": t} for k, t in enumerate(d)]})
    if (i + 1) % 25 == 0: print(i + 1, f"{time.time()-t0:.0f}s", flush=True)
(out / "dataset_metadata.json").write_text(json.dumps(meta, indent=1))
print("done", time.time() - t0, flush=True)
