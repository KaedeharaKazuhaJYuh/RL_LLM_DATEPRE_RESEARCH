"""Additive offline acceptance, preserving both historical release inventories."""
import argparse
import json
from pathlib import Path

from . import VERSION
from ..release030 import audit as previous
from ..acceptance.audit import pinned_path, digest
from ..semantic.tasks import REPO
from ..multistep.suite import require

CATALOG=REPO/'faultda_bench/protocols/acceptance_v20.json'


def check_inventory(root=REPO,catalog_path=CATALOG):
    root=Path(root); catalog=json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    require(catalog['version']==VERSION,'release version')
    require(catalog['scientific_gate']=='HOLD','science is not an engineering check')
    old=json.loads((root/'faultda_bench/protocols/acceptance_v19.json').read_text(encoding='utf-8'))
    require(all(catalog['files'].get(n)==h for n,h in old['files'].items()),'historical hashes and scope')
    require(catalog['new_experiments']==['semantics_v22'],'new scope')
    require(catalog['new_experiments_human_reviewed'] is False,'cannot borrow historical human signatures')
    for name,checksum in catalog['files'].items():
        path=pinned_path(root,name)
        require(path.is_file() and digest(path.read_bytes())==checksum,'changed evidence: '+name)
    return {'files_verified':len(catalog['files']),'catalog_sha256':digest(Path(catalog_path).read_bytes()),
        'provider_authenticity_verified':False,'external_publication_confirmed':False}


def audit(full_replay=False):
    inventory=check_inventory(); result=previous.audit(full_replay)
    from .suite import verify
    result['checks']['semantics_v22_deepseek']=verify(REPO/'faultda_bench/reports/semantics_v22_deepseek.json')
    result['previous_release_version']=result['version']; result['version']=VERSION
    result['new_experiment_review']['semantics_v22']='pending'
    result.update(inventory)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--full-replay',action='store_true'); p.add_argument('--output',type=Path); a=p.parse_args()
    result=audit(a.full_replay); data=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
    if a.output:
        with a.output.open('xb') as stream: stream.write(data)
    print(data.decode(),end='')
