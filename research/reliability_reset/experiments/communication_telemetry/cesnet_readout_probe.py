"""Fit frozen-encoder readouts on W15 released labels; evaluate disjoint rows."""
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
    with args.archive.open('rb') as f:
        while block := f.read(8 * 1024 * 1024):
            digest.update(block)
    if digest.hexdigest() != EXPECTED:
        raise ValueError('archive checksum mismatch')
    pilot = json.loads(args.pilot_summary.read_text(encoding='utf-8'))
    confidence = json.loads(args.confidence_summary.read_text(encoding='utf-8'))
    manifest = HERE / 'CESNET_TLS_YEAR22_XS_SPLIT_MANIFEST_2026_11_10.csv'
    if hashlib.sha256(manifest.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != '9eb553e31354665e5d15b5b4b0f4f1f13bac0b252562c9350f772d0e0aa4f33d':
        raise ValueError('manifest checksum mismatch')
    with manifest.open(encoding='utf-8', newline='') as f:
        dates = [r['date'] for r in csv.DictReader(f) if r['iso_year'] == '2022' and r['iso_week'] == '15']
    with tables.open_file(args.archive) as archive:
        population = sum(archive.get_node('/flows/D' + d.replace('-', '')).nrows for d in dates)
    positions = np.sort(np.random.default_rng(20261129).choice(population, 1000, replace=False))
    x, mask, labels, refs = select_positions(args.archive, dates, positions, labels=True)
    rowhash = hashlib.sha256('\n'.join(f'{d}:{i}' for d, i in refs).encode()).hexdigest()
    if pilot['dataset_sha256'] != EXPECTED or pilot['profile'] != 'balanced' or confidence['labeled_row_ids_sha256'] != rowhash:
        raise ValueError('pilot or sampling provenance mismatch')
    split = np.random.default_rng(20261130).permutation(1000)
    fit, valid = split[:500], split[500:]
    result = {'scope': 'W15 development-only frozen-encoder readout probe', 'dataset_sha256': EXPECTED,
              'row_ids_sha256': rowhash, 'split_seed': 20261130,
              'fit_positions_sha256': hashlib.sha256(fit.astype('<i8').tobytes()).hexdigest(),
              'fit_count': len(fit), 'validation_count': len(valid),
              'fit_unique_classes': int(len(np.unique(labels[fit]))),
              'validation_unique_classes': int(len(np.unique(labels[valid]))),
              'validation_labels_absent_from_fit': int((~np.isin(labels[valid], labels[fit])).sum()),
              'optimizer': 'Adam lr=0.01, 100 full-batch steps, unweighted cross-entropy', 'models': {}}
    for name, constructor in [('ann_gru', Ann), ('snn_lif_surrogate', Snn)]:
        checkpoint = args.pilot_dir / f'{name}.pt'
        checkpoint_hash = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        if checkpoint_hash != pilot['models'][name]['checkpoint_sha256']:
            raise ValueError('checkpoint checksum mismatch')
        saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
        classes = np.asarray(saved['classes'], dtype=np.int32)
        if not np.isin(labels, classes).all():
            raise ValueError('label outside frozen vocabulary')
        target = torch.tensor(np.searchsorted(classes, labels), device='cuda', dtype=torch.long)
        model = constructor(len(classes)).cuda().eval()
        model.load_state_dict(saved['model'])
        captured = []
        handle = model.head.register_forward_pre_hook(lambda module, inputs: captured.append(inputs[0].detach()))
        with torch.inference_mode():
            xx = torch.tensor(x, device='cuda', dtype=torch.float32)
            mm = torch.tensor(mask, device='cuda')
            mean = torch.tensor(saved['event_mean'], device='cuda', dtype=torch.float32)
            scale = torch.tensor(saved['event_scale'], device='cuda', dtype=torch.float32)
            xx = ((torch.sign(xx) * torch.log1p(torch.abs(xx)) - mean) / scale) * mm.unsqueeze(-1)
            logits = model(xx, mm)
        handle.remove()
        features = captured[0].clone()
        replay = model.head(features)
        max_diff = (logits - replay).abs().max().item()
        if max_diff > 1e-6:
            raise ValueError('readout replay mismatch')
        arms = {}
        for arm in ('original', 'bias', 'full'):
            head = torch.nn.Linear(32, len(classes), device='cuda')
            head.load_state_dict(model.head.state_dict())
            if arm != 'original':
                head.weight.requires_grad_(arm == 'full')
                optimizer = torch.optim.Adam([p for p in head.parameters() if p.requires_grad], lr=.01)
                for _ in range(100):
                    optimizer.zero_grad()
                    loss = F.cross_entropy(head(features[fit]), target[fit])
                    loss.backward()
                    optimizer.step()
            with torch.no_grad():
                fit_logits, val_logits = head(features[fit]), head(features[valid])
                probs = val_logits.softmax(1)
                pred = probs.argmax(1).cpu().numpy()
                truth = target[valid].cpu().numpy()
                tp = np.bincount(truth[pred == truth], minlength=len(classes))
                predn = np.bincount(pred, minlength=len(classes))
                truen = np.bincount(truth, minlength=len(classes))
                f1 = np.divide(2 * tp, predn + truen, out=np.zeros(len(classes)), where=(predn + truen) != 0)
                arms[arm] = {'fit_nll': float(F.cross_entropy(fit_logits, target[fit]).cpu()),
                             'validation_nll': float(F.cross_entropy(val_logits, target[valid]).cpu()),
                             'validation_accuracy': float(np.mean(pred == truth)),
                             'validation_macro_f1_180': float(f1.mean()),
                             'validation_predicted_classes': int(len(np.unique(pred))),
                             'validation_mean_confidence': float(probs.max(1).values.mean().cpu()),
                             'weight_sha256': hashlib.sha256(head.weight.detach().cpu().numpy().tobytes() + head.bias.detach().cpu().numpy().tobytes()).hexdigest()}
        centered = features - features.mean(0)
        singular = torch.linalg.svdvals(centered).cpu().numpy()
        result['models'][name] = {'checkpoint_sha256': checkpoint_hash, 'max_logit_replay_difference': max_diff,
                                  'representation_singular_values': singular.tolist(), 'arms': arms}
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
