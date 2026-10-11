import argparse
import hashlib
import itertools
import json
import random
import tempfile
from pathlib import Path

from ..clarity.tasks import write_json
from ..evidence.core import tasks
from ..semantic.oracle import evaluate
from ..semantic.policies import choose
from ..semantic.tasks import REPO, sha
from ..surface.policy import choose_stage_reference
from ..trust.environment import ComputeFaultEnv, MODES
from ..trust.policy import choose_guarded_read
from . import VERSION
from .contract import MAX_PROMPT_BYTES, RELIABILITY, SYSTEM, prompt_bytes, public_observation

ARMS = ('read_reference', 'stage_reference', 'guarded_read', 'abstain')


def order():
    cells = [dict(task_id=t['id'], mode=mode, evidence='E1', budget=3)
             for t, mode in itertools.product(tasks(), MODES)]
    random.Random(20261011).shuffle(cells)
    return cells


def code_hashes():
    paths = [REPO / 'agent/deepseek_config.py']
    for package in ('semantic', 'clarity', 'evidence', 'surface', 'trust', 'pilot'):
        paths.extend((REPO / 'faultda_bench' / package).glob('*.py'))
    return {p.relative_to(REPO).as_posix(): sha(p) for p in sorted(paths)}


def protocol(model='deepseek-flash'):
    ts = tasks()
    return {'version': VERSION, 'tasks': ts, 'pilot_order': order(),
            'offline_order': [{**c, 'arm': a} for c in order() for a in ARMS],
            'reliability_contract': RELIABILITY, 'system': SYSTEM,
            'requested_model': model, 'max_calls': 96, 'max_tokens': 800, 'temperature': 0,
            'max_prompt_bytes': MAX_PROMPT_BYTES, 'timeout_seconds': 45, 'implicit_retries': 0,
            'concurrency': 1, 'censoring': 'record request-cap, input-limit and provider failures separately; do not drop them',
            'code_sha256': code_hashes(), 'source_sha256': {t['source_path']: t['source_sha256'] for t in ts},
            'scope': 'nine old-instance diagnostic conditions; one provider; no RL, novelty or significance claim',
            'scoring': 'private Decimal oracle; completion, false completion, unsafe writes and escalation separate',
            'information': 'identical public tools, reliability warning and evidence permissions; no oracle answers or fault mode',
            'cost': 'actual reads, writes, response bytes and provider usage separately; rule arithmetic is system assistance'}


def execute(task, folder, cell, client=None):
    env = ComputeFaultEnv(task, folder, **{k: cell[k] for k in ('mode', 'evidence', 'budget')})
    calls, prompts = [], []
    selectors = {'read_reference': lambda o: choose(o, 'task_semantic'),
                 'stage_reference': choose_stage_reference, 'guarded_read': choose_guarded_read,
                 'abstain': lambda o: {'action': 'escalate'}}
    while not env.terminal:
        observation = public_observation(env)
        encoded = prompt_bytes(observation)
        prompts.append({'sha256': hashlib.sha256(encoded).hexdigest(), 'bytes': len(encoded)})
        if len(encoded) > MAX_PROMPT_BYTES:
            env.terminal = 'input_limit'
            break
        if client is None:
            decision = selectors[cell['arm']](observation)
            if decision['action'] in ('inspect', 'inputs', 'catalog', 'status') and not observation['remaining']['checks']:
                decision = {'action': 'escalate'}
        else:
            decision, metadata = client.choose(observation)
            calls.append(metadata)
            if decision is None:
                error = metadata.get('error')
                env.terminal = ('api_budget_exceeded' if error == 'pilot_call_cap' else
                                'input_limit' if error == 'input_limit' else 'provider_error')
                break
        # Model overbudget/invalid decisions are not repaired by the runner.
        env.step(decision['action'], decision.get('params', {}))
    return {**cell, **evaluate(env), 'prompt_audit': prompts, 'api_calls': calls}


