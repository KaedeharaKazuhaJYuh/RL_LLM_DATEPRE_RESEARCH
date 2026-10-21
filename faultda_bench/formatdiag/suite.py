import argparse
import itertools
import json
import random
import tempfile
from pathlib import Path

from . import VERSION
from .core import Client, body, sha_bytes, summarize
from ..pilot.suite import code_hashes
from ..pilot.contract import public_observation
from ..evidence.core import tasks
from ..trust.environment import ComputeFaultEnv
from ..semantic.tasks import REPO, sha
from ..clarity.tasks import write_json


def snapshots():
    with tempfile.TemporaryDirectory(prefix='faultda_format_snapshot_') as folder:
        return {t['id']: public_observation(ComputeFaultEnv(t, Path(folder) / t['id'],
                    mode='healthy', evidence='E1', budget=3)) for t in tasks()}


def protocol():
    cells = [dict(task_id=t['id'], thinking=mode, max_tokens=tokens, repeat=repeat)
             for t, mode, tokens, repeat in itertools.product(tasks(), ('disabled', 'enabled'), (800, 2048), (0, 1))]
    random.Random(2026101170).shuffle(cells)
    hashes = code_hashes()
    hashes.update({p.relative_to(REPO).as_posix(): sha(p) for p in Path(__file__).parent.glob('*.py')})
    return {'version': VERSION, 'order': cells, 'observations': snapshots(), 'code_sha256': hashes,
            'source_sha256': {t['source_path']: t['source_sha256'] for t in tasks()},
            'request_cap': 24, 'model': 'deepseek-flash', 'thinking_effort_when_enabled': 'low',
            'temperature': 0, 'timeout_seconds': 45, 'implicit_retries': 0,
            'scope': 'three initial public snapshots; two repeats per configuration; single decisions, no actions executed',
            'scientific_gate': 'HOLD'}


def live(plan, output):
    frozen = json.loads(Path(plan).read_text(encoding='utf-8'))
    if frozen != protocol():
        raise ValueError('protocol or frozen code changed')
    output = Path(output)
    pp, tp = output.with_suffix('.protocol.json'), output.with_suffix('.jsonl')
    if any(p.exists() for p in (output, pp, tp)):
        raise FileExistsError('use new paths')
    client = Client('deepseek-flash', max_calls=24)
    write_json(pp, frozen)
    rows = []
    with tp.open('xb') as stream:
        for cell in frozen['order']:
            row = {**cell, **client.request_once(frozen['observations'][cell['task_id']], cell)}
            rows.append(row)
            stream.write((json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n').encode())
            stream.flush()
            print(json.dumps({'completed': len(rows), 'planned': 24, 'calls': client.calls}), flush=True)
    write_json(output, {'version': VERSION, 'backend': 'deepseek_live_single_decision',
                        'protocol': pp.name, 'protocol_sha256': sha(pp), 'trace': tp.name,
                        'trace_sha256': sha(tp), 'summary': summarize(rows)})
    return summarize(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', type=Path)
    parser.add_argument('--protocol', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.freeze is not None and args.protocol is None and args.output is None:
        write_json(args.freeze, protocol())
    elif args.freeze is None and args.protocol is not None and args.output is not None:
        print(json.dumps(live(args.protocol, args.output)))
    else:
        parser.error('choose --freeze or --protocol with --output')
