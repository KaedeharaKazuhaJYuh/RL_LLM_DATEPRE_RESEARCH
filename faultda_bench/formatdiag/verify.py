"""Rebuild requests and validate sanitized receipts without network calls."""
import argparse
import json
import math
from pathlib import Path

from . import VERSION
from .core import body, sha_bytes, summarize
from .suite import protocol
from ..pilot.contract import valid_decision
from ..semantic.tasks import sha


def require(condition, message):
    if not condition:
        raise ValueError(message)


def same(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def verify(path):
    path = Path(path)
    result = json.loads(path.read_text(encoding='utf-8'))
    pp, tp = path.with_suffix('.protocol.json'), path.with_suffix('.jsonl')
    require(result['version'] == VERSION and result['backend'] == 'deepseek_live_single_decision', 'provenance')
    require(result['protocol'] == pp.name and result['trace'] == tp.name, 'artifact names')
    require(sha(pp) == result['protocol_sha256'] and sha(tp) == result['trace_sha256'], 'artifact hash')
    frozen = json.loads(pp.read_text(encoding='utf-8'))
    require(same(frozen, protocol()), 'frozen protocol')
    rows = [json.loads(x) for x in tp.read_text(encoding='utf-8').splitlines()]
    require(len(rows) == 24, 'coverage')
    allowed = {'valid_action', 'empty_content', 'json_error', 'schema_error', 'response_shape', 'provider_error', 'input_limit', 'request_cap'}
    for row, cell in zip(rows, frozen['order']):
        require(same({k: row[k] for k in cell}, cell), 'paired cell/order')
        payload = json.dumps(body(frozen['observations'][cell['task_id']], cell), ensure_ascii=False, allow_nan=False).encode('utf-8')
        require(row['request_sha256'] == sha_bytes(payload) and type(row['request_bytes']) is int
                and row['request_bytes'] == len(payload), 'request rebuild')
        require(type(row['request_sent']) is bool and row['category'] in allowed, 'receipt shape')
        if row['request_sent']:
            require(type(row['seconds']) in (int, float) and math.isfinite(row['seconds']) and row['seconds'] >= 0, 'time')
        if row['category'] not in ('provider_error', 'input_limit', 'request_cap'):
            require(type(row['length_finish']) is bool and row['length_finish'] == (row['finish_reason'] == 'length'), 'finish metadata')
            require((row['category'] == 'valid_action') == valid_decision(row['decision']), 'decision schema')
            if row['category'] != 'valid_action':
                require(row['decision'] is None, 'failed output must not become an action')
            for key in ('content_bytes', 'reasoning_bytes'):
                require(row[key] is None or (type(row[key]) is int and row[key] >= 0), 'byte counts')
    require(same(result['summary'], summarize(rows)), 'summary')
    require(result['summary']['request_attempts'] <= 24, 'cap')
    return {'version': VERSION, 'executions': 24, 'status': 'verified', 'requests_rebuilt': True,
            'response_classification_independently_replayed': False, 'provider_authenticity_verified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    print(json.dumps(verify(parser.parse_args().report)))
