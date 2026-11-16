"""Single-batch CUDA forward/backward smoke; not a matched model experiment."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

from .cesnet_input import iter_batches

EXPECTED = '340f84491dc9c5eb8173718bea15cd7fe80abf8e945adf26859a34aaa66e7816'
COUNTS_HASH = 'bd5331a573168e593ed6a5608212cbd409baa359af213c5cc4ed6ae8006493c9'
HERE = Path(__file__).parent


class Ann(nn.Module):
    def __init__(self, nclasses):
        super().__init__()
        self.encoder = nn.GRU(4, 32, batch_first=True)
        self.head = nn.Linear(32, nclasses)

    def forward(self, x, mask):
        encoded, _ = self.encoder(x)
        last = mask.sum(1).long() - 1
        return self.head(encoded[torch.arange(len(x), device=x.device), last])


class Snn(nn.Module):
    def __init__(self, nclasses):
        super().__init__()
        self.input = nn.Linear(4, 32)
        self.head = nn.Linear(32, nclasses)

    def forward(self, x, mask):
        membrane = x.new_zeros((len(x), 32))
        spikes = torch.zeros_like(membrane)
        for t in range(x.shape[1]):
            active = mask[:, t:t + 1]
            candidate = 0.9 * membrane + self.input(x[:, t])
            soft = torch.sigmoid(5.0 * (candidate - 1.0))
            hard = (candidate >= 1.0).to(x.dtype)
            spike = (hard + soft - soft.detach()) * active
            membrane = torch.where(active, candidate * (1.0 - hard.detach()), membrane)
            spikes = spikes + spike
        return self.head(spikes / mask.sum(1, keepdim=True).clamp_min(1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    digest = hashlib.sha256()
    with args.archive.open('rb') as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    if digest.hexdigest() != EXPECTED:
        raise ValueError('archive SHA-256 mismatch')
    count_path = HERE / 'CESNET_TLS_YEAR22_XS_DATE_APP_COUNTS_2026_11_10.csv'
    if hashlib.sha256(count_path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != COUNTS_HASH:
        raise ValueError('initialization census checksum mismatch')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA is not available to PyTorch')
    counts = Counter()
    with count_path.open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            if row['iso_year'] == '2022' and 11 <= int(row['iso_week']) <= 14:
                counts[int(row['app_code'])] += int(row['rows'])
    classes = sorted(code for code, count in counts.items() if count)
    lookup = {code: index for index, code in enumerate(classes)}
    batch = next(iter_batches(args.archive, ['2022-03-14'], batch_size=128, include_labels=True))
    if not batch.mask.any(axis=1).all():
        raise ValueError('empty packet sequence in smoke batch')
    torch.manual_seed(20261112)
    x = torch.as_tensor(batch.events, device='cuda', dtype=torch.float32)
    x = torch.sign(x) * torch.log1p(torch.abs(x)) / 10.0
    mask = torch.as_tensor(batch.mask, device='cuda')
    labels = torch.tensor([lookup[int(code)] for code in batch.labels], device='cuda')
    result = {'dataset_sha256': EXPECTED, 'date': '2022-03-14', 'phase': 'initialization',
              'flows': len(labels), 'classes': len(classes), 'torch_version': torch.__version__,
              'cuda_runtime': torch.version.cuda, 'gpu': torch.cuda.get_device_name(0),
              'seed': 20261112, 'event_transform': 'sign(x)*log1p(abs(x))/10; masked padding zero',
              'scope': 'single identical minibatch, one optimizer step per model; engineering smoke only', 'models': {}}
    for name, model in [('ann_gru', Ann(len(classes))), ('snn_lif_surrogate', Snn(len(classes)))]:
        model = model.cuda()
        optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
        logits = model(x, mask)
        loss = nn.functional.cross_entropy(logits, labels)
        if not torch.isfinite(logits).all() or not torch.isfinite(loss):
            raise RuntimeError(f'{name}: non-finite logits or loss')
        loss.backward()
        grads = [p.grad for p in model.parameters() if p.grad is not None]
        if not grads or not all(torch.isfinite(g).all() for g in grads):
            raise RuntimeError(f'{name}: missing or non-finite gradients')
        nonzero = any(bool(torch.count_nonzero(g)) for g in grads)
        if not nonzero:
            raise RuntimeError(f'{name}: all gradients are zero')
        encoder = model.encoder if name == 'ann_gru' else model.input
        encoder_params = list(encoder.parameters())
        if not any(p.grad is not None and bool(torch.count_nonzero(p.grad)) for p in encoder_params):
            raise RuntimeError(f'{name}: encoder has no nonzero gradients')
        before = [p.detach().clone() for p in encoder_params]
        optimizer.step()
        torch.cuda.synchronize()
        encoder_updated = any(not torch.equal(old, new) for old, new in zip(before, encoder_params))
        if not encoder_updated:
            raise RuntimeError(f'{name}: encoder parameters did not change')
        result['models'][name] = {'parameters': sum(p.numel() for p in model.parameters()),
                                  'loss_before_step': float(loss.detach().cpu()),
                                  'finite_gradients': True, 'nonzero_gradient': nonzero,
                                  'encoder_gradient_nonzero': True, 'encoder_parameters_updated': encoder_updated,
                                  'optimizer_steps': 1}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
