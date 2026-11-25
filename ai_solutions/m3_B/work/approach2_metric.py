# Approach 2: learned asymmetric siamese frame metric + DTW (path-subgradient training, 4-way softmax loss)
import json, pickle, time, sys
import numpy as np, torch
sys.path.insert(0, '.')
torch.set_num_threads(2); torch.manual_seed(0)
from dtw import dtw_path
from model import Metric, prep
D = pickle.load(open('work/logmel.pkl', 'rb')); S = json.load(open('work/split.json'))
tr_all = np.array(S['train']); perm = np.random.RandomState(1).permutation(len(tr_all))
inner_va = tr_all[perm[:320]]; inner_tr = tr_all[perm[320:]]
mode = sys.argv[1] if len(sys.argv) > 1 else 'inner'
if mode == 'full': inner_tr = tr_all
EPOCHS = int(sys.argv[2]) if len(sys.argv) > 2 else 8
T = {t: (torch.tensor(prep(D[t]['ref'])), [torch.tensor(prep(o)) for o in D[t]['opts']], D[t]['ans'] - 1) for t in tr_all}
net = Metric(); opt = torch.optim.Adam(net.parameters(), lr=1e-3)

def item_costs(t, grad):
    r, os, a = T[t]
    cs = []
    for o in os:
        C = net.cost(r, o)
        c, ii, jj = dtw_path(C.detach().numpy().astype(np.float64))
        if ii is None: cs.append(torch.tensor(10.0)); continue
        cs.append(C[ii, jj].sum() / (C.shape[0] + C.shape[1]))
    return torch.stack(cs), a

def evaluate(ts):
    net.eval(); ok = 0; marg = []
    with torch.no_grad():
        for t in ts:
            c, a = item_costs(t, False); c = c.numpy(); ok += int(c.argmin() == a)
            marg.append(np.delete(c, a).min() - c[a])
    net.train(); return ok, np.array(marg)

t_start = time.time()
ok, m = evaluate(inner_va if mode == 'inner' else tr_all[:200]); print('init val', ok, 'min margin %.4f' % m.min(), flush=True)
for ep in range(EPOCHS):
    t0 = time.time(); rng = np.random.RandomState(ep); order = rng.permutation(inner_tr); tl = 0
    for bi in range(0, len(order), 16):
        loss = 0
        for t in order[bi:bi + 16]:
            c, a = item_costs(t, True)
            loss = loss + torch.nn.functional.cross_entropy((-c * net.logscale.exp() * 10).unsqueeze(0), torch.tensor([a]))
        loss = loss / len(order[bi:bi + 16]); opt.zero_grad(); loss.backward(); opt.step(); tl += loss.item()
    msg = f'ep {ep} loss {tl / (len(order) / 16):.4f} time {time.time() - t0:.0f}s'
    if mode == 'inner':
        ok, m = evaluate(inner_va); msg += f' | inner-val {ok}/{len(inner_va)} min margin {m.min():.4f} p5 {np.percentile(m, 5):.4f}'
    print(msg, flush=True)
print('train time %.1fs' % (time.time() - t_start))
torch.save(net.state_dict(), f'work/metric_{mode}.pt')
