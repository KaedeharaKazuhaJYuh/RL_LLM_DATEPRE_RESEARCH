"""Preserve all old evidence and verify offline probe qualification only."""
import argparse
import json
from pathlib import Path
from . import VERSION, suite as s, review
from ..postreceipt385.audit import audit as previous
from ..acceptance.audit import pinned_path, digest
from ..multistep.suite import require

CATALOG = s.REPO/'faultda_bench/protocols/acceptance_v35.json'


def check_inventory(root=s.REPO,catalog_path=CATALOG):
    root = Path(root); c = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    old = json.loads((root/'faultda_bench/protocols/acceptance_v34.json').read_text(encoding='utf-8'))
    require(c['version'] == VERSION and c['scientific_gate'] == 'HOLD','scope')
    require(c['new_experiments'] == ['probes_v37'] and c['new_experiments_human_reviewed'] is False,'review scope')
    require(all(c['files'].get(n) == h for n,h in old['files'].items()),'historical preservation')
    for n,h in c['files'].items():
        p = pinned_path(root,n); require(p.is_file() and digest(p.read_bytes()) == h,'changed evidence: '+n)
    return {'files_verified':len(c['files']),'catalog_sha256':digest(Path(catalog_path).read_bytes())}


def audit():
    inventory = check_inventory(); result = previous()
    result['previous_release_version'] = result['version']; result['version'] = VERSION
    result['checks']['probes_v37'] = s.verify(); result['checks']['probes_v37_review'] = review.verify()
    decision = json.loads((s.REPO/'faultda_bench/reports/PROBES_0390_GO_NO_GO.json').read_text(encoding='utf-8'))
    require(decision['decision'] == 'NO_GO_LIVE' and decision['approved_transport_requests'] == 0,'no live approval')
    require(decision['offline_sha256'] == s.old.sha(s.OUTPUT) and decision['draft_sha256'] == s.old.sha(s.PLAN),'decision inputs')
    require(decision['independent_review'] == 'pending' and decision['scientific_gate'] == 'HOLD','review boundary')
    result['new_experiment_review']['probes_v37'] = 'pending'; result.update(inventory); return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--output',type=Path); a = p.parse_args(); data = audit()
    if a.output:
        from ..clarity.tasks import write_json
        write_json(a.output,data)
    print(json.dumps(data,ensure_ascii=False,indent=2))
