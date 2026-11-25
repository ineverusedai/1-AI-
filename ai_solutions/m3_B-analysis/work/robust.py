import sys, io, wave, numpy as np
sys.path.insert(0, sys.argv[1]); import solver as S
rng = np.random.default_rng(0)
base = [2, 1, 3, 3, 3, 2, 2, 4, 4, 1, 1, 1, 3, 4, 2, 3, 3, 1, 1, 1, 1, 3, 4, 2]
def toWav(x, sr=22050):
    b = io.BytesIO(); w = wave.open(b, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(np.clip(x, -32767, 32767).astype('<i2').tobytes()); w.close(); return b.getvalue()
def perturb(b, noise_db, maxpad):
    x = S._read(b) * 20000 * rng.uniform(0.3, 1.0)
    a, c = rng.integers(0, int(maxpad*22050), 2)
    x = np.concatenate([np.zeros(a), x, np.zeros(c)])
    if noise_db is not None:
        x = x + rng.normal(0, 20000 * 10**(noise_db/20), len(x))
    return toWav(x)
for noise_db, maxpad in [(None, 4.0), (-70, 4.0)]:
    wrong = []; gaps = []
    for trial in range(2):
        for q in range(1, 25):
            d = f'{sys.argv[1]}/problems/q{q:02d}'
            ref = perturb(open(f'{d}/ref.wav','rb').read(), noise_db, maxpad)
            opts = [perturb(open(f'{d}/opt{i}.wav','rb').read(), noise_db, maxpad) for i in range(1,5)]
            sc = S.scores(ref, opts)['combined']; o = np.argsort(sc)
            if o[0]+1 != base[q-1]: wrong.append((trial, q, o[0]+1))
            gaps.append(sc[o[1]] - sc[o[0]])
    print(f'noise={noise_db} pad<={maxpad}s: changed={wrong} min gap={min(gaps):.2f} mean gap={np.mean(gaps):.2f}')
