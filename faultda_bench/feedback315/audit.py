"""Additive inventory and full response/action replay for this release."""
import argparse
import json
from pathlib import Path

from . import VERSION
from .suite import verify
from ..consistency310.audit import audit as previous
from ..acceptance.audit import pinned_path, digest
from ..semantic.tasks import REPO
from ..multistep.suite import require

CATALOG = REPO/'faultda_bench/protocols/acceptance_v22.json'


def check_inventory(root=REPO, catalog_path=CATALOG):
    root = Path(root); catalog = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    old = json.loads((root/'faultda_bench/protocols/acceptance_v21.json').read_text(encoding='utf-8'))
    require(catalog['version'] == VERSION and catalog['scientific_gate'] == 'HOLD', 'release scope')
    require(catalog['new_experiments'] == ['feedback_v24'] and catalog['new_experiments_human_reviewed'] is False, 'review scope')
    require(all(catalog['files'].get(n) == h for n, h in old['files'].items()), 'historical preservation')
    for name, checksum in catalog['files'].items():
        path = pinned_path(root, name)
        require(path.is_file() and digest(path.read_bytes()) == checksum, 'changed evidence: '+name)
    return {'files_verified': len(catalog['files']), 'catalog_sha256': digest(Path(catalog_path).read_bytes())}


def audit():
    inventory = check_inventory(); result = previous()
    result['previous_release_version'] = result['version']; result['version'] = VERSION
    result['checks']['feedback_v24'] = verify(REPO/'faultda_bench/reports/feedback_v24_deepseek.json')
    from .analysis import verify as verify_accounting
    result['checks']['feedback_v24_accounting'] = verify_accounting()
    result['new_experiment_review']['feedback_v24'] = 'pending'
    result.update(inventory)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path); a = p.parse_args()
    data = (json.dumps(audit(), ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    if a.output:
        with a.output.open('xb') as stream: stream.write(data)
    print(data.decode(), end='')
