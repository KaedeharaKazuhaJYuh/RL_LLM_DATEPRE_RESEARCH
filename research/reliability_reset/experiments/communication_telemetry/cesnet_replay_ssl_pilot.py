"""Development-only replay and pseudo-label controls with fixed update batches."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import tables
import torch
from torch import nn

from .cesnet_adaptive_development import selected_examples
from .cesnet_input import iter_batches
from .cesnet_prequential import run_week
from .smoke_cesnet_cuda_models import Ann, Snn, EXPECTED, HERE


def select_positions(archive, dates, positions, *, labels):
    """Load selected global positions, retaining labels only when explicitly requested."""
    positions = np.asarray(positions, dtype=np.int64)
    if len(np.unique(positions)) != len(positions):
        raise ValueError('duplicate selected positions')
    positions.sort()
    events, masks, targets, refs = [], [], [], []
    offset = 0
    for batch in iter_batches(archive, dates, include_labels=labels):
        local = np.flatnonzero(np.isin(np.arange(offset, offset + len(batch.row_indices)), positions))
        if local.size:
            events.append(batch.events[local])
            masks.append(batch.mask[local])
            if labels:
                targets.append(batch.labels[local])
            refs.extend((batch.dates[i], int(batch.row_indices[i])) for i in local)
        offset += len(batch.row_indices)
    if len(refs) != len(positions):
        raise ValueError('selected positions do not match population')
    return np.concatenate(events), np.concatenate(masks), np.concatenate(targets) if labels else None, refs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--pilot-dir', required=True, type=Path)
    parser.add_argument('--pilot-summary', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--summary-path', required=True, type=Path)
    parser.add_argument('--label-seed-offset', type=int, default=0)
    parser.add_argument('--pseudo-threshold', type=float, default=0.8)
    parser.add_argument('--replay-pseudo-only', action='store_true')
    parser.add_argument('--replay-only', action='store_true')
    parser.add_argument('--matched-pseudo-arms', action='store_true')
    parser.add_argument('--matched-augment-only', action='store_true')
    parser.add_argument('--replay-extra-labels-only', action='store_true')
    parser.add_argument('--class-gated-only', action='store_true')
    parser.add_argument('--head-only', action='store_true')
    parser.add_argument('--snn-only', action='store_true')
    parser.add_argument('--no-pseudo-arms', action='store_true')
    args = parser.parse_args()
    if not 0 <= args.pseudo_threshold <= 1:
        raise ValueError('pseudo threshold must be between zero and one')
    if args.output_dir.exists():
        raise ValueError('output directory already exists')
    digest = hashlib.sha256()
    with args.archive.open('rb') as stream:
        while block := stream.read(8 * 1024 * 1024):
            digest.update(block)
    if digest.hexdigest() != EXPECTED:
        raise ValueError('archive checksum mismatch')
    pilot = json.loads(args.pilot_summary.read_text(encoding='utf-8'))
    if pilot['dataset_sha256'] != EXPECTED or pilot['profile'] != 'balanced':
        raise ValueError('unexpected pilot provenance')
    manifest = HERE / 'CESNET_TLS_YEAR22_XS_SPLIT_MANIFEST_2026_11_10.csv'
    if hashlib.sha256(manifest.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != '9eb553e31354665e5d15b5b4b0f4f1f13bac0b252562c9350f772d0e0aa4f33d':
        raise ValueError('split manifest checksum mismatch')
    with manifest.open(encoding='utf-8', newline='') as stream:
        manifest_rows = list(csv.DictReader(stream))
    weeks = {w: [r['date'] for r in manifest_rows if r['iso_year'] == '2022' and int(r['iso_week']) == w] for w in range(11, 19)}
    with tables.open_file(args.archive) as archive:
        populations = {w: sum(archive.get_node('/flows/D' + d.replace('-', '')).nrows for d in dates) for w, dates in weeks.items()}
    rng = np.random.default_rng(20261112)
    initial_positions = {w: np.sort(rng.choice(populations[w], 1000, replace=False)) for w in range(11, 15)}
    initial_parts = [select_positions(args.archive, weeks[w], initial_positions[w], labels=True) for w in range(11, 15)]
    init_x = np.concatenate([x[0] for x in initial_parts])
    init_m = np.concatenate([x[1] for x in initial_parts])
    init_y = np.concatenate([x[2] for x in initial_parts])
    init_refs = [r for part in initial_parts for r in part[3]]
    init_ref_hash = hashlib.sha256('\n'.join(f'{d}:{i}' for d, i in init_refs).encode()).hexdigest()
    if init_ref_hash != pilot['sampled_row_ids_sha256']:
        raise ValueError('initialization samples differ from pilot')
    replay_ids = np.sort(np.random.default_rng(20261116).choice(len(init_y), 1000, replace=False))
    replay_x, replay_m, replay_y = init_x[replay_ids], init_m[replay_ids], init_y[replay_ids]
    holdout_pool = np.setdiff1d(np.arange(populations[11]), initial_positions[11], assume_unique=True)
    holdout_ids = np.sort(np.random.default_rng(20261115).choice(holdout_pool, 2000, replace=False))
    old_x, old_m, old_y, old_refs = select_positions(args.archive, weeks[11], holdout_ids, labels=True)
    if set(old_refs) & set(init_refs):
        raise ValueError('initialization train/holdout overlap')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable')
    args.output_dir.mkdir(parents=True)
    results = {'dataset_sha256': EXPECTED, 'scope': 'development only; fixed-composition replay and confidence pseudo-label controls',
               'initial_samples_sha256': init_ref_hash, 'replay_rows': len(replay_y),
               'replay_array_bytes': int(replay_x.nbytes + replay_m.nbytes + replay_y.nbytes),
               'holdout_rows': len(old_y), 'holdout_row_ids_sha256': hashlib.sha256('\n'.join(f'{d}:{i}' for d, i in old_refs).encode()).hexdigest(),
               'label_budget_per_week': 1000, 'unlabeled_candidates_per_week': 1000,
               'pseudo_threshold': args.pseudo_threshold, 'steps_per_week': 40, 'batch_size': 192 if args.matched_pseudo_arms or args.matched_augment_only else 128,
               'label_seed_offset': args.label_seed_offset, 'head_only': args.head_only, 'torch_version': torch.__version__, 'gpu': torch.cuda.get_device_name(0), 'models': {}}
    model_specs = [('snn_lif_surrogate', Snn)] if args.snn_only else [('ann_gru', Ann), ('snn_lif_surrogate', Snn)]
    for model_name, constructor in model_specs:
        checkpoint = args.pilot_dir / f'{model_name}.pt'
        expected = pilot['models'][model_name]['checkpoint_sha256']
        if hashlib.sha256(checkpoint.read_bytes()).hexdigest() != expected:
            raise ValueError('checkpoint checksum mismatch')
        saved = torch.load(checkpoint, map_location='cpu', weights_only=True)
        classes = np.asarray(saved['classes'], dtype=np.int32)
        if not np.isin(np.concatenate([init_y, old_y]), classes).all():
            raise ValueError('initialization label outside vocabulary')
        means = torch.tensor(saved['event_mean'], device='cuda', dtype=torch.float32)
        scales = torch.tensor(saved['event_scale'], device='cuda', dtype=torch.float32)
        def transform(x, mask):
            return ((torch.sign(x) * torch.log1p(torch.abs(x)) - means) / scales) * mask.unsqueeze(-1)
        def logits_for(model, x, mask):
            with torch.inference_mode():
                result = []
                for start in range(0, len(x), 2048):
                    xx = torch.as_tensor(x[start:start + 2048], dtype=torch.float32, device='cuda')
                    mm = torch.as_tensor(mask[start:start + 2048], device='cuda')
                    result.append(model(transform(xx, mm), mm).cpu())
                return torch.cat(result)
        def old_score(model):
            pred = classes[logits_for(model, old_x, old_m).argmax(1).numpy()]
            f1 = []
            for code in classes:
                tp = int(np.count_nonzero((pred == code) & (old_y == code)))
                fp = int(np.count_nonzero((pred == code) & (old_y != code)))
                fn = int(np.count_nonzero((pred != code) & (old_y == code)))
                f1.append(2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0)
            return {'accuracy': float(np.mean(pred == old_y)), 'macro_f1_fixed_vocabulary': float(np.mean(f1)),
                    'ground_truth_classes': int(len(np.unique(old_y)))}
        arms = {}
        arm_names = ('matched_aug_pseudo',) if args.matched_augment_only else ('matched_control', 'matched_pseudo') if args.matched_pseudo_arms else ('replay',) if args.replay_only else ('replay_class_gate',) if args.class_gated_only else ('replay_extra_labels',) if args.replay_extra_labels_only else ('replay_pseudo',) if args.replay_pseudo_only else (('supervised', 'replay') if args.no_pseudo_arms else ('supervised', 'replay', 'pseudo', 'replay_pseudo'))
        for arm in arm_names:
            print(f'processing model={model_name} arm={arm}', flush=True)
            model = constructor(len(classes)).cuda()
            model.load_state_dict(saved['model'])
            if args.head_only:
                for name, parameter in model.named_parameters():
                    parameter.requires_grad_(name.startswith('head.'))
            optimizer = torch.optim.Adam((p for p in model.parameters() if p.requires_grad), lr=0.001)
            arm_result = {'initial_old_holdout': None, 'weeks': {}}
            model.eval()
            arm_result['initial_old_holdout'] = old_score(model)
            for week in range(15, 19):
                model.eval()
                def predict(batch):
                    return classes[logits_for(model, batch.events, batch.mask).argmax(1).numpy()]
                pred_path = args.output_dir / f'{model_name}_{arm}_w{week}.npz'
                score, released = run_week(args.archive, weeks[week], predict, classes, 1000, 20261114 + week + args.label_seed_offset, pred_path, 2048)
                if week == 15 and score['prediction_sha256'] != pilot['models'][model_name]['score']['prediction_sha256']:
                    raise RuntimeError(f'{model_name}: W15 frozen checkpoint predictions differ from pilot')
                record = {'score_before_update': score,
                          'released_row_ids_sha256': hashlib.sha256('\n'.join(f'{d}:{i}' for d, i, _ in released).encode()).hexdigest(),
                          'old_holdout_before_update': old_score(model)}
                if week < 18:
                    current_x, current_m, current_y = selected_examples(args.archive, weeks[week], released)
                    chosen_labels = np.sort(np.random.default_rng(20261114 + week + args.label_seed_offset).choice(populations[week], 1000, replace=False))
                    unlabeled_pool = np.setdiff1d(np.arange(populations[week]), chosen_labels, assume_unique=True)
                    unlabeled_ids = np.sort(np.random.default_rng(20261300 + week).choice(unlabeled_pool, 1000, replace=False))
                    un_x, un_m, _, un_refs = select_positions(args.archive, weeks[week], unlabeled_ids, labels=False)
                    if set(un_refs) & {(d, i) for d, i, _ in released}:
                        raise RuntimeError('labeled/unlabeled sample overlap')
                    teacher_started = time.perf_counter()
                    unlabeled_logits = logits_for(model, un_x, un_m)
                    record['teacher_inference_seconds'] = time.perf_counter() - teacher_started
                    probs = torch.softmax(unlabeled_logits, dim=1)
                    confidence, pseudo_index = probs.max(1)
                    accepted = (confidence.numpy() >= args.pseudo_threshold)
                    pseudo_y = classes[pseudo_index.numpy()[accepted]]
                    record['unlabeled_row_ids_sha256'] = hashlib.sha256('\n'.join(f'{d}:{i}' for d, i in un_refs).encode()).hexdigest()
                    record['pseudo_candidates'] = len(un_x)
                    record['pseudo_accepted'] = int(accepted.sum())
                    labeled_probs = torch.softmax(logits_for(model, current_x, current_m), dim=1)
                    lc, li = labeled_probs.max(1)
                    lm = lc.numpy() >= args.pseudo_threshold
                    record['labeled_confidence_accepted'] = int(lm.sum())
                    record['labeled_confidence_accuracy'] = float(np.mean(classes[li.numpy()[lm]] == current_y[lm])) if lm.any() else None
                    predicted_labeled = classes[li.numpy()]
                    record['labeled_accepted_by_predicted_class'] = {str(int(c)): {'accepted': int(np.sum(lm & (predicted_labeled == c))), 'correct': int(np.sum(lm & (predicted_labeled == c) & (current_y == c)))} for c in np.unique(predicted_labeled[lm])}
                    if arm == 'replay_class_gate':
                        allowed = []
                        for code, stats in record['labeled_accepted_by_predicted_class'].items():
                            n, correct = stats['accepted'], stats['correct']
                            phat, z = correct / n, 1.959963984540054
                            lower = (phat + z*z/(2*n) - z*np.sqrt(phat*(1-phat)/n + z*z/(4*n*n))) / (1 + z*z/n)
                            stats['wilson_lower'] = float(lower)
                            if n >= 10 and lower >= 0.5:
                                allowed.append(int(code))
                        record['gate_allowed_classes'] = allowed
                        record['pre_gate_pseudo_accepted'] = int(accepted.sum())
                        accepted &= np.isin(classes[pseudo_index.numpy()], allowed)
                        pseudo_y = classes[pseudo_index.numpy()[accepted]]
                        record['pseudo_accepted'] = int(accepted.sum())
                    record['pseudo_by_predicted_class'] = {str(int(c)): int(np.sum(pseudo_y == c)) for c in np.unique(pseudo_y)}
                    replay_on = arm in ('replay', 'replay_pseudo', 'replay_extra_labels', 'replay_class_gate', 'matched_control', 'matched_pseudo', 'matched_aug_pseudo')
                    pseudo_on = (arm in ('pseudo', 'replay_pseudo', 'replay_class_gate') and accepted.any()) or arm == 'replay_extra_labels'
                    weights_counts = np.bincount(np.searchsorted(classes, np.concatenate([current_y, replay_y])), minlength=len(classes))
                    weights = np.zeros(len(classes), dtype=np.float32)
                    observed = weights_counts > 0
                    weights[observed] = 1 / np.sqrt(weights_counts[observed])
                    weights[observed] /= weights[observed].mean()
                    class_weights = torch.tensor(weights, device='cuda')
                    rng_batches = np.random.default_rng(20261400 + week)
                    rng_extra = np.random.default_rng(20261500 + week)
                    supervised_batch_digest = hashlib.sha256()
                    augmentation_rng = torch.Generator(device='cuda').manual_seed(20261600 + week)
                    model.train()
                    started = time.perf_counter()
                    for _ in range(40):
                        matched = arm in ('matched_control', 'matched_pseudo', 'matched_aug_pseudo')
                        current_n = 64 if matched else 32 if replay_on and pseudo_on else 64 if replay_on or pseudo_on else 128
                        replay_n = 64 if matched else 32 if replay_on and pseudo_on else 64 if replay_on else 0
                        pseudo_n = 64 if matched or pseudo_on else 0
                        ci = rng_batches.integers(0, len(current_y), current_n)
                        chunks_x, chunks_m, chunks_y = [current_x[ci]], [current_m[ci]], [current_y[ci]]
                        if replay_n:
                            ri = rng_batches.integers(0, len(replay_y), replay_n)
                            chunks_x.append(replay_x[ri]); chunks_m.append(replay_m[ri]); chunks_y.append(replay_y[ri])
                        if matched:
                            supervised_batch_digest.update(ci.astype('<i8').tobytes())
                            supervised_batch_digest.update(ri.astype('<i8').tobytes())
                        supervised_n = current_n + replay_n
                        if pseudo_n:
                            if matched:
                                if accepted.any():
                                    pi = rng_extra.integers(0, len(pseudo_y), pseudo_n)
                                    chunks_x.append(un_x[accepted][pi]); chunks_m.append(un_m[accepted][pi]); chunks_y.append(pseudo_y[pi])
                                else:
                                    pi = rng_extra.integers(0, len(un_x), pseudo_n)
                                    chunks_x.append(un_x[pi]); chunks_m.append(un_m[pi]); chunks_y.append(classes[pseudo_index.numpy()[pi]])
                            elif arm == 'replay_extra_labels':
                                ei = rng_batches.integers(0, len(current_y), 32)
                                er = rng_batches.integers(0, len(replay_y), 32)
                                chunks_x.extend((current_x[ei], replay_x[er])); chunks_m.extend((current_m[ei], replay_m[er])); chunks_y.extend((current_y[ei], replay_y[er]))
                            else:
                                pi = rng_batches.integers(0, len(pseudo_y), pseudo_n)
                                chunks_x.append(un_x[accepted][pi]); chunks_m.append(un_m[accepted][pi]); chunks_y.append(pseudo_y[pi])
                        x = torch.as_tensor(np.concatenate(chunks_x), device='cuda', dtype=torch.float32)
                        mask = torch.as_tensor(np.concatenate(chunks_m), device='cuda')
                        y = torch.as_tensor(np.searchsorted(classes, np.concatenate(chunks_y)), device='cuda', dtype=torch.long)
                        optimizer.zero_grad(set_to_none=True)
                        transformed = transform(x, mask)
                        if arm == 'matched_aug_pseudo':
                            extra = transformed[supervised_n:]
                            keep = torch.rand(extra.shape, device='cuda', generator=augmentation_rng) >= 0.1
                            transformed = torch.cat((transformed[:supervised_n], extra * keep), dim=0)
                        logits = model(transformed, mask)
                        loss = nn.functional.cross_entropy(logits[:supervised_n], y[:supervised_n], weight=class_weights)
                        if pseudo_n:
                            extra_loss = nn.functional.cross_entropy(logits[supervised_n:], y[supervised_n:])
                            extra_weight = float(arm != 'matched_control' and (not matched or accepted.any()))
                            loss = loss + extra_weight * extra_loss
                        if not torch.isfinite(loss):
                            raise RuntimeError('non-finite update loss')
                        loss.backward(); optimizer.step()
                    torch.cuda.synchronize()
                    if args.head_only:
                        for name, value in model.state_dict().items():
                            if not name.startswith('head.') and not torch.equal(value.cpu(), saved['model'][name].cpu()):
                                raise RuntimeError('frozen encoder changed')
                    record['update_seconds'] = time.perf_counter() - started
                    record['update_steps'] = 40
                    if arm in ('matched_control', 'matched_pseudo', 'matched_aug_pseudo'):
                        record['supervised_batch_indices_sha256'] = supervised_batch_digest.hexdigest()
                        record['extra_loss_weight'] = float(arm in ('matched_pseudo', 'matched_aug_pseudo') and accepted.any())
                    record['effective_replay'] = replay_on
                    record['effective_pseudo'] = bool((pseudo_on and arm != 'replay_extra_labels') or (arm in ('matched_pseudo', 'matched_aug_pseudo') and accepted.any()))
                    record['extra_true_label_control'] = arm == 'replay_extra_labels'
                    checkpoint_path = args.output_dir / f'{model_name}_{arm}_after_w{week}.pt'
                    torch.save({'model': model.state_dict(), 'optimizer': optimizer.state_dict(),
                                'classes': classes.tolist(), 'event_mean': saved['event_mean'],
                                'event_scale': saved['event_scale'], 'after_week': week, 'arm': arm}, checkpoint_path)
                    record['checkpoint_sha256'] = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
                    model.eval()
                    record['old_holdout_after_update'] = old_score(model)
                arm_result['weeks'][str(week)] = record
                print(f'completed model={model_name} arm={arm} week={week}', flush=True)
            arms[arm] = arm_result
        results['models'][model_name] = {'initial_checkpoint_sha256': expected, 'arms': arms}
    for week in range(15, 19):
        records = [a['weeks'][str(week)] for m in results['models'].values() for a in m['arms'].values()]
        if len({r['released_row_ids_sha256'] for r in records}) != 1:
            raise RuntimeError('arms did not receive identical labeled rows')
        if week < 18 and len({r['unlabeled_row_ids_sha256'] for r in records}) != 1:
            raise RuntimeError('arms did not receive identical unlabeled rows')
    args.summary_path.parent.mkdir(parents=True, exist_ok=True)
    args.summary_path.write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
