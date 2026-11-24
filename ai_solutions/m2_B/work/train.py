import json,sys,time,numpy as np,torch,torch.nn.functional as F,math
sys.path.insert(0,'.')
from model import Net
torch.set_num_threads(4); torch.manual_seed(int(sys.argv[3]) if len(sys.argv)>3 else 0); np.random.seed(0)
d=json.load(open('labeled/labels.json')); X=np.load(sys.argv[5] if len(sys.argv)>5 else 'work/X.npy'); sp=json.load(open('work/split.json'))
trn=sp['train']+ (sp['val'] if len(sys.argv)>2 and sys.argv[2]=='full' else [])
val=sp['val']
syl=sorted({c for i in trn for w in d[i]['choices'] if len(w)==2 for c in w})
V={c:k for k,c in enumerate(syl)}
y=np.array([[V.get(d[i]['answer'][0],-1),V.get(d[i]['answer'][1],-1)] for i in range(len(d))])
EP=int(sys.argv[1]) if len(sys.argv)>1 else 30
net=Net(len(syl),cin=X.shape[1]); opt=torch.optim.AdamW(net.parameters(),2e-3,weight_decay=5e-4)
BS=64; steps=EP*math.ceil(len(trn)/BS)
sch=torch.optim.lr_scheduler.OneCycleLR(opt,3e-3,total_steps=steps,pct_start=0.2)
def aug(xb):
    B=xb.shape[0]; H,W=xb.shape[2],xb.shape[3]
    th=torch.zeros(B,2,3); sc=torch.empty(B).uniform_(0.85,1.15); rot=torch.empty(B).uniform_(-0.08,0.08)
    th[:,0,0]=sc*torch.cos(rot); th[:,0,1]=-sc*torch.sin(rot)*H/W; th[:,1,0]=sc*torch.sin(rot)*W/H; th[:,1,1]=sc*torch.cos(rot)*torch.empty(B).uniform_(0.9,1.1)
    th[:,0,2]=torch.empty(B).uniform_(-0.25,0.25); th[:,1,2]=torch.empty(B).uniform_(-0.25,0.25)
    g=F.affine_grid(th,xb.shape,align_corners=False)
    xb=F.grid_sample(xb,g,padding_mode='reflection',align_corners=False)
    xb=xb+torch.randn_like(xb)*torch.empty(B,1,1,1).uniform_(0,0.4)
    return xb
def evaluate(idx):
    net.eval(); c=0; nll=[]
    with torch.no_grad():
        l1,l2=net(torch.from_numpy(X[idx]))
        p1=F.log_softmax(l1,1).numpy(); p2=F.log_softmax(l2,1).numpy()
    for k,i in enumerate(idx):
        ch=d[i]['choices']; s=[p1[k,V[w[0]]]+p2[k,V[w[1]]] if len(w)==2 and w[0] in V and w[1] in V else -1e9 for w in ch]
        c+=ch[int(np.argmax(s))]==d[i]['answer']
        s=np.array(s); s=s-s.max(); nll.append(-(s[ch.index(d[i]['answer'])]-np.log(np.exp(s).sum())))
    net.train(); return f'{c} nll {np.mean(nll):.4f} maxnll {np.max(nll):.3f}'
t0=time.time()
for ep in range(EP):
    perm=np.random.permutation(trn); tl=0
    for b in range(0,len(perm),BS):
        ix=perm[b:b+BS]; xb=aug(torch.from_numpy(X[ix])); yb=torch.from_numpy(y[ix])
        l1,l2=net(xb); loss=F.cross_entropy(l1,yb[:,0],label_smoothing=0.05)+F.cross_entropy(l2,yb[:,1],label_smoothing=0.05)
        opt.zero_grad(); loss.backward(); opt.step(); sch.step(); tl+=loss.item()*len(ix)
    print(f'ep{ep} loss {tl/len(trn):.3f} val {evaluate(val)}/{len(val)} t {time.time()-t0:.0f}s',flush=True)
torch.save({'sd':net.state_dict(),'syl':syl},sys.argv[4] if len(sys.argv)>4 else 'work/net.pt')
print('train_time',time.time()-t0)
