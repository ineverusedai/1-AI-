import sys, time, numpy as np
sys.path.insert(0, sys.argv[1])
import solver
B = sys.argv[1] + '/problems'
picks = []; tt = []
for q in range(1, 25):
    d = f'{B}/q{q:02d}'
    ref = open(f'{d}/ref.wav','rb').read(); opts = [open(f'{d}/opt{i}.wav','rb').read() for i in range(1,5)]
    t0 = time.time(); p = solver.solve(ref, opts); tt.append(time.time()-t0)
    sc = solver.scores(ref, opts)
    line = []
    for k in ['mfcc','mel','formant','resynth','combined']:
        v = sc[k]; o = np.argsort(v); z = (v - v.mean())/v.std()
        line.append(f"{k}:{o[0]+1}(gapz={z[o[1]]-z[o[0]]:.2f},ratio={v[o[1]]/v[o[0]] if k!='combined' else 0:.2f})")
    picks.append(p)
    print(f'q{q:02d} -> {p}  ' + '  '.join(line))
print('picks', picks)
print('time per q: mean %.3f max %.3f' % (np.mean(tt), np.max(tt)))
