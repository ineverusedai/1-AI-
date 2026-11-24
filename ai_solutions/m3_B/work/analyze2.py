import sys; sys.path.insert(0, sys.path[0])
from analyze import *
from formant import lpc_formants, sine_tracks

def fill(F):
    F = F.copy()
    for k in range(F.shape[1]):
        v = F[:, k]; ok = ~np.isnan(v)
        if ok.sum() < 2: F[:, k] = np.nanmean(v) if ok.any() else 1000*(k+1); continue
        F[:, k] = np.interp(np.arange(len(v)), np.where(ok)[0], v[ok])
    return F

def ffeat(F, E, we):
    e = 10*np.log10(E/E.max()+1e-12)
    idx = np.where(e > -35)[0]; s, t = idx[0], idx[-1]+1
    F = F[s:t]; e = e[s:t]
    F[e < -30] = np.nan
    L = np.log(fill(F))
    en = np.clip(e, -40, 0)/40.0
    return np.column_stack([L*np.array([1.0, 1.0, 0.5]), we*en])

def m_formant(xs, we=0.5):
    Fr, Er = lpc_formants(xs[0]); R = ffeat(Fr, Er, we)
    out = []
    for o in xs[1:]:
        F, E = sine_tracks(o); O = ffeat(F, E, we)
        D = np.abs(R[:, None, :] - O[None, :, :]).sum(-1)
        out.append(dtw(D))
    return out

if __name__ == '__main__':
    r = report('formant', m_formant)
