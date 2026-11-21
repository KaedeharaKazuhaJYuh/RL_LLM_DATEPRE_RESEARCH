"""Evaluate frozen balanced pilot checkpoints on later development weeks without updates."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from .cesnet_prequential import run_week
from .smoke_cesnet_cuda_models import Ann, Snn, EXPECTED, HERE

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('archive', type=Path)
parser.add_argument('--pilot-dir', required=True, type=Path)
parser.add_argument('--pilot-summary', required=True, type=Path)
parser.add_argument('--output-dir', required=True, type=Path)
parser.add_argument('--summary-path', required=True, type=Path)
parser.add_argument('--snn-only', action='store_true')
args = parser.parse_args()
if args.output_dir.exists():
    raise ValueError('output directory must not already exist')
args.output_dir.mkdir(parents=True)
h = hashlib.sha256()
with args.archive.open('rb') as stream:
    while block := stream.read(8 * 1024 * 1024):
        h.update(block)
if h.hexdigest() != EXPECTED:
    raise ValueError('archive checksum mismatch')
pilot = json.loads(args.pilot_summary.read_text(encoding='utf-8'))
if pilot['dataset_sha256'] != EXPECTED or pilot['profile'] != 'balanced':
    raise ValueError('unexpected pilot provenance')
manifest = HERE / 'CESNET_TLS_YEAR22_XS_SPLIT_MANIFEST_2026_11_10.csv'
if hashlib.sha256(manifest.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != '9eb553e31354665e5d15b5b4b0f4f1f13bac0b252562c9350f772d0e0aa4f33d':
    raise ValueError('split manifest checksum mismatch')
with manifest.open(encoding='utf-8', newline='') as stream:
    rows = list(csv.DictReader(stream))
weeks = {w: [r['date'] for r in rows if r['iso_year'] == '2022' and int(r['iso_week']) == w] for w in (16, 17, 18)}
if not torch.cuda.is_available():
    raise RuntimeError('CUDA unavailable')
results = {'dataset_sha256': EXPECTED, 'scope': 'static frozen models on development weeks only; no continual update',
           'pilot_profile': 'balanced tuned using W15', 'torch_version': torch.__version__,
           'gpu': torch.cuda.get_device_name(0), 'models': {}}
models = [('snn_lif_surrogate', Snn)] if args.snn_only else [('ann_gru', Ann), ('snn_lif_surrogate', Snn)]
for name, constructor in models:
    checkpoint = args.pilot_dir / f'{name}.pt'
    expected = pilot['models'][name]['checkpoint_sha256']
    if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != expected:
        raise ValueError(f'{name}: checkpoint checksum mismatch')
    saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
    classes = np.asarray(saved['classes'], dtype=np.int32)
    means = torch.tensor(saved['event_mean'], device='cuda', dtype=torch.float32)
    scales = torch.tensor(saved['event_scale'], device='cuda', dtype=torch.float32)
    model = constructor(len(classes)).cuda()
    model.load_state_dict(saved['model'])
    model.eval()
    def predict(batch):
        with torch.inference_mode():
            values = torch.as_tensor(batch.events, device='cuda', dtype=torch.float32)
            mask = torch.as_tensor(batch.mask, device='cuda')
            values = ((torch.sign(values) * torch.log1p(torch.abs(values)) - means) / scales) * mask.unsqueeze(-1)
            return classes[model(values, mask).argmax(dim=1).cpu().numpy()]
    per_week = {}
    for week, dates in weeks.items():
        prediction_path = args.output_dir / f'{name}_w{week}_predictions.npz'
        score, released = run_week(args.archive, dates, predict, classes, 1000, 20261114 + week,
                                   prediction_path, batch_size=2048)
        with np.load(prediction_path) as sealed:
            _, predicted_counts = np.unique(sealed['prediction'], return_counts=True)
        per_week[str(week)] = {'score': score, 'released_label_count': len(released),
                               'predicted_classes': len(predicted_counts),
                               'most_common_prediction_fraction': float(predicted_counts.max() / predicted_counts.sum())}
    results['models'][name] = {'checkpoint_sha256': expected, 'weeks': per_week}
args.summary_path.parent.mkdir(parents=True, exist_ok=True)
args.summary_path.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
print(json.dumps(results, indent=2))
