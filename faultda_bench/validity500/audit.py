"""Additive validity annotations do not modify scientific or human acceptance."""
import argparse
import json
from pathlib import Path
from . import VERSION, suite as s
from ..coherent395.audit import audit as previous
from ..acceptance.audit import pinned_path, digest
from ..multistep.suite import require

CATALOG = s.REPO/'faultda_bench/protocols/acceptance_v37.json'


def check_inventory(root=s.REPO,catalog_path=CATALOG):
    root = Path(root); c = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    old = json.loads((root/'faultda_bench/protocols/acceptance_v36.json').read_text(encoding='utf-8'))
    require(c['version']==VERSION and c['scientific_gate']=='HOLD','scope')
    require(c['new_experiments']==['validity_v39'] and c['new_experiments_human_reviewed'] is False,'review scope')
    require(all(c['files'].get(n)==h for n,h in old['files'].items()),'historical preservation')
    for n,h in c['files'].items():
        path = pinned_path(root,n); require(path.is_file() and digest(path.read_bytes())==h,'changed evidence: '+n)
    return {'files_verified':len(c['files']),'catalog_sha256':digest(Path(catalog_path).read_bytes())}


def audit():
    inventory = check_inventory(); result = previous(); result['previous_release_version'] = result['version']; result['version'] = VERSION
    result['checks']['validity_v39'] = s.verify()
    from . import review
    result['checks']['validity_v39_review'] = review.verify()
    decision = json.loads((s.REPO/'faultda_bench/reports/VALIDITY_0500_GO_NO_GO.json').read_text(encoding='utf-8'))
    require(decision['decision']=='NO_GO_LIVE' and decision['approved_transport_requests']==0,'no new live approval')
    require(decision['source_live_sha256']==s.source.sha(s.pilot.LIVE) and decision['claims_sha256']==s.source.sha(s.CLAIMS),'decision evidence')
    require(decision['independent_review']=='pending' and decision['scientific_gate']=='HOLD','review boundary')
    result['new_experiment_review']['validity_v39'] = 'pending'; result.update(inventory); return result


if __name__ == '__main__':
    cli = argparse.ArgumentParser(); cli.add_argument('--output',type=Path); args = cli.parse_args(); data = audit()
    if args.output:
        from ..clarity.tasks import write_json
        write_json(args.output,data)
    print(json.dumps(data,ensure_ascii=False,indent=2))
