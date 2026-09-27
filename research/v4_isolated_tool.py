"""Bound and validate one V4 tool process before its result may enter agent state."""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from agent.tools import MUTATING
from research.io import ROOT, digest, read_table, resolve, write_json


def _kill_tree(process):
    if process.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       capture_output=True, check=False)
        if process.poll() is None:
            process.kill()
    else:
        os.killpg(process.pid, signal.SIGKILL)
    process.wait(timeout=5)


def execute_isolated(action, uri, params, attempt_dir, *, timeout=10,
                     fault='none', max_result_bytes=2_000_000,
                     max_artifact_bytes=10_000_000):
    """A failed attempt may leave private files, but cannot return a committed result."""
    if fault not in ('none', 'timeout', 'partial_write'):
        raise ValueError('unsupported fault')
    if timeout <= 0 or max_result_bytes <= 0 or max_artifact_bytes <= 0:
        raise ValueError('invalid process limits')
    source = resolve(uri).resolve(strict=True)
    before = digest(source)
    attempt_dir = Path(attempt_dir).resolve()
    attempt_dir.mkdir(parents=True, exist_ok=False)
    artifact_dir = attempt_dir / 'artifact'
    request = attempt_dir / 'request.json'
    reply = attempt_dir / 'reply.json'
    ready = attempt_dir / 'ready'
    log = attempt_dir / 'worker.log'
    write_json(request, {'action': action, 'args': {'uri': str(source),
               'params': params, 'artifact_dir': str(artifact_dir)}})
    command = [sys.executable, '-m', 'research.v4_tool_worker',
               '--request', str(request), '--reply', str(reply),
               '--ready', str(ready), '--fault', fault]
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    with log.open('wb') as stream:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=stream,
                                   creationflags=flags, start_new_session=os.name != 'nt')
        started = time.perf_counter()
        try:
            while not ready.exists() and process.poll() is None:
                if time.perf_counter() - started > 5:
                    raise TimeoutError('tool process did not become ready')
                time.sleep(.005)
            if not ready.exists():
                raise RuntimeError('tool process exited before ready')
            process.wait(timeout=timeout)
        except (TimeoutError, subprocess.TimeoutExpired):
            _kill_tree(process)
            raise TimeoutError('tool process timed out')
    if digest(source) != before:
        raise ValueError('tool changed its input')
    if process.returncode != 0:
        raise RuntimeError('tool process failed; inspect private worker.log')
    if not reply.exists() or reply.stat().st_size > max_result_bytes:
        raise ValueError('tool reply missing or oversized')
    result = json.loads(reply.read_text(encoding='utf-8'))
    evidence = result.get('evidence') if isinstance(result, dict) else None
    if not isinstance(evidence, dict) or evidence.get('input_sha256') != before:
        raise ValueError('tool reply has invalid input evidence')
    if action in MUTATING:
        artifact = result.get('artifact')
        if not isinstance(artifact, dict):
            raise ValueError('tool artifact missing')
        path = resolve(artifact['path']).resolve(strict=True)
        if not path.is_relative_to(artifact_dir.resolve()):
            raise ValueError('tool artifact escaped attempt directory')
        if path.stat().st_size > max_artifact_bytes or digest(path) != artifact.get('sha256'):
            raise ValueError('tool artifact is oversized or has wrong hash')
        columns, rows = read_table(path)
        if columns != artifact.get('columns') or rows != artifact.get('rows'):
            raise ValueError('tool artifact content does not match reply')
    elif 'artifact' in result:
        raise ValueError('unexpected artifact for read-only tool')
    return result
