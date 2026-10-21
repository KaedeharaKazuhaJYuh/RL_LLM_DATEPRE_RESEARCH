"""Run frozen training before opening any holdout model results."""
import argparse
import json
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path

from research.io import ROOT
from research.v5_recovery_protocol import load
from research.v5_recovery_protocol import PROTOCOL
from research.v5_recovery_audit import training, evaluation
from research.io import digest, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=('train', 'eval'), required=True)
    parser.add_argument('--resume', action='store_true', help='reuse only verified complete results')
    args = parser.parse_args()
    _, _, manifest = load()
    model = ROOT/'work/modelscope_deepseek_r1_1p5b'
    model_hash = digest(model/'model.safetensors')
    if args.stage == 'eval':
        frozen = []
        for s in manifest['seeds']:
            for a in manifest['arms']:
                target = ROOT/f'work/v5_0_15_{a}_seed{s}'
                verified = training(target, a, s)
                if verified['model_sha256'] != model_hash:
                    raise ValueError('training base model mismatch')
                frozen.append({'seed': s, 'arm': a, 'adapter_sha256': verified['adapter_sha256'],
                               'summary_sha256': digest(target/'summary.json')})
        receipt = {'model_sha256': model_hash, 'training': frozen,
                   'implementation_sha256': {name: digest(ROOT/name) for name in (
                       'experiments/v5_recovery_train.py', 'experiments/v5_recovery_eval.py',
                       'research/v5_recovery_env.py', 'research/v5_recovery_protocol.py')}}
        freeze_path = ROOT/'work/v5_0_15_freeze.json'
        if freeze_path.exists():
            if json.loads(freeze_path.read_text(encoding='utf-8')) != receipt:
                raise ValueError('training changed after evaluation freeze')
        else:
            if any((ROOT/'work').glob('v5_0_15_*_eval.json')):
                raise ValueError('evaluation exists without freeze receipt')
            write_json(freeze_path, receipt)
    for seed in manifest['seeds']:
        initial = f'work/v5_0_05_sft_control_seed{seed}/adapter'
        arms = manifest['arms'] if args.stage == 'train' else ['baseline'] + manifest['arms']
        for arm in arms:
            target = ROOT/f'work/v5_0_15_{arm}_seed{seed}'
            if args.stage == 'train':
                if (target/'summary.json').exists():
                    if not args.resume:
                        raise FileExistsError('use explicit --resume to verify existing training')
                    verified = training(target, arm, seed)
                    if verified['model_sha256'] != model_hash:
                        raise ValueError('training base model mismatch')
                    print('VERIFIED', seed, arm, flush=True)
                    continue
                command = [sys.executable, '-m', 'experiments.v5_recovery_train',
                           '--adapter', initial, '--arm', arm, '--seed', str(seed), '--out', str(target)]
            else:
                # Ensure every frozen training arm finished before evaluation.
                for s in manifest['seeds']:
                    for a in manifest['arms']:
                        if not (ROOT/f'work/v5_0_15_{a}_seed{s}/summary.json').exists():
                            raise RuntimeError('complete entire training matrix before evaluation')
                adapter = initial if arm == 'baseline' else str(target/'adapter')
                eval_path = Path(str(target) + '_eval.json')
                if eval_path.exists():
                    if not args.resume:
                        raise FileExistsError('use explicit --resume to verify existing evaluation')
                    evaluation(eval_path, digest(ROOT/adapter/'adapter_model.safetensors'), model_hash)
                    print('VERIFIED', seed, arm, flush=True)
                    continue
                command = [sys.executable, '-m', 'experiments.v5_recovery_eval',
                           '--adapter', adapter, '--out', str(target)+ '_eval.json']
            print('RUN', seed, arm, args.stage, flush=True)
            if args.stage == 'eval':
                # Serial, fresh policy per adapter. Reuse Python imports only;
                # no batching, cached predictions, or persistent environment state.
                from experiments.v5_recovery_eval import run
                print(run(SimpleNamespace(protocol=str(PROTOCOL), model=str(model),
                                          adapter=str(ROOT/adapter), out=str(eval_path))), flush=True)
            else:
                subprocess.run(command, cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
