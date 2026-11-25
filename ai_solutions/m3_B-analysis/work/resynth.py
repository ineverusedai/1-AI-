# validation method: synthesize sine-wave speech from ref's LPC formants, compare sine-vs-sine
import sys, numpy as np
sys.path.insert(0, sys.argv[1]); import solver as S
def synth(x):
    F, E = S._lpc_formants(x)            # 5 ms hop at 11025 -> frame times
    F = S._fill(F)
    hop = S.HOP // 2 * 2                  # in 22050 samples
    n = len(F) * hop
    t = np.arange(n) / hop
    amp = np.sqrt(E / E.max()); amp[10*np.log10(E/E.max()+1e-12) < -35] = 0
    y = np.zeros(n)
    for k, g in enumerate([1.0, 0.5, 0.25]):
        fk = np.interp(t, np.arange(len(F)), F[:, k])
        ph = 2*np.pi*np.cumsum(fk)/S.SR
        y += g*np.interp(t, np.arange(len(F)), amp)*np.sin(ph)
    return y/np.abs(y).max()
def run(q):
    d = f'{sys.argv[1]}/problems/q{q:02d}'
    xr = synth(S._read(open(f'{d}/ref.wav','rb').read()))
    Cr, Mr = S._mel_and_mfcc(*S._spec(xr))
    out = []
    for i in range(1,5):
        x = S._read(open(f'{d}/opt{i}.wav','rb').read())
        C, M = S._mel_and_mfcc(*S._spec(x))
        out.append(S._dtw(1 - Mr @ M.T))
    return np.array(out)
picks=[]
for q in range(1,25):
    v = run(q); o = np.argsort(v); z=(v-v.mean())/v.std(); picks.append(int(o[0]+1))
    print(f'q{q:02d} pick={o[0]+1} gapz={z[o[1]]-z[o[0]]:.2f} ratio={v[o[1]]/v[o[0]]:.2f}')
print(picks)
