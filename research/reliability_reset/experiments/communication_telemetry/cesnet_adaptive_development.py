"""Development-only supervised weekly updates after sealed predictions and scoring."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

from .cesnet_input import iter_batches
from .cesnet_prequential import run_week
from .smoke_cesnet_cuda_models import Ann, Snn, EXPECTED, HERE


def selected_examples(archive_path, dates, released, batch_size=4096):
    """Collect only feature rows whose labels were released by the evaluator."""
    labels = {(day, row): label for day, row, label in released}
    if len(labels) != len(released):
        raise ValueError('repeated released row')
    events, masks, targets, found = [], [], [], set()
    for batch in iter_batches(archive_path, dates, batch_size):
        if batch.labels is not None:
            raise RuntimeError('features reader unexpectedly returned labels')
        positions = [i for i, row in enumerate(batch.row_indices) if (batch.dates[i], int(row)) in labels]
        if positions:
            events.append(batch.events[positions])
            masks.append(batch.mask[positions])
            keys = [(batch.dates[i], int(batch.row_indices[i])) for i in positions]
            targets.extend(labels[key] for key in keys)
            found.update(keys)
    if found != set(labels):
        raise ValueError('released rows do not match selected dates')
    return np.concatenate(events), np.concatenate(masks), np.asarray(targets, dtype=np.int32)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--pilot-dir', required=True, type=Path)
    parser.add_argument('--pilot-summary', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--summary-path', required=True, type=Path)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise ValueError('output directory must not already exist')
    digest = hashlib.sha256()
    with args.archive.open('rb') as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    if digest.hexdigest() != EXPECTED:
        raise ValueError('archive checksum mismatch')
    pilot = json.loads(args.pilot_summary.read_text(encoding='utf-8'))
    if pilot['dataset_sha256'] != EXPECTED or pilot['profile'] != 'balanced':
        raise ValueError('unexpected checkpoint provenance')
    manifest = HERE / 'CESNET_TLS_YEAR22_XS_SPLIT_MANIFEST_2026_11_10.csv'
    if hashlib.sha256(manifest.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != '9eb553e31354665e5d15b5b4b0f4f1f13bac0b252562c9350f772d0e0aa4f33d':
        raise ValueError('split manifest checksum mismatch')
    with manifest.open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    weeks = {w: [r['date'] for r in rows if r['iso_year'] == '2022' and int(r['iso_week']) == w] for w in range(15, 19)}
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    args.output_dir.mkdir(parents=True)
    results = {'dataset_sha256': EXPECTED, 'scope': 'development only, sequential supervised fine-tuning; no SSL or replay',
               'initial_checkpoint_profile': 'balanced tuned using W15', 'update_budget': 1000,
               'update_epochs': 5, 'update_batch_size': 128, 'update_optimizer': 'Adam lr=0.001',
               'torch_version': torch.__version__, 'gpu': torch.cuda.get_device_name(0), 'models': {}}
    for name, constructor in [('ann_gru', Ann), ('snn_lif_surrogate', Snn)]:
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
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        def transform(values, mask):
            return ((torch.sign(values) * torch.log1p(torch.abs(values)) - means) / scales) * mask.unsqueeze(-1)
        def predict(batch):
            with torch.inference_mode():
                x = torch.as_tensor(batch.events, device='cuda', dtype=torch.float32)
                mask = torch.as_tensor(batch.mask, device='cuda')
                return classes[model(transform(x, mask), mask).argmax(dim=1).cpu().numpy()]
        per_week = {}
        for week, dates in weeks.items():
            model.eval()
            prediction_path = args.output_dir / f'{name}_w{week}_predictions.npz'
            score, released = run_week(args.archive, dates, predict, classes, 1000, 20261114 + week,
                                       prediction_path, batch_size=2048)
            refs = '\n'.join(f'{day}:{row}' for day, row, _ in released)
            record = {'score_before_update': score, 'released_label_count': len(released),
                      'released_row_ids_sha256': hashlib.sha256(refs.encode()).hexdigest(),
                      'released_distinct_classes': len({label for _, _, label in released})}
            if week < 18:
                events, masks, labels = selected_examples(args.archive, dates, released)
                if not np.isin(labels, classes).all():
                    raise ValueError('released label outside fixed vocabulary')
                x_cpu = torch.as_tensor(events, dtype=torch.float32)
                mask_cpu = torch.as_tensor(masks)
                y_cpu = torch.as_tensor(np.searchsorted(classes, labels), dtype=torch.long)
                counts = np.bincount(np.searchsorted(classes, labels), minlength=len(classes))
                weights = np.zeros(len(classes), dtype=np.float32)
                seen = counts > 0
                weights[seen] = 1.0 / np.sqrt(counts[seen])
                weights[seen] /= weights[seen].mean()
                class_weights = torch.as_tensor(weights, device='cuda')
                rng = np.random.default_rng(20261200 + week)
                model.train()
                start_time = time.perf_counter()
                for _ in range(5):
                    order = rng.permutation(len(labels))
                    for start in range(0, len(order), 128):
                        idx = order[start:start + 128]
                        mask = mask_cpu[idx].cuda()
                        x = transform(x_cpu[idx].cuda(), mask)
                        y = y_cpu[idx].cuda()
                        optimizer.zero_grad(set_to_none=True)
                        loss = nn.functional.cross_entropy(model(x, mask), y, weight=class_weights)
                        if not torch.isfinite(loss):
                            raise RuntimeError('non-finite loss')
                        loss.backward()
                        optimizer.step()
                torch.cuda.synchronize()
                record['update_steps'] = 5 * ((len(labels) + 127) // 128)
                record['update_seconds'] = time.perf_counter() - start_time
                next_checkpoint = args.output_dir / f'{name}_after_w{week}.pt'
                torch.save({'model': model.state_dict(), 'optimizer': optimizer.state_dict(),
                            'classes': classes.tolist(), 'event_mean': saved['event_mean'],
                            'event_scale': saved['event_scale'], 'after_week': week}, next_checkpoint)
                record['checkpoint_sha256'] = hashlib.sha256(next_checkpoint.read_bytes()).hexdigest()
            per_week[str(week)] = record
        results['models'][name] = {'initial_checkpoint_sha256': expected, 'weeks': per_week}
    for week in weeks:
        if results['models']['ann_gru']['weeks'][str(week)]['released_row_ids_sha256'] != results['models']['snn_lif_surrogate']['weeks'][str(week)]['released_row_ids_sha256']:
            raise RuntimeError('models did not receive the same sampled rows')
    args.summary_path.parent.mkdir(parents=True, exist_ok=True)
    args.summary_path.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
