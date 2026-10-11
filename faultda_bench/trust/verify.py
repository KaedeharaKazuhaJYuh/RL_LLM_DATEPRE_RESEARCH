import argparse
import json
import tempfile
from pathlib import Path

from ..acceptance.audit import pinned_path, require
from ..semantic.tasks import REPO, sha
from .suite import execute, protocol, summarize
from . import VERSION


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def verify(report):
    report = Path(report).resolve()
    result = json.loads(report.read_text(encoding='utf-8'))
    pp, tp = (pinned_path(report.parent, result[k]) for k in ('protocol', 'trace'))
    require(result['version'] == VERSION, 'version')
    require(sha(pp) == result['protocol_sha256'] and sha(tp) == result['trace_sha256'], 'artifact hash')
    frozen = json.loads(pp.read_text(encoding='utf-8'))
    require(same(frozen, protocol()), 'complete frozen design and code hash coverage')
    for name, checksum in frozen['source_sha256'].items():
        require(sha(pinned_path(REPO, name)) == checksum, 'source hash')
    rows = [json.loads(line) for line in tp.read_text(encoding='utf-8').splitlines()]
    require(len(rows) == len(frozen['order']), 'case coverage')
    mapping = {t['id']: t for t in frozen['tasks']}
    with tempfile.TemporaryDirectory(prefix='faultda_trust_replay_') as folder:
        for i, (row, cell) in enumerate(zip(rows, frozen['order'])):
            require(same(row, execute(mapping[cell['task_id']], Path(folder) / str(i), cell)),
                    'full effect replay: ' + str(i))
    require(same(result['summary'], summarize(rows)), 'summary')
    return {'version': VERSION, 'executions': len(rows), 'replayed': True, 'status': 'verified', 'api_requests': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    print(json.dumps(verify(parser.parse_args().report)))
