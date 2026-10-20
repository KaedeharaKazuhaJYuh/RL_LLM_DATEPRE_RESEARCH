"""Within-0.5.55 optimized audit, retaining the frozen original audit entry."""
import argparse
import hashlib
import json
from pathlib import Path

from . import core
from .runtime import BatchSnapshot, BASE_CATALOG_SHA256
from ..acceptance.audit import pinned_path

MANIFEST = core.ROOT/'faultda_bench/protocols/performance555_v1.json'


def audit(historical=False):
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    if (manifest['version']!='0.5.55-dev' or manifest['revision']!='within-version-performance-1'
            or manifest['base_catalog_sha256']!=BASE_CATALOG_SHA256
            or manifest['scientific_gate']!='HOLD'):
        raise ValueError('performance revision scope mismatch')
    for name,want in manifest['optimization_files'].items():
        if hashlib.sha256(pinned_path(core.ROOT,name).read_bytes()).hexdigest()!=want:
            raise ValueError('changed optimization evidence: '+name)
    with BatchSnapshot.load() as session:
        result=session.qualify()
        expected=json.loads((core.ROOT/'faultda_bench/reports/termination555/qualification.json').read_text(encoding='utf-8'))
        if result!=expected:
            raise ValueError('optimized qualification differs from frozen result')
        metadata=session.metadata
    measured=json.loads((core.ROOT/'faultda_bench/reports/termination555_performance/paired_benchmark.json').read_text(encoding='utf-8'))
    if (len({s['result_sha256'] for s in measured['samples']})!=1
            or measured['cpu_energy_joules'] is not None
            or measured['energy_improvement_percent'] is not None):
        raise ValueError('benchmark equivalence or energy evidence scope mismatch')
    if historical:
        from .audit import audit as reference
        reference(True)
    return {'version':'0.5.55-dev','revision':'within-version-performance-1',
            'status':'verified_optimized_offline_only','base_frozen_files_verified':metadata['frozen_files_verified'],
            'optimization_files_verified':len(manifest['optimization_files']),
            'registered_packets':len(result['rows']),'frozen_qualification_identical':True,
            'snapshot_lifetime':metadata['lifetime'],'recorded_benchmark_reexecuted':False,
            'historical_reference_audit_replayed':historical,
            'cpu_energy_joules':None,'energy_improvement_percent':None,
            'case_identity_authenticated':False,'provider_or_runtime_input_attested':False,
            'new_provider_requests':0,'new_model_executions':0,'scientific_gate':'HOLD'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--historical',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=audit(args.historical)
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        with args.output.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
    print(text)
