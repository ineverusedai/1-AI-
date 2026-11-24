import json,sys,numpy as np,time
sys.path.insert(0,'.')
from prep import preprocess,decode
d=json.load(open('labeled/labels.json'))
t=time.time()
X=np.stack([preprocess(decode(open('labeled/'+x['file'],'rb').read())) for x in d])
np.save(sys.argv[1] if len(sys.argv)>1 else 'work/X.npy',X); print(X.shape,time.time()-t)
rng=np.random.RandomState(12345); perm=rng.permutation(len(d))
split={'holdout':sorted(perm[:600].tolist()),'val':sorted(perm[600:900].tolist()),'train':sorted(perm[900:].tolist())}
pass
print({k:len(v) for k,v in split.items()})
