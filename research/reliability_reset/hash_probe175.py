"""Isolate public AppWorld comparison functions; this is not a task evaluator.

The adapters supply synthetic rows and content labels, not an actual ORM, hash
implementation, API, database, task contract or native task score.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any


FIXTURES = Path(__file__).with_name('fixtures')


def load_functions(fixture_bytes: bytes | None = None) -> dict[str, Any]:
    metadata = json.loads((FIXTURES / 'appworld_175_source.json').read_text(encoding='utf-8'))
    data = fixture_bytes if fixture_bytes is not None else (FIXTURES / metadata['fixture']).read_bytes()
    if hashlib.sha256(data).hexdigest() != metadata['fixture_sha256']:
        raise ValueError('Public-source excerpt does not match the recorded digest')
    module = ast.parse(data.decode('utf-8'))
    expected = {'_validate_model_name', '_changed_model_names', '_changed_records', 'set_record_hash'}
    functions = {n.name: n for n in module.body if isinstance(n, ast.FunctionDef)}
    if set(functions) != expected:
        raise ValueError('Unexpected public-source function selection')

    def canonical_modelize(name: str) -> str:
        if name != 'Item':
            raise ValueError('Diagnostic adapter supports the canonical Item name only')
        return name

    # Keep the function bodies unchanged. Only database/naming boundaries are
    # supplied here; set_record_hash is inspected as AST and never executed.
    selected = ast.Module(body=[
        ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0),
        *(functions[n] for n in ('_validate_model_name', '_changed_model_names', '_changed_records')),
    ], type_ignores=[])
    ast.fix_missing_locations(selected)
    namespace: dict[str, Any] = {'defaultdict': defaultdict, 'modelize': canonical_modelize}
    exec(compile(selected, '<pinned-public-AppWorld-comparison-excerpt>', 'exec'), namespace)
    skips = [ast.literal_eval(keyword.value)
             for node in ast.walk(functions['set_record_hash']) if isinstance(node, ast.Call)
             for keyword in node.keywords if keyword.arg == 'skip']
    namespace['hash_omits_id_source_fact'] = any('id' in skip for skip in skips)
    return namespace


@dataclass(frozen=True)
class OpaqueRow:
    id: int
    record_hash: str


class Table:
    def __init__(self, rows: list[OpaqueRow]):
        self.rows = rows

    def size(self) -> int:
        return len(self.rows)

    def by_ids(self, ids: set[int] | list[int]) -> list[OpaqueRow]:
        return [row for row in self.rows if row.id in ids]


class AppView(SimpleNamespace):
    def __getitem__(self, name: str) -> Any:
        return getattr(self, name)


class Snapshot:
    def __init__(self, values: tuple[tuple[int, str], ...], mutation_counter: int):
        self.rows = [OpaqueRow(*value) for value in values]
        if len({row.id for row in self.rows}) != len(self.rows):
            raise ValueError('A synthetic primary key must be unique')
        self.mutation_counter = mutation_counter
        self.app = AppView(
            SQLModel=SimpleNamespace(model_names=lambda: ['Item']),
            Item=Table(self.rows),
        )

    def keys(self) -> list[str]:
        return ['probe']

    def __getitem__(self, name: str) -> Any:
        if name != 'probe':
            raise ValueError('Unexpected synthetic application')
        return self.app

    def model_hashes(self) -> dict[str, int]:
        return {'probe.Item': self.mutation_counter}

    def ids(self, app: str, model: str) -> set[int]:
        return {row.id for row in self.rows}

    def ids_record_hashes(self, app: str, model: str) -> list[tuple[int, str]]:
        return [(row.id, row.record_hash) for row in self.rows]

    def record_hashes(self, app: str, model: str) -> set[str]:
        return {row.record_hash for row in self.rows}


CASES = (
    ('unchanged_content', ((1, 'a'), (2, 'b')), ((1, 'a'), (2, 'b'))),
    ('ordinary_content_update', ((1, 'a'), (2, 'b')), ((1, 'a'), (2, 'c'))),
    ('ordinary_addition', ((1, 'a'), (2, 'b')), ((1, 'a'), (2, 'b'), (3, 'c'))),
    ('ordinary_removal', ((1, 'a'), (2, 'b')), ((1, 'a'),)),
    ('same_content_recreated_id', ((1, 'a'), (2, 'b')), ((1, 'a'), (3, 'b'))),
    ('content_permuted_across_ids', ((1, 'a'), (2, 'b')), ((1, 'b'), (2, 'a'))),
    ('duplicate_multiplicity_redistributed', ((1, 'a'), (2, 'a'), (3, 'b')),
     ((1, 'a'), (2, 'b'), (3, 'b'))),
    ('duplicate_added_changes_size', ((1, 'a'), (2, 'b')), ((1, 'a'), (2, 'b'), (3, 'b'))),
)


def probe() -> dict[str, Any]:
    functions = load_functions()
    rows = []
    for name, before, after in CASES:
        # Deliberately different mutation counters exercise the native detailed
        # comparison rather than an equal-counter early return.
        pair = SimpleNamespace(start=Snapshot(before, 1), end=Snapshot(after, 2))
        changed = functions['_changed_model_names'](pair)
        added, updated, removed = functions['_changed_records'](pair, 'probe.Item')
        old_by_id, new_by_id = dict(before), dict(after)
        content_equal = Counter(v for _, v in before) == Counter(v for _, v in after)
        identity_equal = old_by_id == new_by_id
        rows.append({
            'case': name, 'start': list(before), 'end': list(after),
            'native_helper_changed_models': sorted(changed),
            'native_helper_added_ids': [row.id for row in added],
            'native_helper_updated_ids': [row.id for row in updated],
            'native_helper_removed_ids': [row.id for row in removed],
            'reference_content_multiset_equal': content_equal,
            'reference_identity_map_equal': identity_equal,
            'helper_misses_content_multiset_change': not content_equal and not changed
                and not added and not updated and not removed,
        })
    return {
        'version': '1.0.75', 'date': '2026-10-26',
        'upstream_commit': '42b5bcf3cd334fee33f0c37c02070a9f5807add5',
        'kind': 'Isolated synthetic software reproduction of unchanged public helper functions',
        'hash_omits_id_source_fact': functions['hash_omits_id_source_fact'],
        'adapters': ['Synthetic in-memory rows, no ORM or database',
                     'Opaque content labels, not actual xxhash values',
                     'Canonical Item naming only',
                     'Different mutation counters force the detailed comparison'],
        'cases': rows,
        'counts': {'synthetic_software_cases': len(rows), 'real_tasks': 0,
                   'native_task_scorer_runs': 0, 'AppWorld_environment_runs': 0,
                   'new_model_api_calls': 0},
        'decision': 'Content-multiplicity blind spot reproduced at helper boundary; real native-task false success remains unconfirmed.',
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = probe()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'software_cases': len(result['cases']), 'missed_multiset_cases':
                      sum(row['helper_misses_content_multiset_change'] for row in result['cases']),
                      'real_tasks': 0, 'model_calls': 0}))


if __name__ == '__main__':
    main()