def summarize(rows):
    sent = [m for r in rows for m in r['api_calls'] if m.get('request_sent') is True]
    usages = [m['usage'] for m in sent if isinstance(m.get('usage'), dict)
              and all(type(m['usage'].get(k)) is int for k in ('prompt_tokens', 'completion_tokens'))]
    return {'executions': len(rows), 'task_clusters': 3,
            'by_arm': {a: {k: sum(int(r[k]) for r in rows if r['arm'] == a)
                          for k in ('safe_complete', 'false_completion', 'safe_escalation', 'agent_wrong_publications')}
                       for a in sorted({r['arm'] for r in rows})},
            'request_attempts': len(sent), 'usage_available_calls': len(usages),
            'reported_prompt_tokens': sum(u['prompt_tokens'] for u in usages) if usages else None,
            'reported_completion_tokens': sum(u['completion_tokens'] for u in usages) if usages else None,
            'actual_models': sorted({m['model'] for m in sent if isinstance(m.get('model'), str)}),
            'terminal_counts': {t: sum(r['terminal'] == t for r in rows) for t in sorted({r['terminal'] for r in rows})},
            'api_censored_cases': sum(r['terminal'] == 'api_budget_exceeded' for r in rows),
            'model_cases_without_request': sum(r['arm'] == 'deepseek' and not any(m.get('request_sent') is True for m in r['api_calls']) for r in rows),
            'scientific_gate': 'HOLD', 'model_improvement_claim': False}


def offline(output, model='deepseek-flash'):
    output = Path(output)
    pp, tp = output.with_suffix('.protocol.json'), output.with_suffix('.jsonl')
    if any(p.exists() for p in (output, pp, tp)):
        raise FileExistsError('use new output paths')
    frozen = protocol(model)
    write_json(pp, frozen)
    mapping = {t['id']: t for t in frozen['tasks']}
    with tempfile.TemporaryDirectory(prefix='faultda_pilot_offline_') as folder:
        rows = [execute(mapping[c['task_id']], Path(folder) / str(i), c)
                for i, c in enumerate(frozen['offline_order'])]
    save(output, pp, tp, rows, 'offline_rules')
    return summarize(rows)


def save(output, pp, tp, rows, backend):
    with tp.open('xb') as f:
        for row in rows:
            f.write((json.dumps(row, ensure_ascii=False) + '\n').encode())
    save_result(output, pp, tp, rows, backend)


def save_result(output, pp, tp, rows, backend):
    write_json(output, {'version': VERSION, 'backend': backend, 'protocol': pp.name,
                       'protocol_sha256': sha(pp), 'trace': tp.name, 'trace_sha256': sha(tp),
                       'summary': summarize(rows)})


def live(protocol_path, output):
    from .client import Client
    protocol_path, output = Path(protocol_path), Path(output)
    frozen = json.loads(protocol_path.read_text(encoding='utf-8'))
    if frozen != protocol(frozen['requested_model']):
        raise ValueError('frozen protocol or code changed')
    for name, checksum in frozen['source_sha256'].items():
        if sha(REPO / name) != checksum:
            raise ValueError('source changed')
    pp, tp = output.with_suffix('.protocol.json'), output.with_suffix('.jsonl')
    if any(p.exists() for p in (output, pp, tp)):
        raise FileExistsError('use new output paths')
    client = Client(frozen['requested_model'], frozen['max_calls'])
    # Preserve identical frozen plan before any network call.
    write_json(pp, frozen)
    mapping = {t['id']: t for t in frozen['tasks']}
    rows = []
    with tempfile.TemporaryDirectory(prefix='faultda_pilot_live_') as folder, tp.open('xb') as stream:
        for i, cell in enumerate(frozen['pilot_order']):
            row = execute(mapping[cell['task_id']], Path(folder) / str(i), {**cell, 'arm': 'deepseek'}, client)
            rows.append(row)
            stream.write((json.dumps(row, ensure_ascii=False) + '\n').encode())
            stream.flush()
            print(json.dumps({'completed_cases': i + 1, 'planned_cases': len(frozen['pilot_order']),
                              'request_attempts': client.calls}), flush=True)
    save_result(output, pp, tp, rows, 'deepseek_live')
    return summarize(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend', choices=('offline', 'deepseek'), default='offline')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', default='deepseek-flash')
    parser.add_argument('--protocol', type=Path)
    args = parser.parse_args()
    if args.backend == 'deepseek' and args.protocol is None:
        parser.error('DeepSeek run needs an existing frozen --protocol')
    print(json.dumps(offline(args.output, args.model) if args.backend == 'offline' else live(args.protocol, args.output)))
