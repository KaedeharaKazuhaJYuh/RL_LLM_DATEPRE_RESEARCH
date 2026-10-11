"""Offline attribution and a public-only gate at recorded publish boundaries."""
import argparse
import json
import math
import tempfile
from decimal import Decimal
from pathlib import Path

from . import VERSION
from ..multistep.suite import verify as verify_source
from ..trust.environment import ComputeFaultEnv
from ..trust.policy import public_expected
from ..semantic.compute import calculate, parameters
from ..semantic.oracle import record_correct
from ..semantic.tasks import REPO, sha
from ..clarity.tasks import write_json
from ..pilot.contract import public_observation

SOURCE = REPO / 'faultda_bench/reports/multistep_v15_deepseek.json'
CHECKLIST = (
    'Before publishing, obtain the public inputs and catalog within the check budget. '
    'Resolve snapshot/latest version from catalog. For grouping, count each business key once; '
    'for windows use start-inclusive/end-exclusive boundaries. '
    'Validate the exact stage_id you intend to publish against trustworthy public evidence. '
    'Compare numerical results independently; report/stage agreement and ok flags alone do not prove correctness. '
    'Do not publish a known incorrect candidate. If evidence or a correct candidate is unavailable, escalate before writing. '
    'After successful verified publication, stop within the remaining budget.'
)


def close_output(actual, expected):
    return isinstance(actual, dict) and set(actual) == set(expected) and all(
        type(actual[k]) in (int,float) and math.isfinite(actual[k]) and
        abs(Decimal(str(actual[k]))-Decimal(str(value))) <= max(Decimal('1e-9'),abs(Decimal(str(value)))*Decimal('1e-9'))
        for k,value in expected.items())


def gate(observation, decision):
    """No task, oracle, hidden mode or private candidate access."""
    if decision.get('action') != 'publish':
        return {'allow':True,'reason':'not_publication'}
    params=decision.get('params',{})
    if not isinstance(params,dict) or set(params)!={'stage_id','request_id','expected_revision','mode'}:
        return {'allow':False,'reason':'publication_schema'}
    candidates=[e['response'] for e in observation['history'] if e['action']=='stage'
                and e['response'].get('ok') is True and e['response'].get('stage_id')==params['stage_id']]
    if len(candidates)!=1:
        return {'allow':False,'reason':'candidate_not_observed'}
    try:
        expected_params, expected=public_expected(observation)
    except (KeyError,TypeError,ValueError):
        return {'allow':False,'reason':'independent_evidence_unavailable'}
    candidate=candidates[0]
    if candidate.get('params')!=expected_params or candidate.get('version')!=expected_params['version']:
        return {'allow':False,'reason':'candidate_contract_mismatch'}
    if not close_output(candidate.get('output'),expected):
        return {'allow':False,'reason':'candidate_numeric_mismatch'}
    inspected=next((e['response'] for e in reversed(observation['history']) if e['action']=='inspect' and e['response'].get('ok') is True),None)
    if inspected is None or params['mode']!='replace' or type(params['expected_revision']) is not int or params['expected_revision']!=inspected['revision']:
        return {'allow':False,'reason':'publication_binding_unverified'}
    return {'allow':True,'reason':'public_candidate_verified'}


def protocol():
    old=json.loads(SOURCE.with_suffix('.protocol.json').read_text(encoding='utf-8'))
    hashes=old['code_sha256'].copy()
    hashes.update({p.relative_to(REPO).as_posix():sha(p) for p in Path(__file__).parent.glob('*.py')})
    return {'version':VERSION,'source_result_sha256':sha(SOURCE),'source_trace_sha256':sha(SOURCE.with_suffix('.jsonl')),
            'code_sha256':hashes,'source_sha256':old['design']['source_sha256'],
            'scope':'all historical publish attempts; pre-publication snapshot gate, not adaptive model rerun',
            'checklist':CHECKLIST,'scientific_gate':'HOLD'}


