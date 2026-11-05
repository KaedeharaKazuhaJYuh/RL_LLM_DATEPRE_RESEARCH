"""One source-bound native start-state preflight, not a native task evaluator.

The protected input remains local. Output contains aggregate counts and file
digests, never instructions, answers, API arguments, rows or per-table results.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, cast
import zipfile


PIN = '42b5bcf3cd334fee33f0c37c02070a9f5807add5'
ZIP_SHA256 = 'f029a84ad87749864be93c4aec0e8c309b119d129847a59ad4dccab15be7f9cf'
FIXTURES = Path(__file__).with_name('fixtures')
APPS = ('admin', 'amazon', 'api_docs', 'file_system', 'gmail', 'phone',
        'simple_note', 'splitwise', 'spotify', 'supervisor', 'todoist', 'venmo')


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_apply_changes(fixture_bytes: bytes | None = None) -> Any:
    """Compile the unchanged public SQL replay function with boundary imports."""
    metadata = json.loads((FIXTURES / 'appworld_180_source.json').read_text(encoding='utf-8'))
    data = fixture_bytes if fixture_bytes is not None else (FIXTURES / metadata['fixture']).read_bytes()
    if _digest(data) != metadata['fixture_sha256']:
        raise ValueError('Public SQL replay excerpt digest mismatch')
    module = ast.parse(data)
    funcs = [n for n in module.body if isinstance(n, ast.FunctionDef)]
    if len(funcs) != 1 or funcs[0].name != 'apply_db_changes':
        raise ValueError('Unexpected public function selection')

    def read_jsonl(path: str, *, use_json_plus: bool) -> list[Any]:
        if use_json_plus:
            raise ValueError('Only upstream plain JSONL mode is supported')
        return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines()
                if line.strip()]

    namespace = {'os': os, 'cast': cast, 'SQLite3Connection': sqlite3.Connection,
                 'Change': tuple, 'read_jsonl': read_jsonl}
    selected = ast.Module(body=[ast.ImportFrom(module='__future__',
        names=[ast.alias(name='annotations')], level=0), funcs[0]], type_ignores=[])
    ast.fix_missing_locations(selected)
    exec(compile(selected, '<pinned-public-AppWorld-SQL-replay>', 'exec'), namespace)
    return namespace['apply_db_changes']


def inspect_hashes(connection: sqlite3.Connection) -> dict[str, int]:
    """Inspect stored hashes, without publishing hash values or recomputing ORM hashes."""
    result = {'hash_tables': 0, 'rows': 0, 'duplicate_groups': 0, 'invalid_hash_rows': 0}
    tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    for (name,) in tables:
        quoted = '"' + name.replace('"', '""') + '"'
        columns = [r[1] for r in connection.execute('PRAGMA table_info(' + quoted + ')')]
        if 'record_hash' not in columns:
            continue  # Includes SQLite/FTS bookkeeping, not a silent model exclusion.
        hashes = Counter(r[0] for r in connection.execute('SELECT record_hash FROM ' + quoted))
        result['hash_tables'] += 1
        result['rows'] += sum(hashes.values())
        result['duplicate_groups'] += sum(count > 1 for count in hashes.values())
        result['invalid_hash_rows'] += sum(count for value, count in hashes.items()
                                           if not isinstance(value, str) or not value)
    if not result['hash_tables']:
        raise ValueError('No record_hash tables; cannot establish the start-state premise')
    return result


def preflight(zip_path: Path, local_case_root: Path) -> dict[str, Any]:
    """Read exactly one train task, all corresponding bases and original deltas.

    local_case_root must already hold the selected task's original JSONL
    packet. Each delta is compared to its original archive member before SQL
    execution. No API server, ORM, hash generator or evaluator is imported.
    """
    data = zip_path.read_bytes()
    if _digest(data) != ZIP_SHA256:
        raise ValueError('Decrypted native package digest mismatch')
    replay = load_apply_changes()
    counts = dict.fromkeys(('hash_tables', 'rows', 'duplicate_groups', 'invalid_hash_rows'), 0)
    packet = []
    bases = []
    delta_statements = 0
    with zipfile.ZipFile(zip_path) as archive:
        if archive.read('data/version.txt').decode().strip() != '0.2.0':
            raise ValueError('Unexpected native data version')
        train = [line.strip() for line in archive.read('data/datasets/train.txt').decode().splitlines()
                 if line.strip()]
        task_id = train[0]  # Frozen selection before any task-specific inspection.
        if task_id != '82e2fac_1':
            raise ValueError('Frozen first-train selection changed')
        prefix = f'data/tasks/{task_id}/'
        names = sorted(n for n in archive.namelist() if n.startswith(prefix) and not n.endswith('/'))
        for name in names:
            raw = archive.read(name)
            packet.append({'path': name, 'bytes': len(raw), 'sha256': _digest(raw)})
        for app in APPS:
            base_name = f'data/base_dbs/{app}.db'
            base = archive.read(base_name)
            bases.append({'path': base_name, 'bytes': len(base), 'sha256': _digest(base)})
            delta_name = prefix + f'dbs/{app}.jsonl'
            delta_path = local_case_root / delta_name
            # Native helper silently permits missing delta files: the preflight
            # must reject that before calling it, including expected empty files.
            if delta_path.read_bytes() != archive.read(delta_name):
                raise ValueError('Original native task delta mismatch')
            connection = sqlite3.connect(':memory:')
            try:
                connection.deserialize(base)
                delta_statements += len(replay(connection, str(delta_path)))
                stats = inspect_hashes(connection)
                for key, value in stats.items():
                    counts[key] += value
            finally:
                connection.close()
    closed = counts['duplicate_groups'] == counts['invalid_hash_rows'] == 0
    return {
        'version': '1.0.80', 'date': '2026-10-26', 'upstream_commit': PIN,
        'kind': 'Native start-state preflight; no native full scorer or legal API execution',
        'selection': {'task_id': task_id, 'split': 'train',
                      'rule': 'First nonempty official train.txt entry, before task inspection'},
        'decrypted_package_sha256': ZIP_SHA256, 'data_version': '0.2.0',
        'original_task_packet': packet, 'original_base_databases': bases,
        'start_state': {'apps': len(APPS), 'native_delta_statements_replayed': delta_statements,
                        **counts, 'hash_generator_recomputed': False},
        'decision': 'CLOSE_MULTIPLICITY_CANDIDATE_FOR_SELECTED_START' if closed else 'UNRESOLVED_PREMISE',
        'execution_go_no_go': 'NO_GO_NOT_NEEDED_FOR_THIS_CANDIDATE' if closed else 'REVIEW_REQUIRED',
        'argument': 'If a start table has n distinct hashes and an end table has the same n rows '
                    'and the same set of hashes, every end hash occurs exactly once. Therefore '
                    'the hash multisets coincide. This excludes only the 1.0.75 multiplicity mechanism.',
        'assumptions': ['Stored hashes and the public comparison path are used as recorded',
                        'No hash collision, stale/tampered hash, identity-permutation or equal-counter claim is tested',
                        'Raw SQLite plus unchanged SQL replay is not full AppWorld environment reconstruction'],
        'counts': {'native_task_packets_inspected': 1, 'native_start_reconstructions': 1,
                   'native_task_scorer_runs': 0, 'AppWorld_environment_runs': 0,
                   'legal_tool_trajectories': 0, 'new_model_api_calls': 0,
                   'confirmed_native_false_successes': 0},
        'scientific_status': 'HOLD',
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decrypted_zip', type=Path)
    parser.add_argument('local_case_root', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Refusing to overwrite an existing preflight record')
    result = preflight(args.decrypted_zip, args.local_case_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(result['decision'])


if __name__ == '__main__':
    main()
