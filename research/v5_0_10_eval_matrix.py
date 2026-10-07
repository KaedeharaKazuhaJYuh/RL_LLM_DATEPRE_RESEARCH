"""Run the frozen serial GPU evaluation matrix without choosing a best seed."""
import argparse
import subprocess
import sys
from pathlib import Path

from research.io import ROOT
from research.v5_0_10_model_audit import SEEDS


def run(work=ROOT / 'work'):
    work = Path(work)
    protocol = ROOT / 'tasks/v5/rewrite_holdout_v1'
    model = work / 'modelscope_deepseek_r1_1p5b'
    jobs = []
    for seed in SEEDS:
        adapters = {'baseline': work / f'v5_0_05_sft_control_seed{seed}/adapter',
                    'sft': work / f'v5_0_10_sft_seed{seed}/adapter',
                    'rl': work / f'v5_0_10_rl_seed{seed}/adapter'}
        for label, adapter in adapters.items():
            output = work / f'v5_0_10_eval_{label}_seed{seed}.json'
            log = output.with_suffix('.log')
            if not (adapter / 'adapter_model.safetensors').is_file():
                raise FileNotFoundError(adapter)
            if output.exists() or log.exists():
                raise FileExistsError(f'new evaluation output required: {output}')
            jobs.append((seed, label, adapter, output, log))
    for index, (seed, label, adapter, output, log) in enumerate(jobs, 1):
        command = [sys.executable, '-m', 'experiments.v4_llm_eval',
                   '--protocol', str(protocol), '--model', str(model),
                   '--adapter', str(adapter), '--out', str(output),
                   '--fault-modes', 'none,transient_read,timeout,partial_write',
                   '--max-new-tokens', '48', '--batch-size', '1']
        print(f'[{index}/9] seed={seed} method={label}', flush=True)
        with log.open('w', encoding='utf-8') as stream:
            result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                    check=False)
        if result.returncode:
            raise RuntimeError(f'evaluation failed: {log} (exit {result.returncode})')
        print(f'[{index}/9] completed {output}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=ROOT / 'work')
    args = parser.parse_args()
    run(args.work)
