"""Re-runs design-time exploration steps E1-E9 as subprocesses over the unmodified scratch scripts.

The four gate0*.py scripts in this directory are byte-identical copies of the design-time scratch
scripts; this driver never edits them. Every result line carries the full config and one of the
labels explored / D1 candidate / final-check. A step whose recorded parameters cannot be passed to
the unmodified script is reported as not reproducible instead of being patched.

Not part of CI. One step/config at a time:
    python run_exploration.py --parts PARTS_DIR [--step E7-R0 --config 3]
then assemble the committed log (every part must be present):
    python run_exploration.py --parts PARTS_DIR --assemble --output exploration_log.txt
The whole re-run is about an hour of CPU; parts of one step may be run in parallel.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKEWED = [35, 20, 12, 10, 8, 6, 5, 4]
EQUAL = [1] * 8
HEADER = ['# VeriCost 0.5.65-dev design-time exploration re-run (E1-E9)',
          '# labels: explored | D1 candidate | final-check',
          '# scripts are unmodified copies of the design-time scratch scripts']

# (step, script, description, label, configs) with configs = list of dicts, or a string reason when
# the recorded parameters cannot be reproduced with the unmodified script.
STEPS = [
    ('E1', 'gate0.py', 'Rev 1: H = 10, R0 rates, no patch candidate', 'explored', [{}]),
    ('E2', 'gate0_v2.py', 'Patch candidate, cc reveals the flagged part, F_hist, F_hist+; H in {10, 2, 0}',
     'explored', [{'H': 10}, {'H': 2}, {'H': 0}]),
    ('E3', 'gate0_v2.py', 'H in {3,5,10,20} x P_cc in {.3,.5,.7}, L = 3, kappa in {.3,.5,1,2}',
     'explored', [{'H': h, 'p_cc': p, 'L': [3.0], 'kappa': [0.3, 0.5, 1.0, 2.0]}
                  for h in (3, 5, 10, 20) for p in (0.3, 0.5, 0.7)]),
    ('E4', 'gate0_v2.py', 'Escalate reactions in F (present in the unmodified script); default grid',
     'explored', [{'H': 10}]),
    ('E5', 'gate0_v3.py', 'Partial global coverage q_g', 'D1 candidate', [{'q_g': 1.0}, {'q_g': 0.5}]),
    ('E6', 'gate0_v4.py', 'Unequal part shares and spot orders', 'explored',
     [{'shares': EQUAL}, {'shares': SKEWED}]),
    ('E7', 'gate0_v4.py', 'Rates R0/R1/R2 x H {3,5,10} x q_g {1,.5} x kappa {.3,1,2} x L {1,3}',
     'explored', 'the R1/R2 rate vectors were not recorded in the scratch results, so only the R0 '
                 'slice of the E7 grid is re-run below'),
    ('E7-R0', 'gate0_v4.py', 'E7 restricted to the recorded R0 rates', 'explored',
     [{'H': h, 'q_g': q, 'kappa': [0.3, 1.0, 2.0], 'L': [1.0, 3.0]}
      for h in (3, 5, 10) for q in (1.0, 0.5)]),
    ('E8', 'gate0_v4.py', 'R2 / H = 5 / q_g .5 skewed shares; levers H = 3, q_g = .3, L = 5',
     'explored', 'the R2 rate vector was not recorded in the scratch results; the H = 3 / q_g = .3 / '
                 'L = 5 levers are re-run on R0 below'),
    ('E8-R0', 'gate0_v4.py', 'E8 levers on the recorded R0 rates', 'explored',
     [{'H': 3, 'q_g': 0.3, 'shares': SKEWED, 'L': [5.0], 'kappa': [0.3, 1.0, 3.0]}]),
    ('E9', 'gate0_v4.py', 'Final check: rev-1 params, equal and skewed shares; D1 equal and skewed',
     'final-check',
     [{'H': 10, 'q_g': 1.0, 'shares': EQUAL}, {'H': 10, 'q_g': 1.0, 'shares': SKEWED},
      {'H': 10, 'q_g': 0.5, 'shares': EQUAL}, {'H': 10, 'q_g': 0.5, 'shares': SKEWED}]),
]


def part_path(parts, step, index):
    return Path(parts) / f'{step}.{index:02d}.txt'


def run_config(parts, step, script, label, index, config):
    command = [sys.executable, str(HERE / script)]
    text = json.dumps(config, sort_keys=True)
    if config:
        command.append(text)
    started = time.time()
    done = subprocess.run(command, capture_output=True, text=True, check=True)
    lines = [f'{step} label={label} config={text} | {line}'
             for line in done.stdout.splitlines() if line.strip()]
    lines.append(f'# {step}: config={text} seconds={time.time() - started:.1f}')
    path = part_path(parts, step, index)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'{step}[{index}]: {len(lines) - 1} line(s) in {time.time() - started:.1f}s', flush=True)


def assemble(parts, output):
    lines = list(HEADER)
    for step, script, description, _, configs in STEPS:
        lines.append('')
        lines.append(f'# {step}: {description} [{script}]')
        if isinstance(configs, str):
            lines.append(f'# {step}: not reproducible with unmodified script: {configs}')
            continue
        for index in range(len(configs)):
            path = part_path(parts, step, index)
            if not path.exists():
                raise ValueError('missing exploration part: ' + path.name)
            lines.extend(path.read_text(encoding='utf-8').splitlines())
    with Path(output).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write('\n'.join(lines) + '\n')
    print('wrote ' + str(output))


def main(args):
    if args.assemble:
        assemble(args.parts, args.output)
        return
    for step, script, _, label, configs in STEPS:
        if isinstance(configs, str) or (args.step and args.step != step):
            continue
        for index, config in enumerate(configs):
            if args.config is None or args.config == index:
                run_config(args.parts, step, script, label, index, config)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--parts', type=Path, default=HERE / 'parts')
    parser.add_argument('--step')
    parser.add_argument('--config', type=int)
    parser.add_argument('--assemble', action='store_true')
    parser.add_argument('--output', type=Path, default=HERE / 'exploration_log.txt')
    main(parser.parse_args())
