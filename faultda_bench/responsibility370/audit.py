"""Additive offline responsibility evidence, without independent acceptance claims."""
import argparse
import json
from pathlib import Path
from . import VERSION
from .suite import verify
from ..goal365.audit import audit as previous
from ..acceptance.audit import digest,pinned_path
from ..semantic.tasks import REPO
from ..multistep.suite import require

CATALOG=REPO/'faultda_bench/protocols/acceptance_v31.json'


def check_inventory(root=REPO,catalog_path=CATALOG):
    root=Path(root);c=json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    old=json.loads((root/'faultda_bench/protocols/acceptance_v30.json').read_text(encoding='utf-8'))
    require(c['version']==VERSION and c['scientific_gate']=='HOLD','scope')
    require(c['new_experiments']==['responsibility_v33'] and c['new_experiments_human_reviewed'] is False,'review scope')
    require(all(c['files'].get(n)==h for n,h in old['files'].items()),'historical preservation')
    for n,h in c['files'].items():
        p=pinned_path(root,n);require(p.is_file() and digest(p.read_bytes())==h,'changed evidence: '+n)
    return {'files_verified':len(c['files']),'catalog_sha256':digest(Path(catalog_path).read_bytes())}


def audit():
    inventory=check_inventory();result=previous()
    result['previous_release_version']=result['version'];result['version']=VERSION
    result['checks']['responsibility_v33']=verify()
    decision=json.loads((REPO/'faultda_bench/reports/RESPONSIBILITY_0370_GO_NO_GO.json').read_text(encoding='utf-8'))
    require(decision['decision']=='NO-GO' and decision['budget']['max_transport_requests']==0 and decision['actual_new_provider_requests']==0,'zero-budget no-go')
    require(decision['scientific_gate']=='HOLD' and decision['independent_scientific_review']=='pending','scientific review boundary')
    result['checks']['responsibility_v33_live_decision']={'status':'verified','decision':'NO-GO','new_provider_requests':0}
    result['new_experiment_review']['responsibility_v33']='pending';result.update(inventory);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
    data=(json.dumps(audit(),ensure_ascii=False,indent=2)+'\n').encode()
    if a.output:
        with a.output.open('xb') as stream:stream.write(data)
    print(data.decode(),end='')
