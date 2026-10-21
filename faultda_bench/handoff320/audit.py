"""Preserve every prior inventory and replay the actual revised-record handoff."""
import argparse
import json
from pathlib import Path

from . import VERSION
from .suite import verify
from ..feedback315.audit import audit as previous
from ..acceptance.audit import digest, pinned_path
from ..semantic.tasks import REPO
from ..multistep.suite import require

CATALOG = REPO/'faultda_bench/protocols/acceptance_v23.json'


def check_inventory(root=REPO, catalog_path=CATALOG):
    root = Path(root); catalog = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    old = json.loads((root/'faultda_bench/protocols/acceptance_v22.json').read_text(encoding='utf-8'))
    require(catalog['version'] == VERSION and catalog['scientific_gate'] == 'HOLD', 'release scope')
    require(catalog['new_experiments'] == ['handoff_v25'] and catalog['new_experiments_human_reviewed'] is False, 'new scope and review')
    require(all(catalog['files'].get(n) == h for n, h in old['files'].items()), 'historical hashes')
    for n, h in catalog['files'].items():
        p = pinned_path(root, n); require(p.is_file() and digest(p.read_bytes()) == h, 'changed evidence: '+n)
    return {'files_verified': len(catalog['files']), 'catalog_sha256': digest(Path(catalog_path).read_bytes())}


def audit():
    inventory = check_inventory(); result = previous()
    result['previous_release_version'] = result['version']; result['version'] = VERSION
    result['checks']['handoff_v25'] = verify(REPO/'faultda_bench/reports/handoff_v25_deepseek.json')
    from .analysis import verify as verify_accounting
    result['checks']['handoff_v25_accounting'] = verify_accounting()
    result['new_experiment_review']['handoff_v25'] = 'pending'; result.update(inventory)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path); a = p.parse_args()
    data = (json.dumps(audit(), ensure_ascii=False, indent=2)+'\n').encode()
    if a.output:
        with a.output.open('xb') as stream: stream.write(data)
    print(data.decode(), end='')
