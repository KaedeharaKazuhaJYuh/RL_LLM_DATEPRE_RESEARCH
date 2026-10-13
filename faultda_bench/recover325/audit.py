"""Additive acceptance; program controls cannot certify model improvement."""
import argparse
import json
from pathlib import Path
from . import VERSION
from .suite import verify
from ..handoff320.audit import audit as previous
from ..acceptance.audit import digest, pinned_path
from ..semantic.tasks import REPO
from ..multistep.suite import require

CATALOG = REPO/'faultda_bench/protocols/acceptance_v24.json'


def check_inventory(root=REPO, catalog_path=CATALOG):
    root = Path(root); c = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    old = json.loads((root/'faultda_bench/protocols/acceptance_v23.json').read_text(encoding='utf-8'))
    require(c['version'] == VERSION and c['scientific_gate'] == 'HOLD', 'release scope')
    require(c['new_experiments'] == ['recover_v26'] and c['new_experiments_human_reviewed'] is False, 'scope and review')
    require(all(c['files'].get(n) == h for n, h in old['files'].items()), 'historical scope')
    for n, h in c['files'].items():
        p = pinned_path(root, n); require(p.is_file() and digest(p.read_bytes()) == h, 'changed evidence: '+n)
    return {'files_verified': len(c['files']), 'catalog_sha256': digest(Path(catalog_path).read_bytes())}


def audit():
    inventory = check_inventory(); result = previous()
    result['previous_release_version'] = result['version']; result['version'] = VERSION
    result['checks']['recover_v26'] = verify()
    result['new_experiment_review']['recover_v26'] = 'pending'; result.update(inventory)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path); a = p.parse_args()
    data = (json.dumps(audit(), ensure_ascii=False, indent=2)+'\n').encode()
    if a.output:
        with a.output.open('xb') as stream: stream.write(data)
    print(data.decode(), end='')
