"""Run the registered offline audits in a fresh work/ directory."""
import argparse
import copy
import sys
from pathlib import Path

from . import runner


def run_audits(output_dir, registry=None):
    work = (runner.ROOT / 'work').resolve()
    destination = (runner.ROOT / Path(output_dir)).resolve()
    if not destination.is_relative_to(work):
        raise ValueError('audit output directory must be under work/')
    registry = copy.deepcopy(registry if registry is not None else runner.load_registry())
    for audit in registry['audits']:
        outputs = {name: str(destination / Path(name).relative_to('work'))
                   for name in audit['outputs']}
        for path in outputs.values():
            if Path(path).exists():
                print('audit output already exists: ' + path +
                      '; choose a fresh --output-dir under work/', file=sys.stderr)
                return 1
        audit['args'] = [outputs.get(arg, arg) for arg in audit['args']]
        audit['outputs'] = list(outputs.values())
    destination.mkdir(parents=True, exist_ok=True)
    return runner.run_audits(registry)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='fresh audit output directory under work/')
    raise SystemExit(run_audits(parser.parse_args().output_dir))
