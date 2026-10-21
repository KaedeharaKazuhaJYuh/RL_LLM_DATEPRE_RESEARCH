"""Previously seen new-wording diagnostic for the V5 supervised control."""

import argparse
import json
from pathlib import Path

from research.io import ROOT, digest, write_json
from research.v5_beta_audit import SEEDS, _indexed


PROTOCOL_SHA = '6387bc6780dc6b5b594e5e8fa4709da9a343b6e786270e87ea56a00bb6ba994c'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def run(work, out):
    work, out = Path(work).resolve(), Path(out)
    if out.exists():
        raise FileExistsError('new diagnostic output required')
    protocol = ROOT / 'tasks/v5/beta_holdout_v1'
    if digest(protocol / 'manifest.json') != PROTOCOL_SHA:
        raise ValueError('diagnostic protocol changed')
    tasks = {task['task_id']: task for task in read(protocol / 'tasks.json')}
    seeds = []
    for seed in SEEDS:
        evaluations = {}
        paths = {
            'initial_sft': work / f'v5_beta1_sft_seed{seed}.json',
            'rl': work / f'v5_beta1_rl_seed{seed}.json',
            'control': work / f'v5_0_05_sft_control_novel_eval_seed{seed}.json',
        }
        for label, path in paths.items():
            value = read(path)
            if value['protocol_sha256'] != PROTOCOL_SHA:
                raise ValueError(f'wrong diagnostic protocol for {seed} {label}')
            if label == 'control' and Path(value['adapter']).resolve() != (
                    work / f'v5_0_05_sft_control_seed{seed}/adapter').resolve():
                raise ValueError(f'wrong control adapter for {seed}')
            _indexed(value, tasks)
            evaluations[label] = value
        seeds.append({'seed': seed,
                      **{f'{label}_passed': value['passed']
                         for label, value in evaluations.items()},
                      **{f'{label}_eval_sha256': digest(path)
                         for label, path in paths.items()}})
    result = {'schema_version': 'v5-sft-control-new-wording-diagnostic-1',
              'protocol_sha256': PROTOCOL_SHA, 'previously_used_for_course_selection': True,
              'seeds': seeds,
              'initial_sft_passed': sum(row['initial_sft_passed'] for row in seeds),
              'rl_passed': sum(row['rl_passed'] for row in seeds),
              'control_passed': sum(row['control_passed'] for row in seeds),
              'new_blind_test': False}
    write_json(out, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work', default=str(ROOT / 'work'))
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    result = run(args.work, args.out)
    print(json.dumps({key: result[key] for key in (
        'initial_sft_passed', 'rl_passed', 'control_passed')}, ensure_ascii=False))
