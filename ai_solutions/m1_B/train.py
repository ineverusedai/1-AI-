import sys, time, math, argparse
import numpy as np, torch, torch.nn as nn, torch.nn.functional as F
from model import CRNN, greedy_decode, BLANK

p = argparse.ArgumentParser()
p.add_argument("--train", nargs="+", default=["data/train1"])
p.add_argument("--val", default="data/val")
p.add_argument("--epochs", type=int, default=10)
p.add_argument("--bs", type=int, default=128)
p.add_argument("--lr", type=float, default=2e-3)
p.add_argument("--out", default="model_a.pt")
p.add_argument("--init", default=None)
p.add_argument("--aug", type=int, default=1)
args = p.parse_args()
torch.set_num_threads(4); torch.manual_seed(0)

X = np.concatenate([np.load(t + "_x.npy") for t in args.train]); Y = np.concatenate([np.load(t + "_y.npy") for t in args.train])
Xv = torch.from_numpy(np.load(args.val + "_x.npy")); Yv = np.load(args.val + "_y.npy")
X = torch.from_numpy(X); Y = torch.from_numpy(Y)
N = len(X); print("train", N, "val", len(Xv), flush=True)

model = CRNN().to(memory_format=torch.channels_last)
if args.init: model.load_state_dict(torch.load(args.init))
print("params", sum(q.numel() for q in model.parameters()), flush=True)
opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
steps = args.epochs * (N // args.bs)
sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=steps, pct_start=0.15)
ctc = nn.CTCLoss(blank=BLANK, zero_infinity=True)

def to_in(xb):
    return (xb.float().unsqueeze(1) / 255.0 - 0.5) / 0.5

def augment(x):
    # 작은 평행이동 (±3px x, ±2px y) - 배경색(밝은값)으로 채움
    B = x.shape[0]
    dx = int(torch.randint(-3, 4, (1,))); dy = int(torch.randint(-2, 3, (1,)))
    x = torch.roll(x, shifts=(dy, dx), dims=(2, 3))
    return x

def evaluate():
    model.eval(); preds = []
    with torch.no_grad():
        for i in range(0, len(Xv), 500):
            preds += greedy_decode(model(to_in(Xv[i:i+500])))
    model.train()
    full = sum(p == list(y) for p, y in zip(preds, Yv)) / len(Yv)
    ch = sum(sum(a == b for a, b in zip(p, y)) for p, y in zip(preds, Yv)) / (5 * len(Yv))
    return full, ch

t0 = time.time(); step = 0
tl = torch.full((args.bs,), 5, dtype=torch.long)
for ep in range(args.epochs):
    perm = torch.randperm(N); run = 0.0
    for bi in range(N // args.bs):
        idx = perm[bi*args.bs:(bi+1)*args.bs]
        x = to_in(X[idx]); y = Y[idx]
        if args.aug: x = augment(x)
        with torch.autocast("cpu", dtype=torch.bfloat16):
            lp = model(x.contiguous(memory_format=torch.channels_last))
        il = torch.full((x.shape[0],), lp.shape[0], dtype=torch.long)
        loss = ctc(lp, y, il, tl)
        opt.zero_grad(); loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        opt.step(); sched.step(); step += 1
        run = 0.98 * run + 0.02 * loss.item() if bi else loss.item()
        if bi % 200 == 0:
            print(f"ep {ep} it {bi} loss {run:.4f} lr {sched.get_last_lr()[0]:.2e} t {time.time()-t0:.0f}s", flush=True)
    full, ch = evaluate()
    print(f"== ep {ep} val full {full:.4f} char {ch:.4f} t {time.time()-t0:.0f}s", flush=True)
    torch.save(model.state_dict(), args.out)
print("done", time.time() - t0, flush=True)
