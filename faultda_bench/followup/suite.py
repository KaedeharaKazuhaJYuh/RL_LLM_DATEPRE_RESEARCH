"""Post-history output checks; returned actions are never executed."""
import argparse
import json
import random
import tempfile
from pathlib import Path

from . import VERSION
from ..formatdiag.core import Client, body, sha_bytes
from ..formatdiag.suite import protocol as initial_protocol
from ..pilot.contract import public_observation
from ..pilot.verify import verify as historical_verify
from ..trust.environment import ComputeFaultEnv
from ..evidence.core import tasks
from ..semantic.tasks import REPO, sha
from ..clarity.tasks import write_json

HISTORY = REPO / 'faultda_bench/reports/pilot_v12_deepseek.json'
SELECTED = (('window-01', 'stage_only'), ('version-01', 'healthy'), ('group-01', 'shared_compute'))


def snapshots():
    historical_verify(HISTORY)
    rows = [json.loads(x) for x in HISTORY.with_suffix('.jsonl').read_text(encoding='utf-8').splitlines()]
    mapping = {t['id']: t for t in tasks()}
    result = {}
    with tempfile.TemporaryDirectory(prefix='faultda_followup_') as folder:
        for task_id, mode in SELECTED:
            row = next(r for r in rows if r['task_id'] == task_id and r['mode'] == mode)
            indices = [i for i, event in enumerate(row['trace']) if i > 0 and event['action'] == 'invalid_model_output']
            for position, index in (('early', indices[0]), ('late', indices[-1])):
                key = task_id + '_' + position
                env = ComputeFaultEnv(mapping[task_id], Path(folder)/key, mode=mode, evidence='E1', budget=3)
                for event in row['trace'][:index]:
                    env.step(event['action'], event['params'])
                    if env.history[-1] != event:
                        raise ValueError('historical feedback mismatch')
                observation = public_observation(env)
                if observation['terminal'] is not None:
                    raise ValueError('snapshot already terminal')
                result[key] = {'observation': observation, 'provenance': {'task_id': task_id, 'historical_mode': mode,
                               'trace_index': index, 'selection': position}}
    return result


def protocol():
    initial = initial_protocol()
    hashes = initial['code_sha256'].copy()
    hashes.update({p.relative_to(REPO).as_posix(): sha(p) for p in Path(__file__).parent.glob('*.py')})
    cells = [dict(snapshot_id=key, thinking='disabled', max_tokens=800, repeat=r)
             for key in sorted(snapshots()) for r in (0, 1)]
    random.Random(2026101175).shuffle(cells)
    return {'version': VERSION, 'snapshots': snapshots(), 'order': cells, 'code_sha256': hashes,
            'source_sha256': initial['source_sha256'], 'historical_trace_sha256': sha(HISTORY.with_suffix('.jsonl')),
            'request_cap': 12, 'scope': 'selected early/late failed-history snapshots; diagnostic selection, no recovery actions',
            'scientific_gate': 'HOLD'}


def summary(rows):
    usage = [r['usage'] for r in rows if isinstance(r.get('usage'), dict)
             and all(type(r['usage'].get(k)) is int for k in ('prompt_tokens','completion_tokens'))]
    return {'planned': len(rows), 'requests': sum(r['request_sent'] is True for r in rows),
            'categories': {c: sum(r['category'] == c for r in rows) for c in sorted({r['category'] for r in rows})},
            'length_finish': sum(r.get('length_finish') is True for r in rows),
            'usage_available_calls': len(usage),
            'reported_prompt_tokens': sum(u['prompt_tokens'] for u in usage) if usage else None,
            'reported_completion_tokens': sum(u['completion_tokens'] for u in usage) if usage else None,
            'scientific_gate': 'HOLD', 'recovery_or_rl_claim': False}


def live(plan, output):
    frozen = json.loads(Path(plan).read_text(encoding='utf-8'))
    if frozen != protocol():
        raise ValueError('frozen plan changed')
    output = Path(output); pp=output.with_suffix('.protocol.json'); tp=output.with_suffix('.jsonl')
    if any(p.exists() for p in (output,pp,tp)):
        raise FileExistsError('use new paths')
    client = Client('deepseek-flash', 12)
    write_json(pp,frozen); rows=[]
    with tp.open('xb') as stream:
        for cell in frozen['order']:
            row={**cell, **client.request_once(frozen['snapshots'][cell['snapshot_id']]['observation'],cell)}
            rows.append(row); stream.write((json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n').encode()); stream.flush()
            print(json.dumps({'completed':len(rows),'planned':12}),flush=True)
    write_json(output,{'version':VERSION,'backend':'deepseek_live_single_decision','protocol_sha256':sha(pp),
                       'trace_sha256':sha(tp),'summary':summary(rows)})
    return summary(rows)


def verify(output):
    output=Path(output); pp=output.with_suffix('.protocol.json'); tp=output.with_suffix('.jsonl')
    result=json.loads(output.read_text(encoding='utf-8')); frozen=json.loads(pp.read_text(encoding='utf-8'))
    def require(value):
        if not value: raise ValueError('followup receipt mismatch')
    require(result['version']==VERSION and result['backend']=='deepseek_live_single_decision')
    require(result['protocol_sha256']==sha(pp) and result['trace_sha256']==sha(tp))
    require(frozen==protocol())
    rows=[json.loads(x) for x in tp.read_text(encoding='utf-8').splitlines()]; require(len(rows)==12)
    from ..pilot.contract import valid_decision
    for row,cell in zip(rows,frozen['order']):
        require(json.dumps({k:row[k] for k in cell},sort_keys=True)==json.dumps(cell,sort_keys=True))
        payload=json.dumps(body(frozen['snapshots'][cell['snapshot_id']]['observation'],cell),ensure_ascii=False,allow_nan=False).encode()
        require(row['request_sha256']==sha_bytes(payload) and row['request_bytes']==len(payload))
        require(type(row['request_sent']) is bool)
        if row['category']=='valid_action': require(valid_decision(row['decision']))
        if 'finish_reason' in row: require(row['length_finish']==(row['finish_reason']=='length'))
    require(result['summary']==summary(rows) and result['summary']['requests']<=12)
    return {'status':'verified','snapshots_rebuilt':6,'requests_rebuilt':12,
            'response_classification_independently_replayed':False,'provider_authenticity_verified':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--freeze',type=Path); parser.add_argument('--protocol',type=Path)
    parser.add_argument('--output',type=Path); parser.add_argument('--verify',type=Path); args=parser.parse_args()
    if args.freeze and not any((args.protocol,args.output,args.verify)): write_json(args.freeze,protocol())
    elif args.verify and not any((args.protocol,args.output,args.freeze)): print(json.dumps(verify(args.verify)))
    elif args.protocol and args.output and not any((args.verify,args.freeze)): print(json.dumps(live(args.protocol,args.output)))
    else: parser.error('choose freeze, verify, or protocol with output')
