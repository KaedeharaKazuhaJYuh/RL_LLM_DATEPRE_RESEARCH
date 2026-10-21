"""Additive engineering qualification, never independent scientific approval."""
import argparse
import json
from pathlib import Path
from . import VERSION
from .suite import verify
from ..recover325.audit import audit as previous
from ..semantic.tasks import REPO
from ..acceptance.audit import digest, pinned_path
from ..multistep.suite import require

CATALOG = REPO/'faultda_bench/protocols/acceptance_v25.json'


def check_inventory(root=REPO, catalog_path=CATALOG):
    root = Path(root); c = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    old = json.loads((root/'faultda_bench/protocols/acceptance_v24.json').read_text(encoding='utf-8'))
    require(c['version'] == VERSION and c['scientific_gate'] == 'HOLD', 'release scope')
    require(c['new_experiments'] == ['qualify_v27'] and c['new_experiments_human_reviewed'] is False, 'review scope')
    require(all(c['files'].get(n) == h for n, h in old['files'].items()), 'historical preservation')
    for n, h in c['files'].items():
        p = pinned_path(root, n); require(p.is_file() and digest(p.read_bytes()) == h, 'changed evidence: '+n)
    return {'files_verified': len(c['files']), 'catalog_sha256': digest(Path(catalog_path).read_bytes())}


def audit():
    inventory = check_inventory(); result = previous()
    result['previous_release_version'] = result['version']; result['version'] = VERSION
    result['checks']['qualify_v27'] = verify(); result['new_experiment_review']['qualify_v27'] = 'pending'
    result.update(inventory); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path); a = p.parse_args()
    data = (json.dumps(audit(), ensure_ascii=False, indent=2)+'\n').encode()
    if a.output:
        with a.output.open('xb') as stream: stream.write(data)
    print(data.decode(), end='')
