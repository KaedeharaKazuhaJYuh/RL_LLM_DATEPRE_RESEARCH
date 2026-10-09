"""Audit once-frozen results and publish descriptive paired evidence, without tuning."""
from collections import defaultdict
from pathlib import Path
import statistics
import json

from research.io import ROOT, digest, write_json
from research.v5_recovery_audit import evaluation, training, require
from research.v5_recovery_protocol import PROTOCOL, load


def macro(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row['source_id'], row['family'])].append(int(row['passed']))
    return statistics.mean(statistics.mean(values) for values in groups.values())


def slices(rows):
    result = {}
    for field in ('source_id', 'family', 'language', 'mode'):
        groups = defaultdict(list)
        for row in rows:
            groups[str(row[field])].append(row)
        result[field] = {key: {'passed': sum(r['passed'] for r in values), 'episodes': len(values),
                              'duplicate_commits': sum(r['duplicate_commit'] for r in values)}
                         for key, values in sorted(groups.items())}
    return result


def failure_patterns(rows):
    groups = defaultdict(lambda: {'episodes': 0, 'passed': 0, 'duplicate_commits': 0})
    for row in rows:
        key = ' -> '.join(row['actions'])
        group = groups[key]
        group['episodes'] += 1
        group['passed'] += int(row['passed'])
        group['duplicate_commits'] += int(row['duplicate_commit'])
    return dict(sorted(groups.items(), key=lambda pair: (-pair[1]['episodes'], pair[0])))


def main():
    _, _, manifest = load()
    arms = ['baseline'] + manifest['arms']
    model_hash = digest(ROOT/'work/modelscope_deepseek_r1_1p5b/model.safetensors')
    freeze = json.loads((ROOT/'work/v5_0_15_freeze.json').read_text(encoding='utf-8'))
    require(freeze['model_sha256'] == model_hash, 'freeze base model mismatch')
    require(all(digest(ROOT/name) == value for name, value in freeze['implementation_sha256'].items()),
            'frozen implementation changed')
    frozen_runs = {(r['arm'], r['seed']): r for r in freeze['training']}
    require(len(frozen_runs) == len(freeze['training']) == 15, 'incomplete freeze receipt')
    train, evaluations, all_rows = [], [], {a: [] for a in arms}
    by_seed = {}
    for seed in manifest['seeds']:
        by_seed[seed] = {}
        for arm in arms:
            target = ROOT/f'work/v5_0_15_{arm}_seed{seed}'
            if arm == 'baseline':
                adapter_hash = digest(ROOT/f'work/v5_0_05_sft_control_seed{seed}/adapter/adapter_model.safetensors')
            else:
                summary = training(target, arm, seed)
                require(summary['model_sha256'] == model_hash, 'training model mismatch')
                train.append(summary)
                adapter_hash = summary['adapter_sha256']
                frozen = frozen_runs[arm, seed]
                require(frozen['summary_sha256'] == digest(target/'summary.json') and
                        frozen['adapter_sha256'] == adapter_hash, 'training changed after freeze')
            path = Path(str(target)+'_eval.json')
            report = evaluation(path, adapter_hash, model_hash)
            evaluations.append({'seed': seed, 'arm': arm, 'file_sha256': digest(path), **report})
            by_seed[seed][arm] = report['records']
            all_rows[arm].extend(report['records'])
    summary = {arm: {'passed': sum(r['passed'] for r in rows), 'episodes': len(rows),
                     'source_family_macro': macro(rows), 'slices': slices(rows),
                     'action_patterns': failure_patterns(rows),
                     'seeds': {str(seed): sum(r['passed'] for r in by_seed[seed][arm])
                               for seed in manifest['seeds']}}
               for arm, rows in all_rows.items()}
    training_cost = {}
    for arm in manifest['arms']:
        runs = [r for r in train if r['arm'] == arm]
        training_cost[arm] = {key: sum(r[key] for r in runs)
                              for key in ('optimizer_steps', 'forward_input_tokens', 'elapsed_seconds')}
        training_cost[arm]['budget'] = {key: sum(r['budget'][key] for r in runs)
                                        for key in runs[0]['budget']}
        training_cost[arm]['skipped_groups'] = sum(not row['updated'] for r in runs for row in r['records'])
        training_cost[arm]['mode_signal'] = {
            mode: {'groups': sum(row['mode'] == mode for r in runs for row in r['records']),
                   'skipped_groups': sum(row['mode'] == mode and not row['updated']
                                         for r in runs for row in r['records'])}
            for mode in manifest['train_modes']}
    source_equivalence = {}
    for arm in arms:
        pairs = []
        for seed in manifest['seeds']:
            groups = defaultdict(list)
            for row in by_seed[seed][arm]:
                groups[(row['family'], row['language'], row['mode'])].append(row)
            pairs.extend(values for values in groups.values())
        source_equivalence[arm] = {
            'source_pairs': len(pairs),
            'identical_action_and_pass_pairs': sum(len(v) == 2 and v[0]['actions'] == v[1]['actions'] and
                                                   v[0]['passed'] == v[1]['passed'] for v in pairs)}
    comparisons = {}
    for other in ('sft', 'grpo', 'branch', 'counterfactual'):
        changes = []
        for seed in manifest['seeds']:
            before = {(r['task_id'], r['mode']): r for r in by_seed[seed][other]}
            after = by_seed[seed]['paired']
            gained = [r for r in after if r['passed'] and not before[r['task_id'], r['mode']]['passed']]
            lost = [r for r in after if not r['passed'] and before[r['task_id'], r['mode']]['passed']]
            changes.append({'seed': seed, 'gained': gained, 'lost': lost, 'net': len(gained)-len(lost)})
        gap = summary['paired']['source_family_macro']-summary[other]['source_family_macro']
        comparisons[other] = {'macro_gap': gap, 'positive_seeds': sum(c['net'] > 0 for c in changes),
                              'per_seed': changes}
    clean_ok = summary['paired']['slices']['mode']['none']['passed'] >= summary['sft']['slices']['mode']['none']['passed']
    gate = clean_ok and all(c['macro_gap'] > 0 and c['positive_seeds'] >= 2 for c in comparisons.values())
    result = {'schema_version': 'v5-recovery-beta2-audit-1',
              'protocol_sha256': digest(PROTOCOL/'manifest.json'),
              'preregistration_sha256': digest(ROOT/'reports/V5_0_15_BETA_1_PROTOCOL.md'),
              'model_sha256': model_hash, 'summary': summary, 'paired_comparisons': comparisons,
              'training_cost': training_cost,
              'source_trace_equivalence': source_equivalence,
              'policy_observation_scope': 'request and recovery history only; no CSV values/source identity/bindings; source holdout is execution coverage, not policy source generalization',
              'freeze_receipt': freeze,
              'confirmation_gate_passed': gate, 'clean_no_regression': clean_ok,
              'scope': 'conditional recovery; 2 source clusters; descriptive, not population significance',
              'training': train, 'evaluations': evaluations}
    write_json(ROOT/'reports/v5_0_15_beta2_results.json', result)
    for arm, values in summary.items():
        print(arm, values['passed'], '/', values['episodes'], values['seeds'])
    print('CONFIRMATION_GATE', gate)


if __name__ == '__main__':
    main()