def findings():
    verify_source(SOURCE)
    frozen=json.loads(SOURCE.with_suffix('.protocol.json').read_text(encoding='utf-8'))
    mapping={t['id']:t for t in frozen['design']['tasks']}
    rows=[json.loads(x) for x in SOURCE.with_suffix('.jsonl').read_text(encoding='utf-8').splitlines()]
    attempts=[]
    with tempfile.TemporaryDirectory(prefix='faultda_publish_audit_') as folder:
        for i,row in enumerate(rows):
            env=ComputeFaultEnv(mapping[row['task_id']],Path(folder)/str(i),mode=row['mode'],evidence='E1',budget=3)
            for index,event in enumerate(row['trace']):
                if event['action']=='publish':
                    decision={'action':'publish','params':event['params']}
                    public_gate=gate(public_observation(env),decision)
                    before=len(env.effects)
                env.step(event['action'],event['params'])
                if env.history[-1]!=event: raise ValueError('historical feedback changed')
                if event['action']!='publish': continue
                effects=env.effects[before:]; effect=next((e for e in effects if e['actor']=='agent'),None)
                item={'task_id':row['task_id'],'mode':row['mode'],'repeat':row['repeat'],'trace_index':index,
                      'request_applied':effect is not None,'public_gate':public_gate,'wrong_publication':False,
                      'relevant_parameter_deviations':[],'healthy_compute_disagreement':False}
                if effect is not None:
                    record=effect['record']; task=env.task; expected=parameters(task['contract'],task['catalog'])
                    relevant=['version']+(['deduplicate_keys'] if task['contract']['family']=='group' else ['closed'] if task['contract']['family']=='window' else [])
                    item['relevant_parameter_deviations']=[k for k in relevant if record['params'].get(k)!=expected[k]]
                    healthy=calculate(task['versions'][record['version']],task['dimension'],task['contract'],record['params'])
                    item['healthy_compute_disagreement']=not close_output(record['output'],healthy)
                    item['wrong_publication']=not record_correct(record,task)
                attempts.append(item)
    return attempts


def summarize(rows):
    bad=[r for r in rows if r['wrong_publication']]
    return {'publication_attempts':len(rows),'applied':sum(r['request_applied'] for r in rows),'wrong_publications':len(bad),
            'bad_parameter_only':sum(bool(r['relevant_parameter_deviations']) and not r['healthy_compute_disagreement'] for r in bad),
            'bad_compute_only':sum(not r['relevant_parameter_deviations'] and r['healthy_compute_disagreement'] for r in bad),
            'bad_both':sum(bool(r['relevant_parameter_deviations']) and r['healthy_compute_disagreement'] for r in bad),
            'bad_neither':sum(not r['relevant_parameter_deviations'] and not r['healthy_compute_disagreement'] for r in bad),
            'gate_reasons':{s:sum(r['public_gate']['reason']==s for r in rows) for s in sorted({r['public_gate']['reason'] for r in rows})},
            'correct_applied_blocked':sum(r['request_applied'] and not r['wrong_publication'] and not r['public_gate']['allow'] for r in rows),
            'wrong_applied_blocked':sum(r['wrong_publication'] and not r['public_gate']['allow'] for r in rows),
            'api_requests':0,'model_recovery_improvement_claim':False,'scientific_gate':'HOLD'}


def run(output):
    output=Path(output); pp=output.with_suffix('.protocol.json'); tp=output.with_suffix('.jsonl')
    if any(p.exists() for p in (output,pp,tp)): raise FileExistsError('use new paths')
    write_json(pp,protocol()); rows=findings()
    with tp.open('xb') as f:
        for row in rows: f.write((json.dumps(row,ensure_ascii=False)+'\n').encode())
    write_json(output,{'version':VERSION,'backend':'offline_historical_publication_audit','protocol_sha256':sha(pp),
                       'trace_sha256':sha(tp),'summary':summarize(rows)})
    return summarize(rows)


def verify(output):
    output=Path(output); pp=output.with_suffix('.protocol.json'); tp=output.with_suffix('.jsonl')
    result=json.loads(output.read_text(encoding='utf-8')); frozen=json.loads(pp.read_text(encoding='utf-8'))
    rows=[json.loads(x) for x in tp.read_text(encoding='utf-8').splitlines()]
    def require(value):
        if not value:
            raise ValueError('publication evidence mismatch')
    require(result['version']==VERSION and result['backend']=='offline_historical_publication_audit')
    require(result['protocol_sha256']==sha(pp) and result['trace_sha256']==sha(tp) and frozen==protocol())
    require(json.dumps(rows,sort_keys=True)==json.dumps(findings(),sort_keys=True))
    require(result['summary']==summarize(rows))
    return {'status':'verified','publication_attempts':len(rows),'replayed':True,'api_requests':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',type=Path); parser.add_argument('--verify',type=Path); args=parser.parse_args()
    if bool(args.output)==bool(args.verify): parser.error('choose output or verify')
    print(json.dumps(run(args.output) if args.output else verify(args.verify)))
