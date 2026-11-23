import sys, time, numpy as np, torch, torch.nn as nn
from PIL import Image
from model import CRNN, CHARS
from spec import Spec, char_centers, crop, to_in
import os; torch.set_num_threads(int(os.environ.get("NT", "4"))); torch.manual_seed(0)
main_ckpt = sys.argv[1]; epochs = int(sys.argv[2]); out = sys.argv[3]
train_sets = sys.argv[4].split(",") if len(sys.argv) > 4 else ["data/spec_train"]
lr = float(sys.argv[5]) if len(sys.argv) > 5 else 2e-3
M = CRNN(); M.load_state_dict(torch.load(main_ckpt)); M.eval()
O, Z = CHARS.index("O"), CHARS.index("0")

def build(pre):
    X = np.load(pre + "_x.npy", mmap_mode="r"); Y = np.load(pre + "_y.npy"); K = np.load(pre + "_k.npy")
    crops, labs, mainpred = [], [], []
    with torch.no_grad():
        for i in range(0, len(X), 500):
            small = np.stack([np.asarray(Image.fromarray(a).resize((144, 48), Image.BILINEAR)) for a in X[i:i+500]])
            lp = M(((torch.from_numpy(small).float() / 255 - .5) / .5).unsqueeze(1))
            for j in range(lp.shape[1]):
                cc = char_centers(lp[:, j])
                if len(cc) != 5: continue
                k = K[i + j]
                crops.append(crop(X[i + j], cc[k][1])); labs.append(int(Y[i + j, k] == Z)); mainpred.append(cc[k][0])
    return np.stack(crops), np.array(labs), np.array(mainpred)

t0 = time.time()
parts = [build(p) for p in train_sets]; Xt = np.concatenate([p[0] for p in parts]); Yt = np.concatenate([p[1] for p in parts]); del parts; Xv, Yv, Pv = build("data/spec_val")
print("crops", Xt.shape, Xv.shape, "align time", time.time() - t0, flush=True)
print("main model O/0 acc on spec_val:", np.mean((Pv == Z) == (Yv == 1)), flush=True)
np.save("data/spec_val_crops.npy", Xv[:16])
model = Spec().to(memory_format=torch.channels_last)
opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
bs = 128; steps = epochs * (len(Xt) // bs)
sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps, pct_start=0.1)
Xt_t = torch.from_numpy(Xt); Yt_t = torch.from_numpy(Yt)
lossf = nn.CrossEntropyLoss()
for ep in range(epochs):
    perm = torch.randperm(len(Xt)); model.train()
    for b in range(len(Xt) // bs):
        idx = perm[b*bs:(b+1)*bs]
        x = to_in(Xt_t[idx]); dx = int(torch.randint(-4, 5, (1,)))
        x = torch.roll(x, dx, dims=3)
        with torch.autocast("cpu", dtype=torch.bfloat16):
            o = model(x.contiguous(memory_format=torch.channels_last))
        loss = lossf(o.float(), Yt_t[idx])
        opt.zero_grad(); loss.backward(); opt.step(); sched.step()
        if b % 200 == 0: print(f"ep {ep} it {b} loss {loss.item():.4f} t {time.time()-t0:.0f}", flush=True)
    model.eval()
    with torch.no_grad():
        pv = torch.cat([model(to_in(torch.from_numpy(Xv[i:i+500]))).argmax(1) for i in range(0, len(Xv), 500)]).numpy()
    print(f"== ep {ep} spec val acc {np.mean(pv == Yv):.4f} t {time.time()-t0:.0f}", flush=True)
    torch.save(model.state_dict(), out)
