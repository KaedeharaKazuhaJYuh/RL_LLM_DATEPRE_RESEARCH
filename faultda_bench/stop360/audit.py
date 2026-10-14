"""Additive live engineering evidence, without independent acceptance claims."""
import argparse
import json
from pathlib import Path
from . import VERSION
from .suite import verify
from ..state355.audit import audit as previous
from ..acceptance.audit import digest,pinned_path
from ..semantic.tasks import REPO
from ..multistep.suite import require

CATALOG=REPO/'faultda_bench/protocols/acceptance_v29.json'


def check_inventory(root=REPO,catalog_path=CATALOG):
    root=Path(root);c=json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    old=json.loads((root/'faultda_bench/protocols/acceptance_v28.json').read_text(encoding='utf-8'))
    require(c['version']==VERSION and c['scientific_gate']=='HOLD','scope')
    require(c['new_experiments']==['stop_v31'] and c['new_experiments_human_reviewed'] is False,'review scope')
    require(all(c['files'].get(n)==h for n,h in old['files'].items()),'historical preservation')
    for n,h in c['files'].items():
        p=pinned_path(root,n);require(p.is_file() and digest(p.read_bytes())==h,'changed evidence: '+n)
    return {'files_verified':len(c['files']),'catalog_sha256':digest(Path(catalog_path).read_bytes())}


def audit():
    inventory=check_inventory();result=previous()
    result['previous_release_version']=result['version'];result['version']=VERSION
    result['checks']['stop_v31']=verify(REPO/'faultda_bench/reports/stop_v31_deepseek.json')
    from .suite import matrix
    from ..multistep.suite import same
    require(same(json.loads((REPO/'faultda_bench/reports/stop_v31_matrix.json').read_text(encoding='utf-8')),matrix()),'offline stop matrix replay')
    result['checks']['stop_v31_matrix']={'status':'verified','snapshots':20,'ready':6}
    from .analysis import verify as accounting_verify
    result['checks']['stop_v31_accounting']=accounting_verify()
    result['new_experiment_review']['stop_v31']='pending';result.update(inventory);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
    data=(json.dumps(audit(),ensure_ascii=False,indent=2)+'\n').encode()
    if a.output:
        with a.output.open('xb') as stream:stream.write(data)
    print(data.decode(),end='')
