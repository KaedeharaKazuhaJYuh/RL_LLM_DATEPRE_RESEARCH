"""Offline unified acceptance for the completed 0.3.0-dev engineering version."""
import argparse
import json
from pathlib import Path

from . import VERSION
from ..acceptance import audit as historical
from ..semantic.tasks import REPO
from ..multistep.suite import require

CATALOG=REPO/'faultda_bench/protocols/acceptance_v19.json'
NEW_EXPERIMENTS=('rowdiag_v19','rowdiag_v20','boundary_v21')


def check_inventory(root=REPO,catalog_path=CATALOG):
    root=Path(root); catalog=json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    require(catalog['version']==VERSION,'release version')
    require(catalog['scientific_gate']=='HOLD','science is not a software test')
    original=json.loads((root/'faultda_bench/protocols/acceptance_v18.json').read_text(encoding='utf-8'))
    require(all(catalog['files'].get(name)==checksum for name,checksum in original['files'].items()),'historical scope and hashes')
    require(catalog['new_experiments']==list(NEW_EXPERIMENTS),'new experiment scope')
    require(catalog['new_experiments_human_reviewed'] is False,'old human signatures cannot approve new experiments')
    for name,checksum in catalog['files'].items():
        path=historical.pinned_path(root,name)
        require(path.is_file() and historical.digest(path.read_bytes())==checksum,'changed evidence: '+name)
    return {'files_verified':len(catalog['files']),'catalog_sha256':historical.digest(Path(catalog_path).read_bytes()),
        'provider_authenticity_verified':False,'external_publication_confirmed':False,
        'new_experiments_review':{name:'pending' for name in NEW_EXPERIMENTS}}


def audit(full_replay=False):
    inventory=check_inventory()
    result=historical.audit(full_replay)
    from scripts.verify_rowdiag_v19 import verify as v19
    from ..rowdiag.isolated import verify as v20
    from ..rowdiag.boundary import verify as v21
    reports=REPO/'faultda_bench/reports'
    for name,verifier in (('rowdiag_v19_deepseek',v19),('rowdiag_v20_deepseek',v20),('boundary_v21_deepseek',v21)):
        result['checks'][name]=verifier(reports/(name+'.json'))
    result['historical_acceptance_version']=result['version']
    result['version']=VERSION
    result['engineering_release_ready']=True
    result['new_experiment_review'].update(inventory.pop('new_experiments_review'))
    result.update(inventory)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--full-replay',action='store_true'); p.add_argument('--output',type=Path); a=p.parse_args()
    result=audit(a.full_replay); data=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
    if a.output:
        with a.output.open('xb') as stream: stream.write(data)
    print(data.decode(),end='')
