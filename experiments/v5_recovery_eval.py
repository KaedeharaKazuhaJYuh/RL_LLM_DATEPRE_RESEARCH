"""Frozen evaluation of a constrained recovery policy, with full paired records."""
import argparse
import json
import tempfile
import time
from pathlib import Path

from experiments.v5_recovery_train import Policy
from research.io import ROOT, digest, write_json
from research.v5_recovery_env import ACTIONS, RecoveryEnv
from research.v5_recovery_protocol import PROTOCOL, load


def run(args):
    if Path(args.out).exists():
        raise FileExistsError('new output required')
    tasks, oracle, manifest = load(args.protocol)
    policy = Policy(args.model, args.adapter)
    records = []
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='recovery_eval_', dir=ROOT/'work') as folder:
        for task in [t for t in tasks if t['split'] == 'dev']:
            for mode in manifest['modes']:
                env = RecoveryEnv(task, oracle[task['task_id']], Path(folder)/f'{task["task_id"]}_{mode}', mode)
                actions = []
                while not env.done:
                    index, _ = policy.act(env.observation())
                    actions.append(ACTIONS[index])
                    env.step(ACTIONS[index])
                records.append({'task_id': task['task_id'], 'source_id': task['source_id'],
                                'family': task['pair_family'], 'language': task['language'],
                                'mode': mode, 'actions': actions, **env.result()})
    report = {'schema_version': 'v5-recovery-eval-1',
              'protocol_sha256': digest(Path(args.protocol)/'manifest.json'),
              'model_sha256': digest(Path(args.model)/'model.safetensors'),
              'adapter_sha256': digest(Path(args.adapter)/'adapter_model.safetensors'),
              'scope': 'conditional_recovery_given_prefix_and_suffix',
              'decoding': 'greedy_4_way_next_token', 'episodes': len(records),
              'passed': sum(row['passed'] for row in records),
              'elapsed_seconds': time.perf_counter()-started, 'records': records}
    write_json(args.out, report)
    return {k:v for k,v in report.items() if k != 'records'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', default=str(PROTOCOL))
    parser.add_argument('--model', default='work/modelscope_deepseek_r1_1p5b')
    parser.add_argument('--adapter', required=True)
    parser.add_argument('--out', required=True)
    print(json.dumps(run(parser.parse_args()), indent=2))
