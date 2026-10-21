"""Fixed-commit review bundle with Python socket guards and no checkout imports."""
import argparse
import hashlib
import json
import locale
import re
import subprocess
import sys
import sysconfig
import time
import zipfile
from pathlib import Path
from . import VERSION
from .audit import CATALOG, REPO
from ..review505.bundle import git_blobs, NAVIGATION
from ..acceptance.audit import pinned_path

RESULT = 'faultda_bench/reports/acceptance_v40_results.json'
CATALOG_NAME = CATALOG.relative_to(REPO).as_posix()


def build(commit, output):
    output = Path(output).resolve()
    if output.exists(): raise FileExistsError(output)
    catalog = json.loads(git_blobs(commit, [CATALOG_NAME])[CATALOG_NAME])
    names = sorted(set(catalog['files']) | set(NAVIGATION) | {CATALOG_NAME, RESULT})
    blobs = git_blobs(commit, names)
    for name, h in catalog['files'].items():
        if hashlib.sha256(blobs[name]).hexdigest() != h:
            raise ValueError('committed evidence mismatch: '+name)
    folder = output.with_suffix(''); folder.mkdir(parents=True, exist_ok=False)
    logs = folder.with_name(folder.name+'_validation_logs'); logs.mkdir(exist_ok=False)
    for name, data in blobs.items():
        target = pinned_path(folder, name)
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    bootstrap = '''import sys,runpy,socket
root,site,module,*args=sys.argv[1:]
sys.path[:0]=[root,site]
def denied(*a,**k): raise RuntimeError("Python socket connection denied during bundle validation")
socket.socket.connect=denied
socket.socket.connect_ex=denied
socket.create_connection=denied
sys.argv=[module]+args
runpy.run_module(module,run_name="__main__")
'''
    checks = {}
    for label, module, args in [('unified_audit', 'faultda_bench.review515.audit', []),
                                ('bundled_tests', 'unittest', ['discover', '-s', 'tests', '-v'])]:
        started = time.monotonic()
        run = subprocess.run([sys.executable, '-I', '-S', '-c', bootstrap,
                              str(folder), sysconfig.get_paths()['purelib'], module, *args],
                             cwd=folder, capture_output=True, timeout=900)
        (logs/(label+'.stdout.log')).write_bytes(run.stdout)
        (logs/(label+'.stderr.log')).write_bytes(run.stderr)
        match = re.search(rb'Ran (\d+) tests?', run.stderr)
        checks[label] = {'exit_code': run.returncode,
                         'elapsed_seconds': round(time.monotonic()-started, 3),
                         'test_count': int(match[1]) if match else None,
                         'stdout_sha256': hashlib.sha256(run.stdout).hexdigest(),
                         'stderr_sha256': hashlib.sha256(run.stderr).hexdigest()}
        if run.returncode: raise RuntimeError('isolated '+label+' failed; see '+str(logs))
        if label == 'unified_audit':
            replay = json.loads(run.stdout.decode(locale.getpreferredencoding(False)))
            if replay != json.loads(blobs[RESULT]): raise ValueError('isolated audit differs from committed result')
    checks['isolation'] = 'python -I -S; explicit bundle/dependency paths, no editable .pth; Python socket connect hooks, not an OS network sandbox'
    checks['inherited_v5_full_test_coverage'] = False
    meta = {'version': VERSION, 'source_commit': commit, 'scientific_gate': 'HOLD',
            'review_scope': 'Received 0.5.10/W4 human opinions; final adjudication and new 0.5.15 independent review pending.',
            'new_provider_requests': 0, 'validation': checks,
            'metadata_origin': 'Project packaging checks, not independent scientific acceptance'}
    blobs['BUNDLE_VALIDATION.json'] = (json.dumps(meta, ensure_ascii=False, indent=2)+'\n').encode()
    manifest = {'version': VERSION, 'commit': commit, 'catalog': CATALOG_NAME,
                'scope': 'Standalone evidence subset; full inherited V5 tests excluded.',
                'files': {n: hashlib.sha256(b).hexdigest() for n, b in sorted(blobs.items())}}
    blobs['REVIEW_MANIFEST.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2)+'\n').encode()
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(blobs.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 18, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED; info.external_attr = 0o100644 << 16
            z.writestr(info, data)
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None or set(z.namelist()) != set(blobs): raise ValueError('ZIP integrity')
        if any(z.read(n) != b for n, b in blobs.items()): raise ValueError('ZIP bytes')
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix+'.sha256').write_bytes((checksum+'  '+output.name+'\n').encode())
    return {'path': str(output), 'sha256': checksum, 'members': len(blobs), 'validation': checks}


if __name__ == '__main__':
    cli = argparse.ArgumentParser(); cli.add_argument('--commit', required=True)
    cli.add_argument('--output', required=True, type=Path); args = cli.parse_args()
    print(json.dumps(build(args.commit, args.output), ensure_ascii=False, indent=2))
