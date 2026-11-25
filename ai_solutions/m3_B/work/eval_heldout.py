# Final evaluation of the locked solver on the held-out 400 (never used for training/tuning)
import json, sys, time
import numpy as np
sys.path.insert(0, '.')
t0 = time.time(); import solver; print('import time %.2fs' % (time.time() - t0))
S = json.load(open('work/split.json')); L = {x['dir']: x['answer'] for x in json.load(open('labeled/labels.json'))}
ok = 0; times = []; wrong = []
for t in S['heldout']:
    ref = open(f'labeled/{t}/ref.wav', 'rb').read(); opts = [open(f'labeled/{t}/opt{k}.wav', 'rb').read() for k in range(1, 5)]
    t1 = time.perf_counter(); p = solver.solve(ref, opts); times.append(time.perf_counter() - t1)
    if p == L[t]: ok += 1
    else: wrong.append((t, p, L[t]))
times = np.array(times)
print(f'held-out acc {ok}/{len(S["heldout"])} = {ok / len(S["heldout"]):.4f}')
print(f'solve time mean {times.mean()*1000:.1f} ms, median {np.median(times)*1000:.1f} ms, max {times.max()*1000:.1f} ms')
print('wrong', wrong)
