"""Exploratory supervised ANN/SNN pilot on sparse initialization labels, evaluated on W15."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import tables
import torch
from torch import nn

from .cesnet_input import iter_batches
from .cesnet_prequential import run_week
from .smoke_cesnet_cuda_models import Ann, Snn, EXPECTED, COUNTS_HASH, HERE

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('archive', type=Path)
parser.add_argument('--output-dir', type=Path, required=True)
parser.add_argument('--summary-path', type=Path, required=True)
parser.add_argument('--profile', choices=('baseline', 'balanced'), default='baseline')
parser.add_argument('--epochs', type=int)
parser.add_argument('--snn-only', action='store_true')
args = parser.parse_args()
if args.output_dir.exists():
    raise ValueError('output directory must not already exist')
args.output_dir.mkdir(parents=True)
digest = hashlib.sha256()
with args.archive.open('rb') as stream:
    while block := stream.read(8 * 1024 * 1024):
        digest.update(block)
if digest.hexdigest() != EXPECTED:
    raise ValueError('archive checksum mismatch')
count_path = HERE / 'CESNET_TLS_YEAR22_XS_DATE_APP_COUNTS_2026_11_10.csv'
if hashlib.sha256(count_path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != COUNTS_HASH:
    raise ValueError('census checksum mismatch')
if not torch.cuda.is_available():
    raise RuntimeError('CUDA unavailable')
counts = Counter()
with count_path.open(encoding='utf-8', newline='') as stream:
    for row in csv.DictReader(stream):
        if row['iso_year'] == '2022' and 11 <= int(row['iso_week']) <= 14:
            counts[int(row['app_code'])] += int(row['rows'])
classes = np.asarray(sorted(code for code, n in counts.items() if n), dtype=np.int32)
manifest = HERE / 'CESNET_TLS_YEAR22_XS_SPLIT_MANIFEST_2026_11_10.csv'
if hashlib.sha256(manifest.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != '9eb553e31354665e5d15b5b4b0f4f1f13bac0b252562c9350f772d0e0aa4f33d':
    raise ValueError('split manifest checksum mismatch')
with manifest.open(encoding='utf-8', newline='') as stream:
    split = list(csv.DictReader(stream))
weeks = {w: [r['date'] for r in split if r['iso_year'] == '2022' and int(r['iso_week']) == w] for w in range(11, 16)}

# Choose row positions without using class labels; only selected labels enter training.
rng = np.random.default_rng(20261112)
events, masks, targets, selected_refs = [], [], [], []
with tables.open_file(args.archive) as archive:
    populations = {w: sum(archive.get_node('/flows/D' + d.replace('-', '')).nrows for d in weeks[w]) for w in range(11, 15)}
for week in range(11, 15):
    chosen = np.sort(rng.choice(populations[week], size=1000, replace=False))
    offset = 0
    for batch in iter_batches(args.archive, weeks[week], include_labels=True):
        positions = np.flatnonzero(np.isin(np.arange(offset, offset + len(batch.row_indices)), chosen))
        if positions.size:
            events.append(batch.events[positions])
            masks.append(batch.mask[positions])
            targets.append(batch.labels[positions])
            selected_refs.extend(f'{batch.dates[i]}:{int(batch.row_indices[i])}' for i in positions)
        offset += len(batch.row_indices)
    if offset != populations[week]:
        raise RuntimeError('week population changed during sampling')
events, masks, targets = np.concatenate(events), np.concatenate(masks), np.concatenate(targets)
if len(targets) != 4000 or not np.isin(targets, classes).all():
    raise RuntimeError('initial sample or class vocabulary mismatch')
transformed = np.sign(events) * np.log1p(np.abs(events.astype(np.float32)))
if args.profile == 'balanced':
    valid = transformed[masks]
    means = valid.mean(axis=0)
    scales = valid.std(axis=0)
    scales[scales < 1e-6] = 1.0
    transformed = ((transformed - means) / scales) * masks[..., None]
else:
    means, scales = np.zeros(4), np.full(4, 10.0)
    transformed = transformed / 10.0
x_cpu = torch.tensor(transformed, dtype=torch.float32)
mask_cpu = torch.tensor(masks)
y_cpu = torch.tensor(np.searchsorted(classes, targets), dtype=torch.long)
class_counts = np.bincount(np.searchsorted(classes, targets), minlength=len(classes))
weights = np.zeros(len(classes), dtype=np.float32)
present = class_counts > 0
weights[present] = 1 / np.sqrt(class_counts[present])
weights[present] /= weights[present].mean()
class_weights = torch.tensor(weights, device='cuda') if args.profile == 'balanced' else None
epochs = args.epochs if args.epochs is not None else (20 if args.profile == 'balanced' else 5)
if epochs <= 0:
    raise ValueError('epochs must be positive')
torch.manual_seed(20261112)
result = {'dataset_sha256': EXPECTED, 'scope': 'development pilot; no SSL, no continual updates, no held-out test',
          'initialization_weeks': [11, 12, 13, 14], 'label_budget_per_week': 1000,
          'label_sampling_seed': 20261112, 'initialization_labels': len(targets),
          'initialization_label_classes': int(len(np.unique(targets))),
          'sampled_row_ids_sha256': hashlib.sha256('\n'.join(selected_refs).encode()).hexdigest(),
          'vocabulary_source': 'all APP classes observed in full W11-W14 census; oracle taxonomy',
          'evaluation_week': 15, 'profile': args.profile, 'training_epochs': epochs, 'batch_size': 128,
          'optimizer': 'Adam lr=0.001', 'event_transform': 'signed log1p, centered and scaled using sampled initialization events' if args.profile == 'balanced' else 'sign(x)*log1p(abs(x))/10',
          'event_mean': means.tolist(), 'event_scale': scales.tolist(),
          'loss': 'inverse square-root class frequency weights from sampled initialization labels' if args.profile == 'balanced' else 'unweighted cross entropy',
          'torch_version': torch.__version__, 'cuda_runtime': torch.version.cuda,
          'gpu': torch.cuda.get_device_name(0), 'models': {}}
models = [('ann_gru', Ann(len(classes))), ('snn_lif_surrogate', Snn(len(classes)))]
if args.snn_only:
    models = models[1:]
for name, model in models:
    model = model.cuda()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    order_rng = np.random.default_rng(20261113)
    started = time.perf_counter()
    model.train()
    epoch_losses = []
    for epoch in range(epochs):
        order = order_rng.permutation(len(targets))
        loss_sum = 0.0
        for start in range(0, len(order), 128):
            idx = order[start:start + 128]
            x, mask, y = x_cpu[idx].cuda(), mask_cpu[idx].cuda(), y_cpu[idx].cuda()
            optimizer.zero_grad(set_to_none=True)
            loss = nn.functional.cross_entropy(model(x, mask), y, weight=class_weights)
            if not torch.isfinite(loss):
                raise RuntimeError(f'{name}: non-finite loss')
            loss.backward()
            optimizer.step()
            loss_sum += float(loss.detach()) * len(idx)
        epoch_losses.append(loss_sum / len(targets))
    torch.cuda.synchronize()
    train_seconds = time.perf_counter() - started
    checkpoint = args.output_dir / f'{name}.pt'
    torch.save({'model': model.state_dict(), 'classes': classes.tolist(), 'event_mean': means.tolist(), 'event_scale': scales.tolist()}, checkpoint)
    model.eval()
    def predict(batch):
        with torch.inference_mode():
            values = torch.as_tensor(batch.events, device='cuda', dtype=torch.float32)
            mask = torch.as_tensor(batch.mask, device='cuda')
            values = torch.sign(values) * torch.log1p(torch.abs(values))
            values = ((values - torch.as_tensor(means, device='cuda', dtype=torch.float32)) / torch.as_tensor(scales, device='cuda', dtype=torch.float32)) * mask.unsqueeze(-1)
            return classes[model(values, mask).argmax(dim=1).cpu().numpy()]
    score, released = run_week(args.archive, weeks[15], predict, classes, 1000, 20261114,
                               args.output_dir / f'{name}_w15_predictions.npz', batch_size=2048)
    with np.load(args.output_dir / f'{name}_w15_predictions.npz') as sealed:
        predicted_codes, predicted_counts = np.unique(sealed['prediction'], return_counts=True)
    result['models'][name] = {'parameters': sum(p.numel() for p in model.parameters()),
                              'training_steps': epochs * ((len(targets) + 127) // 128),
                              'epoch_losses': epoch_losses,
                              'predicted_classes': len(predicted_codes),
                              'most_common_prediction_fraction': float(predicted_counts.max() / predicted_counts.sum()),
                              'training_seconds': train_seconds, 'score': score,
                              'released_label_count': len(released),
                              'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest()}
args.summary_path.parent.mkdir(parents=True, exist_ok=True)
args.summary_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
