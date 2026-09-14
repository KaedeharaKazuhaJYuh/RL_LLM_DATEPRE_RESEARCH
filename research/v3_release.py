"""Offline V3 acceptance run; reports in --out and scratch artifacts in artifacts/."""
import argparse
import hashlib
import subprocess
from pathlib import Path
from research.io import ROOT, write_json
from research.v3_baselines import evaluate as planning
from research.v3_runtime import evaluate as runtime
from research.v3_final import evaluate as recovery
from research.v3_subprocess_faults import evaluate as processes


def tracked_hashes():
    paths = subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    return {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths if p and (ROOT/p).is_file()}


def main(out):
    out = Path(out).resolve(); out.mkdir(parents=True,exist_ok=True)
    before = tracked_hashes()
    plans = {mode: planning(mode) for mode in ('keyword','nearest','oracle')}
    runs = {}
    for mode, recover, inject in [('oracle',False,False),('oracle',False,True),('oracle',True,True),('keyword',False,False)]:
        key = f'{mode}_recover{int(recover)}_inject{int(inject)}'
        result = runtime(mode,recover,inject)
        runs[key] = {k:v for k,v in result.items() if k != 'records'}
        write_json(out/(key+'.json'),result)
    selective = recovery(str(out/'selective.json'))
    child = processes(out=str(out/'processes.json'))
    after = tracked_hashes()
    changed = [p for p in before if before[p] != after.get(p)]
    checks = {'tracked_files_unchanged': not changed,
              'oracle_executes_all': runs['oracle_recover0_inject0']['passed'] == runs['oracle_recover0_inject0']['tasks'],
              'bounded_recovery_executes_all': runs['oracle_recover1_inject1']['passed'] == runs['oracle_recover1_inject1']['tasks'],
              'child_process_cases_pass': child['passed'] == child['cases'],
              'terse_logs_escalate': selective['by_style']['terse']['accepted'] == 0}
    result = {'version':'3.6-final','checks':checks,'changed_tracked_files':changed,
              'planning':{k:{x:y for x,y in v.items() if x!='records'} for k,v in plans.items()},
              'runtime':runs,'recovery':selective['baselines'],
              'processes':{k:v for k,v in child.items() if k!='records'}}
    write_json(out/'acceptance.json',result)
    if not all(checks.values()): raise RuntimeError('V3 acceptance failed: '+str(checks))
    print(checks)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',default='work/v3_acceptance')
    main(parser.parse_args().out)
