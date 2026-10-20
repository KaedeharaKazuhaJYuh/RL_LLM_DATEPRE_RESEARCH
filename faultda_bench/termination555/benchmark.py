"""Paired CPU/file-work benchmark. No inferred joules or provider execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import sysconfig
import time
from unittest.mock import patch

from . import core
from .runtime import BatchSnapshot, BASE_CATALOG_SHA256, BASE_COMMIT


class _Reads:
    def __init__(self):
        self.opens = 0
        self.returned_bytes = 0

    def wrap(self, stream):
        owner = self
        class Reader:
            def __enter__(self):
                stream.__enter__()
                return self
            def __exit__(self, *args):
                return stream.__exit__(*args)
            def read(self, *args, **kwargs):
                value = stream.read(*args, **kwargs)
                owner.returned_bytes += len(value.encode('utf-8') if isinstance(value, str) else value)
                return value
            def __getattr__(self, name):
                return getattr(stream, name)
        return Reader()


def _peak_memory():
    try:
        import psutil
        info = psutil.Process().memory_info()
        if hasattr(info, 'peak_wset'):
            return info.peak_wset, 'Windows process peak working set (psutil)'
    except ImportError:
        pass
    if sys.platform.startswith('linux'):
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024, 'Linux process peak RSS'
    return None, 'unavailable; not estimated'


def worker(variant):
    if variant not in ('reference', 'snapshot'):
        raise ValueError('unknown benchmark variant')
    keys = tuple(core.registry()['entries'])  # common scheduling, outside timing
    counter = _Reads()
    original_open = Path.open
    def counted(path, *args, **kwargs):
        stream = original_open(path, *args, **kwargs)
        mode = args[0] if args else kwargs.get('mode', 'r')
        if 'r' in mode:
            counter.opens += 1
            return counter.wrap(stream)
        return stream
    digest = hashlib.sha256()
    metadata = None
    with patch.object(Path, 'open', counted):
        wall, cpu = time.perf_counter(), time.process_time()
        snapshot = BatchSnapshot.load() if variant == 'snapshot' else None
        try:
            for key in keys:
                engine = snapshot if snapshot is not None else core
                prepared = engine.prepare(key)
                decision = core.old.rule(prepared['payload'])
                result = engine.grade(key, prepared['payload'], prepared['body'], decision)
                # Bind complete public inputs and complete score/binding records.
                digest.update(core.canonical(prepared).encode())
                digest.update(core.canonical(result).encode())
            if snapshot is not None:
                metadata = snapshot.metadata
        finally:
            if snapshot is not None:
                snapshot.close()
        cpu = time.process_time() - cpu
        wall = time.perf_counter() - wall
    memory, method = _peak_memory()
    return {'variant': variant, 'cases': len(keys), 'wall_seconds': wall,
            'process_cpu_seconds': cpu, 'cases_per_second': len(keys)/wall,
            'process_cpu_seconds_per_case': cpu/len(keys),
            'path_read_opens': counter.opens, 'logical_read_bytes': counter.returned_bytes,
            'process_peak_memory_bytes': memory, 'process_peak_memory_method': method,
            'result_sha256': digest.hexdigest(), 'snapshot_metadata': metadata,
            'cpu_energy_joules': None, 'system_energy_joules': None,
            'energy_improvement_percent': None}


def benchmark(pairs=3):
    if type(pairs) is not int or not 1 <= pairs <= 9:
        raise ValueError('paired repeats must be between 1 and 9')
    bootstrap = '''import sys,runpy,socket
root,site,module,*args=sys.argv[1:]
sys.path[:0]=[root,site]
def denied(*a,**k): raise RuntimeError('Benchmark Python network connections disabled')
socket.socket.connect=denied
socket.socket.connect_ex=denied
socket.create_connection=denied
sys.argv=[module]+args
runpy.run_module(module,run_name='__main__')
'''
    samples = []
    for pair in range(pairs):
        order = ('reference', 'snapshot') if pair % 2 == 0 else ('snapshot', 'reference')
        for variant in order:
            result = subprocess.run([sys.executable, '-I', '-S', '-c', bootstrap,
                                     str(core.ROOT), sysconfig.get_paths()['purelib'],
                                     'faultda_bench.termination555.benchmark', '--worker', variant],
                                    cwd=core.ROOT, capture_output=True, timeout=300, check=True)
            row = json.loads(result.stdout)
            row.update(pair=pair, position=order.index(variant))
            samples.append(row)
    if len({s['result_sha256'] for s in samples}) != 1:
        raise ValueError('reference/snapshot outputs differ')
    medians = {}
    fields = ('wall_seconds','process_cpu_seconds','cases_per_second',
              'process_cpu_seconds_per_case','path_read_opens','logical_read_bytes',
              'process_peak_memory_bytes')
    for variant in ('reference','snapshot'):
        rows = [r for r in samples if r['variant']==variant]
        medians[variant] = {k: statistics.median([r[k] for r in rows])
                            if all(r[k] is not None for r in rows) else None for k in fields}
    a,b = medians['reference'], medians['snapshot']
    return {'version':'0.5.55-dev','revision':'within-version-performance-1',
            'baseline_commit':BASE_COMMIT,'baseline_catalog_sha256':BASE_CATALOG_SHA256,
            'python':platform.python_version(),'platform':platform.platform(),
            'logical_cpu_count':os.cpu_count(),'paired_repeats':pairs,'samples':samples,
            'median':medians,'wall_speedup':a['wall_seconds']/b['wall_seconds'],
            'cpu_time_reduction_percent':100*(1-b['process_cpu_seconds']/a['process_cpu_seconds']),
            'logical_read_reduction_percent':100*(1-b['logical_read_bytes']/a['logical_read_bytes']),
            'all_public_inputs_and_scores_match':True,
            'cpu_energy_joules':None,'system_energy_joules':None,'energy_improvement_percent':None,
            'measurement_limits':[
                'Fresh subprocesses, alternating order; OS filesystem cache not flushed',
                'Times include snapshot validation and cache construction; exclude interpreter/import startup',
                'Read counters cover Path.open reads; text counted as returned UTF-8, not physical disk traffic',
                'Snapshot checks all 660 frozen files once; reference rechecks its own sources per API call',
                'Peak process memory includes interpreter and imports; not Python allocations alone',
                'CPU time and logical reads are work proxies, not measured electrical energy',
                'No model inference, GPU/NPU throughput or model-capability comparison'],
            'new_provider_requests':0,'scientific_gate':'HOLD'}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--worker',choices=('reference','snapshot'))
    parser.add_argument('--pairs',type=int,default=3)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=worker(args.worker) if args.worker else benchmark(args.pairs)
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        with args.output.open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
    print(text)
