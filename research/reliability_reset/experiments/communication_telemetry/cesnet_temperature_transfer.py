"""Apply W15-fitted temperatures to frozen checkpoints on later development weeks."""
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
    parser.add_argument('--pilot-dir', type=Path, required=True)
    parser.add_argument('--pilot-summary', type=Path, required=True)
    parser.add_argument('--static-dir', type=Path, required=True)
    parser.add_argument('--static-summary', type=Path, required=True)
    parser.add_argument('--temperature-summary', type=Path, required=True)
    parser.add_argument('--replay-summary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    digest = hashlib.sha256()
    with args.archive.open('rb') as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    if digest.hexdigest() != EXPECTED:
        raise ValueError('archive checksum mismatch')
    pilot = json.loads(args.pilot_summary.read_text(encoding='utf-8'))
    static = json.loads(args.static_summary.read_text(encoding='utf-8'))
    temperatures = json.loads(args.temperature_summary.read_text(encoding='utf-8'))
    replay = json.loads(args.replay_summary.read_text(encoding='utf-8'))
    if any(d['dataset_sha256'] != EXPECTED for d in (pilot, static, temperatures, replay)):
        raise ValueError('input dataset provenance mismatch')
    manifest = HERE / 'CESNET_TLS_YEAR22_XS_SPLIT_MANIFEST_2026_11_10.csv'
    if hashlib.sha256(manifest.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != '9eb553e31354665e5d15b5b4b0f4f1f13bac0b252562c9350f772d0e0aa4f33d':
        raise ValueError('split manifest checksum mismatch')
    with manifest.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    weeks = {w: [r['date'] for r in rows if r['iso_year'] == '2022' and int(r['iso_week']) == w] for w in (16, 17, 18)}
    with tables.open_file(args.archive) as archive:
        populations = {w: sum(archive.get_node('/flows/D' + d.replace('-', '')).nrows for d in dates) for w, dates in weeks.items()}
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    result = {'dataset_sha256': EXPECTED, 'scope': 'frozen W15 temperatures transferred without updates; development weeks only',
              'temperature_summary_sha256': hashlib.sha256(args.temperature_summary.read_bytes()).hexdigest(),
              'static_summary_sha256': hashlib.sha256(args.static_summary.read_bytes()).hexdigest(), 'models': {}}
    for name, constructor in [('ann_gru', Ann), ('snn_lif_surrogate', Snn)]:
        checkpoint = args.pilot_dir / f'{name}.pt'
        checkpoint_hash = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        if checkpoint_hash != pilot['models'][name]['checkpoint_sha256'] or checkpoint_hash != temperatures['models'][name]['checkpoint_sha256']:
            raise ValueError('checkpoint mismatch')
        saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
        classes = np.asarray(saved['classes'], dtype=np.int32)
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
        per_week = {}
        for week, dates in weeks.items():
            sealed_path = args.static_dir / f'{name}_w{week}_predictions.npz'
            sealed_hash = hashlib.sha256(sealed_path.read_bytes()).hexdigest()
            expected = static['models'][name]['weeks'][str(week)]['score']['prediction_sha256']
            if sealed_hash != expected:
                raise ValueError('sealed prediction checksum mismatch')
            labeled = np.sort(np.random.default_rng(20261114 + week).choice(populations[week], 1000, replace=False))
            pool = np.setdiff1d(np.arange(populations[week]), labeled, assume_unique=True)
            unlabeled = np.sort(np.random.default_rng(20261300 + week).choice(pool, 1000, replace=False))
            with np.load(sealed_path) as sealed:
                sealed_dates, sealed_rows = sealed['date'][labeled], sealed['row'][labeled]
                sealed_refs = [(str(day), int(row)) for day, row in zip(sealed_dates, sealed_rows)]
                sealed_predictions = sealed['prediction'][labeled].copy()
            lx, lm, ly, lrefs = select_positions(args.archive, dates, labeled, labels=True)
            ux, um, _, urefs = select_positions(args.archive, dates, unlabeled, labels=False)
            if lrefs != sealed_refs or set(lrefs) & set(urefs):
                raise ValueError('sample identity mismatch')
            lhash = hashlib.sha256('\n'.join(f'{d}:{i}' for d, i in lrefs).encode()).hexdigest()
            uhash = hashlib.sha256('\n'.join(f'{d}:{i}' for d, i in urefs).encode()).hexdigest()
            prior = replay['models'][name]['arms']['supervised']['weeks'][str(week)]
            if lhash != prior['released_row_ids_sha256'] or (week < 18 and uhash != prior['unlabeled_row_ids_sha256']):
                raise ValueError('sample differs from replay pilot')
            if not np.isin(ly, classes).all():
                raise ValueError('sample label outside vocabulary')
            ll, ul = infer(lx, lm), infer(ux, um)
            if not np.array_equal(classes[ll.argmax(dim=1).cpu().numpy()], sealed_predictions):
                raise ValueError('recomputed sampled predictions differ from pre-sealed predictions')
            targets = torch.tensor(np.searchsorted(classes, ly), device='cuda', dtype=torch.long)
            values = []
            for t in (1.0, float(temperatures['models'][name]['selected_temperature'])):
                probs = torch.softmax(ll / t, dim=1)
                lc, pred = probs.max(dim=1)
                uc = torch.softmax(ul / t, dim=1).max(dim=1).values.cpu().numpy()
                lc, pred = lc.cpu().numpy(), pred.cpu().numpy()
                assessment = {'temperature': t, 'labeled_nll': float(F.cross_entropy(ll / t, targets).cpu()), 'thresholds': []}
                for threshold in (0.5, 0.8):
                    mask = lc >= threshold
                    assessment['thresholds'].append({'threshold': threshold, 'labeled_accepted': int(mask.sum()),
                                                     'labeled_correct': int(np.sum(classes[pred[mask]] == ly[mask])),
                                                     'unlabeled_accepted': int(np.count_nonzero(uc >= threshold))})
                values.append(assessment)
            per_week[str(week)] = {'sealed_prediction_sha256': sealed_hash, 'labeled_row_ids_sha256': lhash,
                                   'unlabeled_row_ids_sha256': uhash, 'assessments': values}
        result['models'][name] = {'checkpoint_sha256': checkpoint_hash, 'weeks': per_week}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
