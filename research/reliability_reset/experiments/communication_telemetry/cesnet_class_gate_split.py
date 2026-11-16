"""Diagnose class-gate support using disjoint released rows and sealed replay predictions."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import tables
import torch

from .cesnet_replay_ssl_pilot import select_positions
from .smoke_cesnet_cuda_models import EXPECTED, HERE, Snn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--pilot-dir', type=Path, required=True)
    parser.add_argument('--baseline-dir', type=Path, required=True)
    parser.add_argument('--baseline-summary', type=Path, required=True)
    parser.add_argument('--seed-offset', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    digest = hashlib.sha256()
    with args.archive.open('rb') as f:
        while block := f.read(8 * 1024 * 1024):
            digest.update(block)
    if digest.hexdigest() != EXPECTED:
        raise ValueError('archive hash mismatch')
    summary = json.loads(args.baseline_summary.read_text(encoding='utf-8'))
    baseline = summary['models']['snn_lif_surrogate']['arms']['replay']
    manifest = HERE / 'CESNET_TLS_YEAR22_XS_SPLIT_MANIFEST_2026_11_10.csv'
    if hashlib.sha256(manifest.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != '9eb553e31354665e5d15b5b4b0f4f1f13bac0b252562c9350f772d0e0aa4f33d':
        raise ValueError('manifest mismatch')
    with manifest.open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    result = {'dataset_sha256': EXPECTED, 'label_seed_offset': args.seed_offset,
              'scope': 'development-only disjoint row split; no model update', 'weeks': {}}
    for week in (15, 16, 17):
        dates = [r['date'] for r in rows if r['iso_year'] == '2022' and int(r['iso_week']) == week]
        with tables.open_file(args.archive) as archive:
            population = sum(archive.get_node('/flows/D' + d.replace('-', '')).nrows for d in dates)
        positions = np.sort(np.random.default_rng(20261114 + week + args.seed_offset).choice(population, 1000, replace=False))
        x, mask, labels, refs = select_positions(args.archive, dates, positions, labels=True)
        rowhash = hashlib.sha256('\n'.join(f'{d}:{i}' for d, i in refs).encode()).hexdigest()
        if rowhash != baseline['weeks'][str(week)]['released_row_ids_sha256']:
            raise ValueError('label sample mismatch')
        if week == 15:
            checkpoint = args.pilot_dir / 'snn_lif_surrogate.pt'
            expected = summary['models']['snn_lif_surrogate']['initial_checkpoint_sha256']
        else:
            checkpoint = args.baseline_dir / f'snn_lif_surrogate_replay_after_w{week-1}.pt'
            expected = baseline['weeks'][str(week-1)]['checkpoint_sha256']
        if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != expected:
            raise ValueError('checkpoint mismatch')
        saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
        classes = np.asarray(saved['classes'], dtype=np.int32)
        model = Snn(len(classes)).cuda().eval()
        model.load_state_dict(saved['model'])
        with torch.inference_mode():
            xx = torch.tensor(x, device='cuda', dtype=torch.float32)
            mm = torch.tensor(mask, device='cuda')
            mean = torch.tensor(saved['event_mean'], device='cuda', dtype=torch.float32)
            scale = torch.tensor(saved['event_scale'], device='cuda', dtype=torch.float32)
            xx = ((torch.sign(xx)*torch.log1p(torch.abs(xx))-mean)/scale)*mm.unsqueeze(-1)
            conf, idx = model(xx, mm).softmax(1).max(1)
            conf = conf.cpu().numpy()
            pred = classes[idx.cpu().numpy()]
        prediction_path = args.baseline_dir / f'snn_lif_surrogate_replay_w{week}.npz'
        if hashlib.sha256(prediction_path.read_bytes()).hexdigest() != baseline['weeks'][str(week)]['score_before_update']['prediction_sha256']:
            raise ValueError('sealed prediction checksum mismatch')
        with np.load(prediction_path) as sealed:
            sealed_dates, sealed_rows, sealed_predictions = sealed['date'], sealed['row'], sealed['prediction']
        lookup = {(str(d), int(i)): int(y) for d, i, y in zip(sealed_dates, sealed_rows, sealed_predictions)}
        if any(lookup[ref] != int(y) for ref, y in zip(refs, pred)):
            raise ValueError('sample predictions differ from sealed predictions')
        perm = np.random.default_rng(20261190 + week).permutation(1000)
        selection, holdout = perm[:500], perm[500:]
        fit_codes = np.unique(pred[selection][conf[selection] >= .05])
        details = []
        for code in fit_codes:
            selected = selection[(pred[selection] == code) & (conf[selection] >= .05)]
            held = holdout[(pred[holdout] == code) & (conf[holdout] >= .05)]
            n, correct = len(selected), int((labels[selected] == code).sum())
            z = 1.959963984540054
            phat = correct / n
            mid = phat + z*z/(2*n)
            delta = z*np.sqrt(phat*(1-phat)/n + z*z/(4*n*n))
            low, high = (mid-delta)/(1+z*z/n), (mid+delta)/(1+z*z/n)
            details.append({'class': int(code), 'selection_count': n, 'selection_correct': correct,
                            'wilson_lower': float(low), 'wilson_upper': float(high),
                            'decision': 'support_below_10' if n < 10 else 'lower_below_0.5' if low < .5 else 'pass',
                            'holdout_count': len(held), 'holdout_correct': int((labels[held] == code).sum())})
        bins = []
        for lower, upper in ((0.05, 0.06), (0.06, 0.08), (0.08, 1.01)):
            chosen = selection[(conf[selection] >= lower) & (conf[selection] < upper)]
            held = holdout[(conf[holdout] >= lower) & (conf[holdout] < upper)]
            n, correct = len(chosen), int((labels[chosen] == pred[chosen]).sum())
            if n:
                phat, z = correct/n, 1.959963984540054
                bound = (phat + z*z/(2*n) - z*np.sqrt(phat*(1-phat)/n + z*z/(4*n*n))) / (1+z*z/n)
            else:
                bound = None
            bins.append({'range': [lower, upper], 'selection_count': n, 'selection_correct': correct,
                         'selection_classes': int(len(np.unique(pred[chosen]))), 'wilson_lower': float(bound) if n else None,
                         'passes': bool(n >= 10 and bound >= .5), 'holdout_count': len(held),
                         'holdout_correct': int((labels[held] == pred[held]).sum()),
                         'holdout_classes': int(len(np.unique(pred[held])))})
        result['weeks'][str(week)] = {'row_ids_sha256': rowhash, 'checkpoint_sha256': expected,
             'selection_positions_sha256': hashlib.sha256(selection.astype('<i8').tobytes()).hexdigest(),
             'selection_rows': len(selection), 'holdout_rows': len(holdout), 'classes': details, 'confidence_bins': bins}
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
