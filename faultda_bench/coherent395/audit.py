"""Additive source/ledger and actual paired-response replay; science remains HOLD."""
import argparse
import json
from pathlib import Path
from . import VERSION, suite as s, pilot as p
from ..probes390.audit import audit as previous
from ..acceptance.audit import pinned_path, digest
from ..multistep.suite import require, same

CATALOG = s.REPO/'faultda_bench/protocols/acceptance_v36.json'


def check_inventory(root=s.REPO,catalog_path=CATALOG):
    root = Path(root); c = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    old = json.loads((root/'faultda_bench/protocols/acceptance_v35.json').read_text(encoding='utf-8'))
    require(c['version']==VERSION and c['scientific_gate']=='HOLD','scope')
    require(c['new_experiments']==['coherent_v38'] and c['new_experiments_human_reviewed'] is False,'review scope')
    require(all(c['files'].get(n)==h for n,h in old['files'].items()),'historical preservation')
    for n,h in c['files'].items():
        path = pinned_path(root,n); require(path.is_file() and digest(path.read_bytes())==h,'changed evidence: '+n)
    return {'files_verified':len(c['files']),'catalog_sha256':digest(Path(catalog_path).read_bytes())}


def audit():
    inventory = check_inventory(); result = previous(); result['previous_release_version'] = result['version']; result['version'] = VERSION
    result['checks']['coherent_v38_environment'] = s.verify()
    require(same(json.loads(p.PLAN.read_text(encoding='utf-8')),p.protocol()),'prospective paired protocol')
    result['checks']['coherent_v38_dry'] = p.verify(p.DRY); result['checks']['coherent_v38_live'] = p.verify(p.LIVE)
    from . import analysis, review
    result['checks']['coherent_v38_accounting'] = analysis.verify(); result['checks']['coherent_v38_review'] = review.verify()
    go = json.loads(p.GO.read_text(encoding='utf-8'))
    require(go['decision']=='GO_bounded_paired_diagnostic' and go['max_transport_requests']==24,'bounded engineering GO')
    require(go['plan_sha256']==s.sha(p.PLAN) and go['dry_sha256']==s.sha(p.DRY) and go['source_sha256']==s.sha(s.OUTPUT),'GO inputs')
    require(go['independent_review']=='pending' and go['scientific_gate']=='HOLD','review scope unchanged')
    result['new_experiment_review']['coherent_v38'] = 'pending'; result.update(inventory); return result


if __name__ == '__main__':
    cli = argparse.ArgumentParser(); cli.add_argument('--output',type=Path); args = cli.parse_args(); data = audit()
    if args.output:
        from ..clarity.tasks import write_json
        write_json(args.output,data)
    print(json.dumps(data,ensure_ascii=False,indent=2))
