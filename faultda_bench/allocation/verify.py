import argparse
import json
import tempfile
from pathlib import Path

from ..acceptance.audit import pinned_path, require
from ..evidence.core import tasks
from ..semantic.tasks import REPO, sha
from . import VERSION
from .suite import code_hashes, execute, order, summarize


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def verify(report):
    report = Path(report).resolve()
    result = json.loads(report.read_text(encoding='utf-8'))
    protocol_path = pinned_path(report.parent, result['protocol'])
    trace_path = pinned_path(report.parent, result['trace'])
    require(sha(protocol_path) == result['protocol_sha256'] and sha(trace_path) == result['trace_sha256'], 'artifact hash')
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    require(result['version'] == protocol['version'] == VERSION, 'version')
    require(same(protocol['order'], order()) and same(protocol['tasks'], tasks()), 'frozen design')
    require(same(protocol['code_sha256'], code_hashes()), 'code coverage or hash')
    require(protocol['api_requests'] == 0, 'no API')
    expected_sources = {t['source_path']: t['source_sha256'] for t in tasks()}
    require(same(protocol['source_sha256'], expected_sources), 'source coverage')
    for name, checksum in expected_sources.items():
        require(sha(pinned_path(REPO, name)) == checksum, 'source hash')
    rows = [json.loads(line) for line in trace_path.read_text(encoding='utf-8').splitlines()]
    require(len(rows) == len(protocol['order']), 'coverage')
    mapping = {t['id']: t for t in tasks()}
    with tempfile.TemporaryDirectory(prefix='faultda_allocation_replay_') as folder:
        for i, (row, cell) in enumerate(zip(rows, protocol['order'])):
            replayed = execute(mapping[cell['task_id']], Path(folder) / str(i), cell)
            require(same(row, replayed), 'full replay mismatch: ' + str(i))
    require(same(summarize(rows), result['summary']), 'summary')
    return {'version': VERSION, 'executions': len(rows), 'replayed': True, 'status': 'verified', 'api_requests': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    print(json.dumps(verify(parser.parse_args().report)))
