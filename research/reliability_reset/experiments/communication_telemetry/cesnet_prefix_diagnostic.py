"""Compare frozen SNN predictions on original PPI and an actual shorter prefix."""
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


def shorten_prefix(events, mask):
    lengths = mask.sum(axis=1)
    shortened = np.maximum(lengths - 1, 1)
    prefix_mask = mask & (np.arange(mask.shape[1])[None, :] < shortened[:, None])
    prefix = events.copy()
    prefix[~prefix_mask] = 0
    return prefix, prefix_mask


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--pilot-dir', type=Path, required=True)
    parser.add_argument('--pilot-summary', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--summary-path', type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise ValueError('output directory already exists')
    digest = hashlib.sha256()
    with args.archive.open('rb') as f:
        while block := f.read(8 * 1024 * 1024):
            digest.update(block)
    if digest.hexdigest() != EXPECTED:
        raise ValueError('archive checksum mismatch')
    pilot = json.loads(args.pilot_summary.read_text(encoding='utf-8'))
    checkpoint = args.pilot_dir / 'snn_lif_surrogate.pt'
    ckhash = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    if pilot['dataset_sha256'] != EXPECTED or ckhash != pilot['models']['snn_lif_surrogate']['checkpoint_sha256']:
        raise ValueError('checkpoint provenance mismatch')
    manifest = HERE / 'CESNET_TLS_YEAR22_XS_SPLIT_MANIFEST_2026_11_10.csv'
    if hashlib.sha256(manifest.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != '9eb553e31354665e5d15b5b4b0f4f1f13bac0b252562c9350f772d0e0aa4f33d':
        raise ValueError('manifest checksum mismatch')
    with manifest.open(encoding='utf-8', newline='') as f:
        dates = [r['date'] for r in csv.DictReader(f) if r['iso_year'] == '2022' and r['iso_week'] == '15']
    with tables.open_file(args.archive) as archive:
        population = sum(archive.get_node('/flows/D' + d.replace('-', '')).nrows for d in dates)
    saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
    classes = np.asarray(saved['classes'], dtype=np.int32)
    model = Snn(len(classes)).cuda().eval()
    model.load_state_dict(saved['model'])
    mean = torch.tensor(saved['event_mean'], device='cuda', dtype=torch.float32)
    scale = torch.tensor(saved['event_scale'], device='cuda', dtype=torch.float32)
    args.output_dir.mkdir(parents=True)
    result = {'dataset_sha256': EXPECTED, 'checkpoint_sha256': ckhash,
              'scope': 'W15 development; no model update; same flow labels under reduced observations', 'seeds': {}}
    for offset in (0, 10000):
        positions = np.sort(np.random.default_rng(20261129 + offset).choice(population, 1000, replace=False))
        x, mask, _, refs = select_positions(args.archive, dates, positions, labels=False)
        shortened, prefix_mask = shorten_prefix(x, mask)
        if not np.array_equal(shortened[prefix_mask], x[prefix_mask]) or np.any(prefix_mask & ~mask):
            raise ValueError('prefix preservation failed')
        predictions = []
        with torch.inference_mode():
            for values, valid in ((x, mask), (shortened, prefix_mask)):
                xx = torch.tensor(values, device='cuda', dtype=torch.float32)
                mm = torch.tensor(valid, device='cuda')
                xx = ((torch.sign(xx)*torch.log1p(torch.abs(xx))-mean)/scale)*mm.unsqueeze(-1)
                predictions.append(classes[model(xx, mm).argmax(1).cpu().numpy()])
        path = args.output_dir / f'prefix_seed{offset}.npz'
        with path.open('xb') as f:
            np.savez_compressed(f, date=np.asarray([r[0] for r in refs]), row=np.asarray([r[1] for r in refs]),
                                full=predictions[0], prefix=predictions[1])
        sealed_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        _, _, truth, label_refs = select_positions(args.archive, dates, positions, labels=True)
        if refs != label_refs:
            raise ValueError('evaluation row mismatch')
        full_correct = predictions[0] == truth
        prefix_correct = predictions[1] == truth
        altered = (mask.sum(1) > 1)
        result['seeds'][str(offset)] = {'rows': len(refs), 'row_ids_sha256': hashlib.sha256('\n'.join(f'{d}:{i}' for d,i in refs).encode()).hexdigest(),
            'prediction_sha256': sealed_hash, 'shortened_rows': int(altered.sum()),
            'prediction_changes': int(np.sum(predictions[0] != predictions[1])),
            'full_correct': int(full_correct.sum()), 'prefix_correct': int(prefix_correct.sum()),
            'correct_to_wrong': int(np.sum(full_correct & ~prefix_correct)),
            'wrong_to_correct': int(np.sum(~full_correct & prefix_correct))}
    args.summary_path.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
