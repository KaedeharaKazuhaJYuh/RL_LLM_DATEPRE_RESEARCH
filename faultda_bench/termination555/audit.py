"""Frozen registration and identifier-bound offline grading verification."""
import argparse
import hashlib
import json
from pathlib import Path
from . import VERSION
from .core import ROOT, qualify
from ..acceptance.audit import pinned_path
from ..termination550.audit import audit as previous

CATALOG = ROOT / 'faultda_bench/protocols/acceptance_v46.json'
OUTPUT = ROOT / 'faultda_bench/reports/termination555/qualification.json'


def audit(historical=False):
    c = json.loads(CATALOG.read_text(encoding='utf-8'))
    old = json.loads((ROOT / 'faultda_bench/protocols/acceptance_v45.json').read_text(encoding='utf-8'))
    if c['version'] != VERSION or c['scientific_gate'] != 'HOLD':
        raise ValueError('release scope mismatch')
    if not all(c['files'].get(n)==h for n,h in old['files'].items()):
        raise ValueError('historical freeze changed')
    for n,h in c['files'].items():
        if hashlib.sha256(pinned_path(ROOT,n).read_bytes()).hexdigest()!=h:
            raise ValueError('frozen bytes changed: '+n)
    if json.loads(OUTPUT.read_text(encoding='utf-8')) != qualify():
        raise ValueError('registered qualification replay differs')
    prior = previous(historical)
    return {'version':VERSION,'status':'verified_registered_offline_only',
            'frozen_files':len(c['files']),'historical_version_verified':prior['version'],
            'historical_semantic_audit_replayed':historical,'registered_packets':144,
            'case_identity_authenticated':False,'provider_or_runtime_input_attested':False,
            'new_provider_requests':0,'new_model_executions':0,'scientific_gate':'HOLD',
            'independent_review':'not_arranged','design_admitted':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--historical',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=audit(args.historical)
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        with args.output.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
    print(text)
