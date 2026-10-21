"""Explicit CI-only v48 migration; historical evidence and v46/v47 remain unchanged."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'faultda_bench/protocols/acceptance_v49_ci.json'
ARCHIVE = ROOT / 'faultda_bench/protocols/ci565_original_bytes.json'
V48_SHA = '855a6fdd6a5ed907033b44131624bfd80a1cd306e3fc122d79e74192634c8f40'
ARCHIVE_SHA = '57e37f1b1a3bc5eb6c822ef30fd0bc0fc892baf3209214a3d687c2c86d3f190d'
SOURCE_COMMIT = '5b7e2b5a78b2c479ce75877c39f5c12dd1de5b72'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def migration():
    if digest(ROOT / 'faultda_bench/protocols/acceptance_v48.json') != V48_SHA:
        raise ValueError('historical v48 catalog changed')
    if digest(ARCHIVE) != ARCHIVE_SHA:
        raise ValueError('historical CI source archive changed')
    record = json.loads(MANIFEST.read_text(encoding='utf-8'))
    originals = json.loads(ARCHIVE.read_text(encoding='utf-8'))
    if record['source_commit'] != SOURCE_COMMIT or originals['source_commit'] != SOURCE_COMMIT:
        raise ValueError('CI migration source mismatch')
    old = json.loads((ROOT / 'faultda_bench/protocols/acceptance_v48.json').read_text(encoding='utf-8'))
    if set(record['superseded']) != set(originals['files']):
        raise ValueError('unarchived CI correction')
    for name, entry in record['superseded'].items():
        raw = base64.b64decode(originals['files'][name], validate=True)
        if hashlib.sha256(raw).hexdigest() != old['files'][name] or entry['original_sha256'] != old['files'][name]:
            raise ValueError('original CI bytes do not match historical freeze: ' + name)
    return record


def effective_v48_digest(name, original):
    correction = migration()['superseded'].get(name)
    if correction is None:
        return original
    if correction['original_sha256'] != original:
        raise ValueError('unexpected original digest')
    return correction['corrected_sha256']


def verify_integration_paths(repo=ROOT):
    record = migration()
    for name, expected in record['integration_paths'].items():
        if hashlib.sha256((Path(repo) / name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != expected:
            raise ValueError('unregistered integration change: ' + name)
    return list(record['integration_paths'])


def audit():
    record = migration()
    v48 = json.loads((ROOT / 'faultda_bench/protocols/acceptance_v48.json').read_text(encoding='utf-8'))
    for name, expected in v48['files'].items():
        correction = record['superseded'].get(name)
        actual_expected = correction['corrected_sha256'] if correction else expected
        if digest(ROOT / name) != actual_expected:
            raise ValueError('v48 current evidence mismatch: ' + name)
    v47 = json.loads((ROOT / 'faultda_bench/protocols/acceptance_v47.json').read_text(encoding='utf-8'))
    for name, expected in v47['files'].items():
        if digest(ROOT / name) != expected:
            raise ValueError('v47 frozen bytes changed: ' + name)
    verify_integration_paths()
    for name, expected in record['files'].items():
        if digest(ROOT / name) != expected:
            raise ValueError('CI correction bytes changed: ' + name)
    return {'version': '0.5.65-dev', 'revision': 'ci-integration-1',
            'historical_v48_catalog_unchanged': True, 'v47_files_unchanged': len(v47['files']),
            'v48_current_or_archived_files_verified': len(v48['files']),
            'explicit_ci_corrections': len(record['superseded']), 'api_calls': 0,
            'scientific_gate': 'HOLD', 'experiment_outputs_changed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = json.dumps(audit(), ensure_ascii=False, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(result)
    print(result)
