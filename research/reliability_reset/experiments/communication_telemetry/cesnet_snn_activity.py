"""Replay the frozen SNN on released W15 labels and summarize spike activity."""
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
    parser.add_argument('--pilot-summary', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    digest = hashlib.sha256()
    with args.archive.open('rb') as f:
        while block := f.read(8 * 1024 * 1024):
            digest.update(block)
    if digest.hexdigest() != EXPECTED:
        raise ValueError('archive checksum mismatch')
    pilot = json.loads(args.pilot_summary.read_text(encoding='utf-8'))
    checkpoint = args.pilot_dir / 'snn_lif_surrogate.pt'
    checkpoint_hash = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    if pilot['dataset_sha256'] != EXPECTED or pilot['profile'] != 'balanced' or checkpoint_hash != pilot['models']['snn_lif_surrogate']['checkpoint_sha256']:
        raise ValueError('checkpoint provenance mismatch')
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
    saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
    classes = np.asarray(saved['classes'], dtype=np.int32)
    model = Snn(len(classes)).cuda().eval()
    model.load_state_dict(saved['model'])
    with torch.inference_mode():
        x = torch.tensor(x, device='cuda', dtype=torch.float32)
        mask = torch.tensor(mask, device='cuda')
        means = torch.tensor(saved['event_mean'], device='cuda', dtype=torch.float32)
        scales = torch.tensor(saved['event_scale'], device='cuda', dtype=torch.float32)
        x = ((torch.sign(x) * torch.log1p(torch.abs(x)) - means) / scales) * mask.unsqueeze(-1)
        expected_logits = model(x, mask)
        membrane = x.new_zeros((len(x), 32))
        counts = torch.zeros_like(membrane)
        for t in range(x.shape[1]):
            active = mask[:, t:t + 1]
            candidate = 0.9 * membrane + model.input(x[:, t])
            hard = (candidate >= 1.0).to(x.dtype)
            counts += hard * active
            membrane = torch.where(active, candidate * (1.0 - hard), membrane)
        replay_logits = model.head(counts / mask.sum(1, keepdim=True).clamp_min(1))
        difference = (expected_logits - replay_logits).abs().max().item()
        if difference > 1e-6:
            raise RuntimeError(f'model replay differs: {difference}')
        probs = expected_logits.softmax(1)
        confidence, index = probs.max(1)
        correct = classes[index.cpu().numpy()] == labels
        flow_spikes = counts.sum(1).cpu().numpy()
        valid_steps = mask.sum(1).cpu().numpy()
        rates = (counts / mask.sum(1, keepdim=True).clamp_min(1)).mean(0).cpu().numpy()
        confidence = confidence.cpu().numpy()
        predicted = index.cpu().numpy()
        silent_prediction = int(model.head.bias.argmax().item())
    groups = {}
    for name, selected in [('silent', flow_spikes == 0), ('one_to_31', (flow_spikes > 0) & (flow_spikes < 32)), ('32_or_more', flow_spikes >= 32)]:
        n = int(selected.sum())
        groups[name] = {'count': n, 'correct': int(correct[selected].sum()), 'mean_confidence': float(confidence[selected].mean()) if n else None}
    result = {'scope': 'W15 development diagnostic; frozen model, released labels, no update', 'dataset_sha256': EXPECTED,
              'checkpoint_sha256': checkpoint_hash, 'row_ids_sha256': rowhash, 'rows': len(labels),
              'max_logit_replay_difference': difference, 'valid_packet_steps': int(valid_steps.sum()),
              'total_spikes': int(flow_spikes.sum()), 'spikes_per_valid_unit_step': float(flow_spikes.sum() / (32 * valid_steps.sum())),
              'flow_spike_quantiles': {str(q): float(np.quantile(flow_spikes, q)) for q in (0, .5, .9, .99, 1)},
              'per_unit_mean_rate': rates.tolist(), 'never_spiking_units': int((rates == 0).sum()),
              'groups': groups, 'predicted_class_count': int(len(np.unique(predicted))),
              'bias_prediction_count': int((predicted == silent_prediction).sum()),
              'correct_count': int(correct.sum())}
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
