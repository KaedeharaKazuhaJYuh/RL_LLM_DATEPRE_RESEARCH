"""Verify frozen terminal files before optionally replaying existing native scores."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from . import native_replay185


BINDING = Path(__file__).parent / 'evidence/closeout-2026-10-27/TERMINAL_BINDING.json'


def verify(native_root: Path, binding_path: Path = BINDING) -> dict:
    binding_bytes = binding_path.read_bytes()
    binding = json.loads(binding_bytes)
    root = native_root.resolve()
    if [arm['arm'] for arm in binding['arms']] != list(native_replay185.ARMS):
        raise ValueError('Unexpected frozen terminal arms')
    checked = 0
    for arm in binding['arms']:
        files = arm['files']
        tree = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        if tree != arm['tree_sha256']:
            raise ValueError('Terminal manifest tree digest mismatch')
        directory = (root / arm['task_directory']).resolve()
        if not directory.is_relative_to(root) or not directory.is_dir():
            raise ValueError('Frozen terminal directory missing or outside native root')
        expected = {row['relative_path'] for row in files}
        actual = {p.relative_to(root).as_posix() for p in directory.rglob('*') if p.is_file()}
        if len(expected) != len(files) or actual != expected:
            raise ValueError('Frozen terminal file membership mismatch')
        for row in files:
            path = (root / row['relative_path']).resolve()
            if not path.is_relative_to(directory):
                raise ValueError('Terminal file outside recorded task directory')
            data = path.read_bytes()
            if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError('Frozen terminal file digest mismatch')
            checked += 1
    return {'binding_date': binding['date'], 'verified_task_output_files': checked,
            'terminal_binding_sha256': hashlib.sha256(binding_bytes).hexdigest(),
            'matches_terminal_binding': True, 'new_native_scorer_calls': 0,
            'new_model_api_calls': 0}


def replay(native_python: Path, native_root: Path, binding_path: Path = BINDING) -> dict:
    result = verify(native_root, binding_path)
    result['native_replay'] = native_replay185.replay(native_python, native_root)
    result['new_native_scorer_calls'] = len(native_replay185.ARMS)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native_root', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--native-python', type=Path,
                        help='Also replay existing scores in isolated native processes; default only hashes files')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Refusing to overwrite a terminal binding check')
    result = (replay(args.native_python, args.native_root) if args.native_python
              else verify(args.native_root))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print('Frozen terminal files verified; native scorer calls:', result['new_native_scorer_calls'])


if __name__ == '__main__':
    main()
