"""Additive unified acceptance; no supplier or independent identity authentication."""
import argparse
import json
from pathlib import Path
from . import VERSION
from . import suite as s
from . import review
from ..receipt380.audit import audit as previous
from ..acceptance.audit import pinned_path, digest
from ..multistep.suite import require, same

CATALOG = s.REPO/'faultda_bench/protocols/acceptance_v34.json'


def check_inventory(root=s.REPO,catalog_path=CATALOG):
    root = Path(root); c = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    old = json.loads((root/'faultda_bench/protocols/acceptance_v33.json').read_text(encoding='utf-8'))
    require(c['version'] == VERSION and c['scientific_gate'] == 'HOLD','scope')
    require(c['new_experiments'] == ['postreceipt_v36'] and c['new_experiments_human_reviewed'] is False,'review scope')
    require(all(c['files'].get(n) == h for n,h in old['files'].items()),'historical preservation')
    for n,h in c['files'].items():
        p = pinned_path(root,n); require(p.is_file() and digest(p.read_bytes()) == h,'changed evidence: '+n)
    return {'files_verified':len(c['files']),'catalog_sha256':digest(Path(catalog_path).read_bytes())}


def audit():
    inventory = check_inventory(); result = previous()
    result['previous_release_version'] = result['version']; result['version'] = VERSION
    require(same(json.loads(s.OFFLINE.read_text(encoding='utf-8')),s.offline()),'all-four offline references')
    require(same(json.loads(s.PLAN.read_text(encoding='utf-8')),s.protocol()),'frozen prospective plan')
    for name,path in [('postreceipt_v36',s.LIVE),('postreceipt_v36_dry',s.DRY)]:result['checks'][name] = s.verify(path)
    result['checks']['postreceipt_v36_review'] = review.verify()
    from .analysis import verify as verify_accounting
    result['checks']['postreceipt_v36_accounting'] = verify_accounting()
    go = json.loads(s.GO.read_text(encoding='utf-8'))
    require(go['decision'] == 'GO_bounded_diagnostic' and go['max_transport_requests'] == 4,'bounded GO')
    require(go['plan_sha256'] == s.sha(s.PLAN) and go['dry_sha256'] == s.sha(s.DRY) and go['offline_sha256'] == s.sha(s.OFFLINE),'GO inputs')
    require(go['scientific_gate'] == 'HOLD' and go['independent_review'] == 'pending','review pending')
    result['new_experiment_review']['postreceipt_v36'] = 'pending'; result.update(inventory); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output',type=Path); a = p.parse_args()
    data = audit()
    if a.output:
        from ..clarity.tasks import write_json
        write_json(a.output,data)
    print(json.dumps(data,ensure_ascii=False,indent=2))
