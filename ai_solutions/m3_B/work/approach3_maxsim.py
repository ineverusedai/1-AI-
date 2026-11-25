# Approach 3: DTW-free siamese — learned frame encoders + soft MaxSim (non-monotonic soft alignment), 4-way softmax
# Also variant 'pool': utterance-level embedding by mean pooling (no alignment at all)
import json, pickle, time, sys
import numpy as np, torch, torch.nn.functional as Fn
sys.path.insert(0, '.')
torch.set_num_threads(2); torch.manual_seed(0)
from model import Metric, prep
D = pickle.load(open('work/logmel.pkl', 'rb')); S = json.load(open('work/split.json'))
tr_all = np.array(S['train']); perm = np.random.RandomState(1).permutation(len(tr_all))
inner_va = tr_all[perm[:320]]; inner_tr = tr_all[perm[320:]]
variant = sys.argv[1]; EPOCHS = int(sys.argv[2])
T = {t: (torch.tensor(prep(D[t]['ref'])), [torch.tensor(prep(o)) for o in D[t]['opts']], D[t]['ans'] - 1) for t in tr_all}
net = Metric(); opt = torch.optim.Adam(net.parameters(), lr=1e-3)
def score(t):
    r, os, a = T[t]; er = net.er(r); s = []
    for o in os:
        eo = net.eo(o)
        if variant == 'pool':
            s.append(Fn.cosine_similarity(er.mean(0), eo.mean(0), dim=0))
        else:
            M = er @ eo.t() * 20
            s.append(0.5 * (torch.logsumexp(M, 1).mean() + torch.logsumexp(M, 0).mean()) / 20)
    return torch.stack(s), a
def evaluate(ts):
    net.eval(); ok = 0
    with torch.no_grad():
        for t in ts:
            s, a = score(t); ok += int(s.argmax().item() == a)
    net.train(); return ok
t_start = time.time()
for ep in range(EPOCHS):
    t0 = time.time(); order = np.random.RandomState(ep).permutation(inner_tr); tl = 0
    for bi in range(0, len(order), 16):
        loss = 0
        for t in order[bi:bi + 16]:
            s, a = score(t); loss = loss + Fn.cross_entropy((s * net.logscale.exp() * 10).unsqueeze(0), torch.tensor([a]))
        loss = loss / 16; opt.zero_grad(); loss.backward(); opt.step(); tl += loss.item()
    print(f'{variant} ep {ep} loss {tl / (len(order) / 16):.4f} time {time.time() - t0:.0f}s inner-val {evaluate(inner_va)}/{len(inner_va)}', flush=True)
print('train time %.1fs' % (time.time() - t_start))
