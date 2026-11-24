import torch, torch.nn as nn, torch.nn.functional as F
def cbr(i,o): return nn.Sequential(nn.Conv2d(i,o,3,padding=1,bias=False),nn.BatchNorm2d(o),nn.ReLU(inplace=True))
class Net(nn.Module):
    def __init__(s,nv,w=32,cin=2):
        super().__init__()
        s.f=nn.Sequential(cbr(cin,w),cbr(w,w),nn.MaxPool2d(2),          # 37x60
                          cbr(w,2*w),cbr(2*w,2*w),nn.MaxPool2d(2),    # 18x30
                          cbr(2*w,4*w),cbr(4*w,4*w),nn.MaxPool2d(2),  # 9x15
                          cbr(4*w,8*w),cbr(8*w,8*w))
        s.drop=nn.Dropout(0.3)
        s.h1=nn.Linear(8*w*2,nv); s.h2=nn.Linear(8*w*2,nv)
    def forward(s,x):
        z=s.f(x)                                   # B,C,9,15
        # attention-free: global max + avg pooling
        z=torch.cat([F.adaptive_max_pool2d(z,1),F.adaptive_avg_pool2d(z,1)],1).flatten(1)
        z=s.drop(z)
        return s.h1(z),s.h2(z)
