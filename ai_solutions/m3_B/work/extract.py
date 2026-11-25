import json, sys, time, pickle
import numpy as np
sys.path.insert(0, '.')
from feats import read_wav, logmel
L = json.load(open('labeled/labels.json'))
t0 = time.time()
out = {}
for x in L:
    t = x['dir']
    out[t] = {'ans': x['answer'],
              'ref': logmel(read_wav(f'labeled/{t}/ref.wav')),
              'opts': [logmel(read_wav(f'labeled/{t}/opt{k}.wav')) for k in range(1, 5)]}
pickle.dump(out, open('work/logmel.pkl', 'wb'))
print('done', time.time() - t0)
