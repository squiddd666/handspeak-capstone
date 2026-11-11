"""Versioned, from-scratch masked temporal candidate; no production promotion."""
import torch
from torch import nn


def temporal_features(x):
    # x: N,4,T,27. Zero missing coordinates and avoid velocities across gaps.
    n, _, t, _ = x.shape
    visible = torch.ones((n, t, 27), dtype=x.dtype, device=x.device)
    visible[:, :, 7:17] = x[:, 2, :, 7:17]
    visible[:, :, 17:27] = x[:, 3, :, 17:27]
    xy = x[:, :2] * visible[:, None]
    velocity = torch.zeros_like(xy)
    velocity[:, :, 1:] = (xy[:, :, 1:] - xy[:, :, :-1]) * (visible[:, None, 1:] * visible[:, None, :-1])
    local = []
    for a, b in [(7, 17), (17, 27)]:
        hand = xy[:, :, :, a:b]
        width = torch.linalg.vector_norm(hand[:, :, :, 2] - hand[:, :, :, 8], dim=1).clamp(min=.04)
        local.append(((hand - hand[:, :, :, :1]) / width[:, None, :, None]) * visible[:, None, :, a:b])
    flatten = lambda y: y.permute(0, 1, 3, 2).reshape(n, -1, t)
    return torch.cat([flatten(xy), flatten(velocity), *(flatten(h) for h in local),
                      visible[:, :, 7:].transpose(1, 2)], dim=1).clamp(-12, 12)


class TemporalCandidate(nn.Module):
    def __init__(self, width=64, classes=21):
        super().__init__()
        self.project = nn.Sequential(nn.Conv1d(168, width, 5, padding=2), nn.GroupNorm(8, width), nn.GELU())
        self.blocks = nn.ModuleList([nn.Sequential(nn.Conv1d(width, width, 3, padding=d, dilation=d),
                                                  nn.GroupNorm(8, width), nn.GELU(), nn.Dropout(.2),
                                                  nn.Conv1d(width, width, 1)) for d in (1, 2, 4)])
        self.head = nn.Sequential(nn.AdaptiveAvgPool1d(4), nn.Flatten(), nn.Dropout(.25), nn.Linear(width * 4, classes))

    def forward(self, x):
        h = self.project(temporal_features(x))
        for block in self.blocks:
            h = torch.nn.functional.gelu(h + block(h))
        return self.head(h)

    def embedding(self, x):
        h = self.project(temporal_features(x))
        for block in self.blocks:
            h = torch.nn.functional.gelu(h + block(h))
        return self.head[:2](h)


class RBFCandidate(nn.Module):
    """Kernel-ridge head: distant embeddings decay toward uncertainty."""
    def __init__(self, support_count, width=64, gamma=8., temperature=.15):
        super().__init__()
        self.encoder = TemporalCandidate(width)
        self.gamma = gamma; self.temperature = temperature
        self.register_buffer('mean', torch.zeros(256))
        self.register_buffer('scale', torch.ones(256))
        self.register_buffer('support', torch.zeros(support_count,256))
        self.register_buffer('coefficients', torch.zeros(support_count,21))

    def forward(self, x):
        z = torch.nn.functional.normalize((self.encoder.embedding(x)-self.mean)/self.scale,dim=1)
        squared = (z*z).sum(1)[:,None]+(self.support*self.support).sum(1)[None]-2*z@self.support.T
        return (torch.exp(-self.gamma*squared.clamp(min=0))@self.coefficients)/self.temperature
