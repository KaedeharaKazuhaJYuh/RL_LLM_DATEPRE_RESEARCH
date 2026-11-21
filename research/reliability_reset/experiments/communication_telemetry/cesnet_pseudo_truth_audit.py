"""Reconstruct and seal previous pseudo candidates, then score with held-out dataset labels."""
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
    parser.add_argument('--pilot-dir', required=True, type=Path)
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--run-summary', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--summary-path', required=True, type=Path)
    parser.add_argument('--seed-offset', required=True, type=int)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise ValueError('audit output already exists')
    digest = hashlib.sha256()
    with args.archive.open('rb') as f:
        while block := f.read(8 * 1024 * 1024):
            digest.update(block)
    if digest.hexdigest() != EXPECTED:
        raise ValueError('archive hash mismatch')
    run = json.loads(args.run_summary.read_text(encoding='utf-8'))
    if run['dataset_sha256'] != EXPECTED or run['label_seed_offset'] != args.seed_offset or run['pseudo_threshold'] != .05:
        raise ValueError('run metadata mismatch')
    source = run['models']['snn_lif_surrogate']
    arm = source['arms']['matched_pseudo']
    manifest = HERE / 'CESNET_TLS_YEAR22_XS_SPLIT_MANIFEST_2026_11_10.csv'
    if hashlib.sha256(manifest.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != '9eb553e31354665e5d15b5b4b0f4f1f13bac0b252562c9350f772d0e0aa4f33d':
        raise ValueError('manifest mismatch')
    with manifest.open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    args.output_dir.mkdir(parents=True)
    result = {'dataset_sha256': EXPECTED, 'label_seed_offset': args.seed_offset,
              'scope': 'offline reconstruction; dataset labels revealed only after predictions sealed', 'weeks': {}}
    for week in (15, 16, 17):
        dates = [r['date'] for r in rows if r['iso_year'] == '2022' and int(r['iso_week']) == week]
        with tables.open_file(args.archive) as archive:
            population = sum(archive.get_node('/flows/D' + d.replace('-', '')).nrows for d in dates)
        labeled = np.sort(np.random.default_rng(20261114 + week + args.seed_offset).choice(population, 1000, replace=False))
        pool = np.setdiff1d(np.arange(population), labeled, assume_unique=True)
        candidates = np.sort(np.random.default_rng(20261300 + week).choice(pool, 1000, replace=False))
        x, mask, _, refs = select_positions(args.archive, dates, candidates, labels=False)
        record = arm['weeks'][str(week)]
        candidate_hash = hashlib.sha256('\n'.join(f'{d}:{i}' for d,i in refs).encode()).hexdigest()
        if candidate_hash != record['unlabeled_row_ids_sha256']:
            raise ValueError('candidate row mismatch')
        checkpoint = (args.pilot_dir / 'snn_lif_surrogate.pt' if week == 15 else
                      args.run_dir / f'snn_lif_surrogate_matched_pseudo_after_w{week-1}.pt')
        expected = source['initial_checkpoint_sha256'] if week == 15 else arm['weeks'][str(week-1)]['checkpoint_sha256']
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
            confidence, idx = model(xx, mm).softmax(1).max(1)
            conf, pred = confidence.cpu().numpy(), classes[idx.cpu().numpy()]
        selected = conf >= .05
        hist = {str(int(c)): int(np.sum(pred[selected] == c)) for c in np.unique(pred[selected])}
        if int(selected.sum()) != record['pseudo_accepted'] or hist != record['pseudo_by_predicted_class']:
            raise ValueError('reconstructed acceptance distribution mismatch')
        sealed_path = args.output_dir / f'candidate_w{week}.npz'
        with sealed_path.open('xb') as f:
            np.savez_compressed(f, date=np.asarray([r[0] for r in refs]), row=np.asarray([r[1] for r in refs]),
                                prediction=pred, confidence=conf, accepted=selected)
        sealed_hash = hashlib.sha256(sealed_path.read_bytes()).hexdigest()
        _, _, truth, truth_refs = select_positions(args.archive, dates, candidates, labels=True)
        if truth_refs != refs:
            raise ValueError('evaluation rows mismatch')
        classes_stats = {}
        for c in np.unique(pred[selected]):
            subset = selected & (pred == c)
            classes_stats[str(int(c))] = {'accepted': int(subset.sum()), 'correct': int((truth[subset] == c).sum())}
        result['weeks'][str(week)] = {'candidate_rows_sha256': candidate_hash, 'checkpoint_sha256': expected,
            'sealed_candidate_sha256': sealed_hash, 'candidate_count': len(pred), 'accepted_count': int(selected.sum()),
            'accepted_correct': int((pred[selected] == truth[selected]).sum()),
            'accepted_truth_classes': int(len(np.unique(truth[selected]))),
            'accepted_predicted_classes': len(hist), 'by_predicted_class': classes_stats}
    args.summary_path.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
