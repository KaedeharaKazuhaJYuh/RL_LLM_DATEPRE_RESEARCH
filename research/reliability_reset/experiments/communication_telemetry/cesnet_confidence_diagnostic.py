"""Descriptive W15 confidence/precision diagnostic; not threshold selection or a model update."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import tables
import torch

from .cesnet_replay_ssl_pilot import select_positions
from .smoke_cesnet_cuda_models import Ann, Snn, EXPECTED, HERE


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--pilot-dir', required=True, type=Path)
    parser.add_argument('--pilot-summary', required=True, type=Path)
    parser.add_argument('--summary-path', required=True, type=Path)
    args = parser.parse_args()
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
        raise ValueError('split checksum mismatch')
    with manifest.open(encoding='utf-8', newline='') as stream:
        dates = [r['date'] for r in csv.DictReader(stream) if r['iso_year'] == '2022' and r['iso_week'] == '15']
    with tables.open_file(args.archive) as archive:
        population = sum(archive.get_node('/flows/D' + d.replace('-', '')).nrows for d in dates)
    labeled = np.sort(np.random.default_rng(20261129).choice(population, 1000, replace=False))
    pool = np.setdiff1d(np.arange(population), labeled, assume_unique=True)
    unlabeled = np.sort(np.random.default_rng(20261315).choice(pool, 1000, replace=False))
    lx, lm, ly, lrefs = select_positions(args.archive, dates, labeled, labels=True)
    ux, um, _, urefs = select_positions(args.archive, dates, unlabeled, labels=False)
    if set(lrefs) & set(urefs):
        raise RuntimeError('labeled/unlabeled overlap')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    result = {'dataset_sha256': EXPECTED, 'week': 15, 'scope': 'post-hoc development diagnostic; no training, no threshold selection',
              'labeled_rows': len(ly), 'unlabeled_rows': len(ux), 'thresholds': [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.8],
              'labeled_row_ids_sha256': hashlib.sha256('\n'.join(f'{d}:{i}' for d, i in lrefs).encode()).hexdigest(),
              'unlabeled_row_ids_sha256': hashlib.sha256('\n'.join(f'{d}:{i}' for d, i in urefs).encode()).hexdigest(),
              'models': {}}
    for name, constructor in [('ann_gru', Ann), ('snn_lif_surrogate', Snn)]:
        checkpoint = args.pilot_dir / f'{name}.pt'
        if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != pilot['models'][name]['checkpoint_sha256']:
            raise ValueError('checkpoint checksum mismatch')
        saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
        classes = np.asarray(saved['classes'], dtype=np.int32)
        means = torch.tensor(saved['event_mean'], device='cuda', dtype=torch.float32)
        scales = torch.tensor(saved['event_scale'], device='cuda', dtype=torch.float32)
        model = constructor(len(classes)).cuda(); model.load_state_dict(saved['model']); model.eval()
        def infer(x, mask):
            with torch.inference_mode():
                x = torch.as_tensor(x, device='cuda', dtype=torch.float32)
                mask = torch.as_tensor(mask, device='cuda')
                x = ((torch.sign(x) * torch.log1p(torch.abs(x)) - means) / scales) * mask.unsqueeze(-1)
                prob = torch.softmax(model(x, mask), dim=1)
                confidence, index = prob.max(dim=1)
                return confidence.cpu().numpy(), classes[index.cpu().numpy()]
        lc, lp = infer(lx, lm)
        uc, _ = infer(ux, um)
        rows = []
        for threshold in result['thresholds']:
            mask = lc >= threshold
            n = int(mask.sum())
            rows.append({'threshold': threshold, 'labeled_accepted': n,
                         'labeled_correct': int(np.sum(lp[mask] == ly[mask])),
                         'labeled_precision': float(np.mean(lp[mask] == ly[mask])) if n else None,
                         'unlabeled_accepted': int(np.count_nonzero(uc >= threshold))})
        result['models'][name] = {'checkpoint_sha256': pilot['models'][name]['checkpoint_sha256'],
                                  'labeled_confidence_quantiles': {str(q): float(np.quantile(lc, q)) for q in (0.5, 0.9, 0.99, 1.0)},
                                  'unlabeled_confidence_quantiles': {str(q): float(np.quantile(uc, q)) for q in (0.5, 0.9, 0.99, 1.0)},
                                  'thresholds': rows}
    args.summary_path.parent.mkdir(parents=True, exist_ok=True)
    args.summary_path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
