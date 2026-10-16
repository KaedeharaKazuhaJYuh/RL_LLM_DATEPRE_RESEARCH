"""Build fixed-commit evidence bundles and test them without editable-checkout imports."""
import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import sysconfig
import time
import zipfile
from pathlib import Path
from . import VERSION
from .intake import REPO

NAVIGATION = ('README.md', 'faultda_bench/README.md', 'docs/REPRODUCIBILITY.md',
              'docs/PROJECT_HISTORY.md', 'faultda_bench/docs/NEXT_STAGE_CHECKLIST.md',
              '.github/workflows/faultda-current.yml', '.gitattributes')
CATALOG = 'faultda_bench/protocols/acceptance_v38.json'
RESULT = 'faultda_bench/reports/acceptance_v38_results.json'


def profile(catalog):
    names = set(catalog['files']) | set(NAVIGATION) | {CATALOG, RESULT,
            'tasks/v5/beta_holdout_v1/manifest.json', 'tasks/v5/recovery_beta1/manifest.json'}
    for name in names:
        if name.startswith('/') or ':' in name or '..' in name.split('/') or '\\' in name:
            raise ValueError('Unsafe bundle member')
    return sorted(names)


def git_blobs(commit, names):
    if re.fullmatch('[0-9a-f]{40}', commit) is None: raise ValueError('Full commit required')
    raw = subprocess.run(['git', 'cat-file', '--batch'], cwd=REPO,
                         input=('\n'.join(commit+':'+n for n in names)+'\n').encode(),
                         capture_output=True, check=True).stdout
    stream = io.BytesIO(raw); result = {}
    for name in names:
        header = stream.readline().split()
        if len(header) != 3 or header[1] != b'blob': raise ValueError('Missing committed '+name)
        result[name] = stream.read(int(header[2]))
        if stream.read(1) != b'\n': raise ValueError('Batch blob framing')
    return result


def isolated_probe(folder, output_dir):
    """-I -S skips cwd, environment import paths and editable-install .pth files."""
    bootstrap = '''import sys,runpy
root,site,module,*args=sys.argv[1:]
sys.path[:0]=[root,site]
import socket
def denied(*a,**k): raise RuntimeError("Network is disabled during bundle validation")
socket.socket.connect=denied
socket.create_connection=denied
sys.argv=[module]+args
runpy.run_module(module,run_name="__main__")
'''
    checks = {}
    for label, module, args in (
            ('unified_audit', 'faultda_bench.review505.audit', []),
            ('bundled_tests', 'unittest', ['discover', '-s', 'tests', '-v'])):
        started = time.monotonic()
        run = subprocess.run([sys.executable, '-I', '-S', '-c', bootstrap,
                              str(folder.resolve()), sysconfig.get_paths()['purelib'], module, *args],
                             cwd=folder, capture_output=True, timeout=900)
        (output_dir/(label+'.stdout.log')).write_bytes(run.stdout)
        (output_dir/(label+'.stderr.log')).write_bytes(run.stderr)
        match = re.search(rb'Ran (\d+) tests?', run.stderr)
        checks[label] = {'exit_code': run.returncode, 'elapsed_seconds': round(time.monotonic()-started, 3),
                         'test_count': int(match[1]) if match else None,
                         'stdout_sha256': hashlib.sha256(run.stdout).hexdigest(),
                         'stderr_sha256': hashlib.sha256(run.stderr).hexdigest()}
        if run.returncode:
            raise RuntimeError('Isolated '+label+' failed; inspect '+str(output_dir))
    checks['isolation'] = 'python -I -S; explicit bundle and dependency paths; no .pth processing; network connect denied'
    checks['inherited_v5_test_coverage'] = False
    return checks


def build(commit, output, validate=True):
    output = Path(output).resolve()
    if output.exists(): raise FileExistsError(output)
    catalog = json.loads(git_blobs(commit, [CATALOG])[CATALOG])
    blobs = git_blobs(commit, profile(catalog))
    for name, expected in catalog['files'].items():
        if hashlib.sha256(blobs[name]).hexdigest() != expected:
            raise ValueError('Committed evidence mismatch: '+name)
    folder = output.with_suffix('')
    folder.mkdir(parents=True, exist_ok=False)
    for name, data in blobs.items():
        target = folder/name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    logs = folder.with_name(folder.name+'_validation_logs'); logs.mkdir(exist_ok=False)
    validation = isolated_probe(folder, logs) if validate else {'status': 'not_run'}
    if not validate: raise ValueError('Distributable bundles require isolated validation')
    meta = {'version': VERSION, 'source_commit': commit, 'scientific_gate': 'HOLD',
            'human_review': '37 prior technical groups; new version pending', 'new_provider_requests': 0,
            'provider_authenticity_verified': False, 'validation': validation,
            'metadata_origin': 'Generated packaging checks, not independent scientific review'}
    blobs['BUNDLE_VALIDATION.json'] = (json.dumps(meta, ensure_ascii=False, indent=2)+'\n').encode()
    manifest = {'version': VERSION, 'commit': commit, 'catalog': CATALOG,
                'scope': 'Evidence subset with real research runtime support; full inherited V5 tests excluded.',
                'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(blobs.items())}}
    blobs['REVIEW_MANIFEST.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2)+'\n').encode()
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(blobs.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 17, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16; z.writestr(info, data)
    with zipfile.ZipFile(output) as z:
        if z.testzip() is not None: raise ValueError('ZIP CRC failed')
        if set(z.namelist()) != set(blobs): raise ValueError('ZIP file scope')
        for name, data in blobs.items():
            if z.read(name) != data: raise ValueError('ZIP bytes differ: '+name)
    sha = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix+'.sha256').write_bytes((sha+'  '+output.name+'\n').encode())
    return {'path': str(output), 'sha256': sha, 'members': len(blobs), 'validation': validation}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--commit', required=True)
    parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    print(json.dumps(build(args.commit, args.output), ensure_ascii=False, indent=2))
