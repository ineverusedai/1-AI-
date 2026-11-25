import torch, torch.nn as nn, torch.nn.functional as Fn


class Enc(nn.Module):
    """Per-frame encoder: 1D conv over time on log-mel frames -> unit-norm embedding."""
    def __init__(self, nin=64, nh=128, nout=48):
        super().__init__()
        self.net = nn.Sequential(nn.Conv1d(nin, nh, 5, padding=2), nn.GELU(),
                                 nn.Conv1d(nh, nh, 3, padding=1), nn.GELU(),
                                 nn.Conv1d(nh, nout, 1))
        self.skip = nn.Conv1d(nin, nout, 1, bias=False)

    def forward(self, x):  # x: T,F (already CMN-normalized)
        x = x.t().unsqueeze(0)
        y = self.net(x) + self.skip(x)
        return Fn.normalize(y.squeeze(0).t(), dim=1)


class Metric(nn.Module):
    """Asymmetric siamese: one encoder for clean speech (ref), one for sine-wave speech (options)."""
    def __init__(self):
        super().__init__()
        self.er = Enc(); self.eo = Enc()
        self.logscale = nn.Parameter(torch.tensor(3.0))

    def cost(self, r, o):
        return 1 - self.er(r) @ self.eo(o).t()


def prep(X):
    X = X - X.mean(0)
    return X / (X.std() + 1e-6)
