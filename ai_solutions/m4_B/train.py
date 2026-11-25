import sys, glob, time, argparse, numpy as np, torch, torch.nn.functional as Fn
torch.set_num_threads(int(__import__("os").environ.get("NT", "2")))
from model import Net, prep, C2I
ap = argparse.ArgumentParser()
ap.add_argument("--epochs", type=int, default=30); ap.add_argument("--out", default="model.pt")
ap.add_argument("--dev", default="data/trA_000.npz"); ap.add_argument("--bs", type=int, default=64)
ap.add_argument("--lr", type=float, default=2e-3); ap.add_argument("--synth", type=int, default=1); ap.add_argument("--width", type=int, default=32)
a = ap.parse_args()
files = sorted(glob.glob("data/tr*_*.npz")) + (sorted(glob.glob("data/sy*_*.npz")) if a.synth else [])
tr = [f for f in files if f != a.dev]
def load(fs):
    X, Y = [], []
    for f in fs:
        d = np.load(f); X.append(prep(d["X"])); Y += list(d["Y"])
    return np.concatenate(X), np.array([[C2I[c] for c in y] for y in Y])
Xtr, Ytr = load(tr); Xdv, Ydv = load([a.dev])
print("train", Xtr.shape, "dev", Xdv.shape, flush=True)
Xtr, Ytr, Xdv, Ydv = map(torch.from_numpy, (Xtr, Ytr, Xdv, Ydv))
torch.manual_seed(0)
net = Net(w=a.width)
opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=1e-4)
steps = a.epochs * (len(Xtr) // a.bs)
sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=a.lr, total_steps=steps, pct_start=0.15)
def augment(x):
    n = x.shape[0]
    # random translation (+-3 px x, +-2 px y) via roll, contrast jitter, noise
    out = torch.empty_like(x)
    dx = torch.randint(-3, 4, (n,)); dy = torch.randint(-2, 3, (n,))
    for i in range(n):
        out[i] = torch.roll(x[i], (int(dy[i]), int(dx[i])), (1, 2))
    out = out * (0.8 + 0.4 * torch.rand(n, 1, 1, 1)) + 0.05 * torch.randn_like(out)
    return out
def evaluate(X, Y):
    net.eval(); c = cs = 0
    with torch.no_grad():
        for i in range(0, len(X), 128):
            p = net(X[i:i+128]).argmax(-1); y = Y[i:i+128]
            c += (p == y).all(1).sum().item(); cs += (p == y).sum().item()
    net.train(); return c / len(X), cs / (4 * len(X))
from model import ALPHABET
_r = __import__("random").Random(7)
def six_way(X, Y):
    net.eval(); ok = 0
    with torch.no_grad():
        lp = torch.cat([Fn.log_softmax(net(X[i:i+128]), -1) for i in range(0, len(X), 128)])
    for k in range(len(X)):
        opts = [Y[k]] + [torch.tensor([_r.randrange(32) for _ in range(4)]) for _ in range(5)]
        sc = [lp[k, torch.arange(4), o].sum().item() for o in opts]
        ok += int(max(range(6), key=lambda j: sc[j]) == 0)
    net.train(); return ok / len(X)
t0 = time.time()
for ep in range(a.epochs):
    perm = torch.randperm(len(Xtr)); tl = 0
    for i in range(0, len(Xtr) - a.bs + 1, a.bs):
        idx = perm[i:i+a.bs]
        out = net(augment(Xtr[idx]))
        loss = Fn.cross_entropy(out.reshape(-1, out.shape[-1]), Ytr[idx].reshape(-1), label_smoothing=0.05)
        opt.zero_grad(); loss.backward(); opt.step(); sch.step(); tl += loss.item()
    seq, ch = evaluate(Xdv, Ydv); six = six_way(Xdv, Ydv)
    print(f"ep {ep} loss {tl/(len(Xtr)//a.bs):.3f} dev_seq {seq:.3f} dev_char {ch:.4f} dev_6way {six:.3f} t {time.time()-t0:.0f}s", flush=True)
    torch.save({"state": net.state_dict(), "width": a.width}, a.out)
print("train_time", time.time() - t0)
