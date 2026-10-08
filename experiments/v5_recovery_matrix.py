"""Run frozen training before opening any holdout model results."""
import argparse
import subprocess
import sys
from pathlib import Path

from research.io import ROOT
from research.v5_recovery_protocol import load


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=('train', 'eval'), required=True)
    args = parser.parse_args()
    _, _, manifest = load()
    for seed in manifest['seeds']:
        initial = f'work/v5_0_05_sft_control_seed{seed}/adapter'
        arms = manifest['arms'] if args.stage == 'train' else ['baseline'] + manifest['arms']
        for arm in arms:
            target = ROOT/f'work/v5_0_15_{arm}_seed{seed}'
            if args.stage == 'train':
                if (target/'summary.json').exists():
                    raise FileExistsError('matrix does not silently reuse training outputs')
                command = [sys.executable, '-m', 'experiments.v5_recovery_train',
                           '--adapter', initial, '--arm', arm, '--seed', str(seed), '--out', str(target)]
            else:
                # Ensure every frozen training arm finished before evaluation.
                for s in manifest['seeds']:
                    for a in manifest['arms']:
                        if not (ROOT/f'work/v5_0_15_{a}_seed{s}/summary.json').exists():
                            raise RuntimeError('complete entire training matrix before evaluation')
                adapter = initial if arm == 'baseline' else str(target/'adapter')
                command = [sys.executable, '-m', 'experiments.v5_recovery_eval',
                           '--adapter', adapter, '--out', str(target)+ '_eval.json']
            print('RUN', seed, arm, args.stage, flush=True)
            subprocess.run(command, cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
