import json,sys,numpy as np,torch,torch.nn.functional as F
sys.path.insert(0,'.')
from model import Net
torch.set_num_threads(1)
d=json.load(open('labeled/labels.json')); sp=json.load(open('work/split.json'))
split=sys.argv[1]; X=np.load(sys.argv[2])
if X.ndim==3: X=X[:,None]
nets=[]
for p in sys.argv[3:]:
    ck=torch.load(p); n=Net(len(ck['syl']),cin=X.shape[1]); n.load_state_dict(ck['sd']); n.eval(); nets.append(n); syl=ck['syl']
V={c:k for k,c in enumerate(syl)}
idx=sp[split]
with torch.no_grad():
    P1=P2=0
    for n in nets:
        l1,l2=n(torch.from_numpy(X[idx])); P1=P1+F.log_softmax(l1,1).numpy(); P2=P2+F.log_softmax(l2,1).numpy()
c=0; nll=[]
for k,i in enumerate(idx):
    ch=d[i]['choices']; s=np.array([P1[k,V[w[0]]]+P2[k,V[w[1]]] if len(w)==2 else -1e9 for w in ch])/len(nets)
    if ch[int(np.argmax(s))]!=d[i]['answer']: print('WRONG',i,d[i]['file'],ch,d[i]['answer'],np.round(s,2))
    else: c+=1
    s=s-s.max(); nll.append(-(s[ch.index(d[i]['answer'])]-np.log(np.exp(s).sum())))
print(f'{c}/{len(idx)} nll {np.mean(nll):.4f} maxnll {np.max(nll):.3f}')
