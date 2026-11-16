"""Fit temperature on half the released W15 labels and evaluate the other half."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import tables
import torch
from torch.nn import functional as F

from .cesnet_replay_ssl_pilot import select_positions
from .smoke_cesnet_cuda_models import Ann, Snn, EXPECTED, HERE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--pilot-dir', required=True, type=Path)
    parser.add_argument('--pilot-summary', required=True, type=Path)
    parser.add_argument('--confidence-summary', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    digest = hashlib.sha256()
    with args.archive.open('rb') as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    if digest.hexdigest() != EXPECTED:
        raise ValueError('archive checksum mismatch')
    pilot = json.loads(args.pilot_summary.read_text(encoding='utf-8'))
    confidence = json.loads(args.confidence_summary.read_text(encoding='utf-8'))
    if pilot['dataset_sha256'] != EXPECTED or pilot['profile'] != 'balanced' or confidence['dataset_sha256'] != EXPECTED:
        raise ValueError('unexpected input provenance')
    manifest = HERE / 'CESNET_TLS_YEAR22_XS_SPLIT_MANIFEST_2026_11_10.csv'
    if hashlib.sha256(manifest.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != '9eb553e31354665e5d15b5b4b0f4f1f13bac0b252562c9350f772d0e0aa4f33d':
        raise ValueError('split manifest checksum mismatch')
    with manifest.open(encoding='utf-8', newline='') as stream:
        dates = [r['date'] for r in csv.DictReader(stream) if r['iso_year'] == '2022' and r['iso_week'] == '15']
    with tables.open_file(args.archive) as archive:
        population = sum(archive.get_node('/flows/D' + d.replace('-', '')).nrows for d in dates)
    labeled_positions = np.sort(np.random.default_rng(20261129).choice(population, 1000, replace=False))
    pool = np.setdiff1d(np.arange(population), labeled_positions, assume_unique=True)
    unlabeled_positions = np.sort(np.random.default_rng(20261315).choice(pool, 1000, replace=False))
    lx, lm, ly, lrefs = select_positions(args.archive, dates, labeled_positions, labels=True)
    ux, um, _, urefs = select_positions(args.archive, dates, unlabeled_positions, labels=False)
    lhash = hashlib.sha256('\n'.join(f'{d}:{i}' for d, i in lrefs).encode()).hexdigest()
    uhash = hashlib.sha256('\n'.join(f'{d}:{i}' for d, i in urefs).encode()).hexdigest()
    if lhash != confidence['labeled_row_ids_sha256'] or uhash != confidence['unlabeled_row_ids_sha256'] or set(lrefs) & set(urefs):
        raise ValueError('W15 sample mismatch')
    indices = np.random.default_rng(20261130).permutation(1000)
    fit, valid = indices[:500], indices[500:]
    if set(fit) & set(valid):
        raise RuntimeError('calibration and validation overlap')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    temperatures = np.unique(np.append(np.geomspace(0.2, 5.0, 41), 1.0))
    result = {'dataset_sha256': EXPECTED, 'week': 15,
              'scope': 'W15 development diagnostic; fit 500 released labels, evaluate 500 disjoint released labels, no update',
              'labeled_row_ids_sha256': lhash, 'unlabeled_row_ids_sha256': uhash,
              'split_seed': 20261130, 'fit_rows': len(fit), 'validation_rows': len(valid),
              'fit_positions_sha256': hashlib.sha256(fit.astype('<i8').tobytes()).hexdigest(),
              'temperature_grid': temperatures.tolist(), 'models': {}}
    for name, constructor in [('ann_gru', Ann), ('snn_lif_surrogate', Snn)]:
        checkpoint = args.pilot_dir / f'{name}.pt'
        if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != pilot['models'][name]['checkpoint_sha256']:
            raise ValueError('checkpoint checksum mismatch')
        saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
        classes = np.asarray(saved['classes'], dtype=np.int32)
        if not np.isin(ly, classes).all():
            raise ValueError('label outside frozen vocabulary')
        means = torch.tensor(saved['event_mean'], device='cuda', dtype=torch.float32)
        scales = torch.tensor(saved['event_scale'], device='cuda', dtype=torch.float32)
        model = constructor(len(classes)).cuda()
        model.load_state_dict(saved['model']); model.eval()
        def infer(x, mask):
            with torch.inference_mode():
                x = torch.as_tensor(x, device='cuda', dtype=torch.float32)
                mask = torch.as_tensor(mask, device='cuda')
                x = ((torch.sign(x) * torch.log1p(torch.abs(x)) - means) / scales) * mask.unsqueeze(-1)
                return model(x, mask)
        labeled_logits = infer(lx, lm)
        unlabeled_logits = infer(ux, um)
        targets = torch.tensor(np.searchsorted(classes, ly), device='cuda', dtype=torch.long)
        fit_nll = [float(F.cross_entropy(labeled_logits[fit] / t, targets[fit]).cpu()) for t in temperatures]
        best = float(temperatures[int(np.argmin(fit_nll))])
        assessments = []
        for temperature in (1.0, best):
            probs = torch.softmax(labeled_logits[valid] / temperature, dim=1)
            uc = torch.softmax(unlabeled_logits / temperature, dim=1).max(dim=1).values.cpu().numpy()
            lc, li = probs.max(dim=1)
            lc, li = lc.cpu().numpy(), li.cpu().numpy()
            row = {'temperature': temperature, 'fit_nll': float(F.cross_entropy(labeled_logits[fit] / temperature, targets[fit]).cpu()),
                   'validation_nll': float(F.cross_entropy(labeled_logits[valid] / temperature, targets[valid]).cpu()),
                   'thresholds': []}
            for threshold in (0.5, 0.8):
                accepted = lc >= threshold
                row['thresholds'].append({'threshold': threshold, 'validation_accepted': int(accepted.sum()),
                                          'validation_correct': int(np.sum(classes[li[accepted]] == ly[valid][accepted])),
                                          'unlabeled_accepted': int(np.count_nonzero(uc >= threshold))})
            assessments.append(row)
        result['models'][name] = {'checkpoint_sha256': pilot['models'][name]['checkpoint_sha256'],
                                  'selected_temperature': best, 'assessments': assessments}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
