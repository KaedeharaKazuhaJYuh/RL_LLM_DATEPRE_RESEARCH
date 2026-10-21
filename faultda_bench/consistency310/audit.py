"""Additive acceptance of public consistency checks."""
import json
from . import VERSION
from .suite import verify
from ..semantics305.audit import audit as previous
from ..semantic.tasks import REPO, sha
from ..multistep.suite import require

def audit():
    catalog=json.loads((REPO/'faultda_bench/protocols/acceptance_v21.json').read_text())
    old=json.loads((REPO/'faultda_bench/protocols/acceptance_v20.json').read_text())
    require(catalog['version']==VERSION and catalog['scientific_gate']=='HOLD','release scope')
    require(all(catalog['files'].get(n)==h for n,h in old['files'].items()),'historical preservation')
    for n,h in catalog['files'].items(): require(sha(REPO/n)==h,'changed evidence: '+n)
    result=previous(); result['previous_release_version']=result['version']; result['version']=VERSION
    result['catalog_sha256']=sha(REPO/'faultda_bench/protocols/acceptance_v21.json')
    result['checks']['consistency_v23']=verify(); result['files_verified']=len(catalog['files'])
    result['new_experiment_review']['consistency_v23']='pending'
    return result

if __name__=='__main__':
    import argparse
    from pathlib import Path
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path); a=p.parse_args()
    data=json.dumps(audit(),ensure_ascii=False,indent=2)+'\n'
    if a.output:
        with a.output.open('x',encoding='utf-8') as stream: stream.write(data)
    print(data,end='')
