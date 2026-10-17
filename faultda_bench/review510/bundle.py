"""Fixed-commit 0.5.10 evidence subset; isolated current audit and all bundled tests."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import sysconfig
import time
import zipfile
from pathlib import Path
from . import VERSION
from ..review505.bundle import git_blobs, profile

CATALOG='faultda_bench/protocols/acceptance_v39.json'
RESULT='faultda_bench/reports/acceptance_v39_results.json'


def build(commit, output):
    output=Path(output).resolve()
    if output.exists():raise FileExistsError(output)
    catalog=json.loads(git_blobs(commit,[CATALOG])[CATALOG])
    names=sorted(set(profile(catalog))|{CATALOG,RESULT})
    blobs=git_blobs(commit,names)
    for n,h in catalog['files'].items():
        if hashlib.sha256(blobs[n]).hexdigest()!=h:raise ValueError('committed evidence '+n)
    folder=output.with_suffix('');folder.mkdir(parents=True,exist_ok=False)
    for n,b in blobs.items():
        p=folder/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    logs=folder.with_name(folder.name+'_validation_logs');logs.mkdir(exist_ok=False)
    bootstrap='''import sys,runpy,socket
root,site,module,*args=sys.argv[1:]
sys.path[:0]=[root,site]
def denied(*a,**k): raise RuntimeError("Network disabled during bundle verification")
socket.socket.connect=denied
socket.create_connection=denied
sys.argv=[module]+args
runpy.run_module(module,run_name="__main__")
'''
    checks={}
    for label,module,args in [('unified_audit','faultda_bench.review510.audit',[]),
                               ('bundled_tests','unittest',['discover','-s','tests','-v'])]:
        start=time.monotonic()
        run=subprocess.run([sys.executable,'-I','-S','-c',bootstrap,str(folder),
                            sysconfig.get_paths()['purelib'],module,*args],cwd=folder,capture_output=True,timeout=900)
        for stream,data in [('stdout',run.stdout),('stderr',run.stderr)]:
            (logs/(label+'.'+stream+'.log')).write_bytes(data)
        count=re.search(rb'Ran (\d+) tests?',run.stderr)
        checks[label]={'exit_code':run.returncode,'elapsed_seconds':round(time.monotonic()-start,3),
                       'test_count':int(count[1]) if count else None,
                       'stdout_sha256':hashlib.sha256(run.stdout).hexdigest(),
                       'stderr_sha256':hashlib.sha256(run.stderr).hexdigest()}
        if run.returncode:raise RuntimeError('Isolated '+label+' failed: '+str(logs))
    if checks['bundled_tests']['test_count']!=318:raise ValueError('unexpected bundled test scope')
    meta={'version':VERSION,'source_commit':commit,'scientific_gate':'HOLD','new_provider_requests':0,
          'new_review_status':'pending','validation':checks,
          'isolation':'python -I -S; no editable .pth imports; network connects denied',
          'metadata_origin':'Packaging validation, not independent human/scientific acceptance',
          'inherited_v5_tests_included':False}
    blobs['BUNDLE_VALIDATION.json']=(json.dumps(meta,ensure_ascii=False,indent=2)+'\n').encode()
    manifest={'version':VERSION,'commit':commit,'files':{n:hashlib.sha256(b).hexdigest() for n,b in sorted(blobs.items())}}
    blobs['REVIEW_MANIFEST.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for n,b in sorted(blobs.items()):
            info=zipfile.ZipInfo(n,(2026,10,18,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16;z.writestr(info,b)
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None or set(z.namelist())!=set(blobs):raise ValueError('ZIP scope/CRC')
        if any(z.read(n)!=b for n,b in blobs.items()):raise ValueError('ZIP bytes')
    sha=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_bytes((sha+'  '+output.name+'\n').encode())
    return {'path':str(output),'sha256':sha,'members':len(blobs),'validation':checks}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(build(a.commit,a.output),indent=2))
