"""Offline history indistinguishability and equal-check evidence controls."""
import argparse
import json
import tempfile
from pathlib import Path
from . import VERSION,SEMANTICS_VERSION
from .environment import prepare,observation
from .semantics import public_evidence
from ..responsibility370.semantics import private_truth
from ..responsibility370.suite import protocol as previous_protocol
from ..semantic.tasks import REPO,sha
from ..clarity.tasks import write_json
from ..multistep.suite import require,same

OUTPUT=REPO/'faultda_bench/reports/lineage_v34_results.json'
REVIEW=REPO/'faultda_bench/reports/LINEAGE_0375_INTERNAL_REVIEW.md'
MODES=('bad_never_committed','bad_committed')
ARMS=('status','inspect','receipt_lookup')

def protocol():
    old=previous_protocol();names=set(old['code_sha256'])|{'faultda_bench/lineage375/'+n for n in ('__init__.py','environment.py','semantics.py','suite.py')}
    return {'version':VERSION,'semantics_version':SEMANTICS_VERSION,'revision':'lineage_v34','views':old['views'],
            'modes':list(MODES),'arms':list(ARMS),'code_sha256':{n:sha(REPO/n) for n in sorted(names)},'internal_review_sha256':sha(REVIEW),
            'scope':'Four scripted snapshots and twelve single-extra-check controls; same final correct content/revision and same complete public history can conceal different historical violations. New request-scoped receipt is additional trusted evidence permission, not a model method. Unique request ids and no concurrency required. No provider calls or novelty claim.',
            'new_provider_requests':0,'scientific_gate':'HOLD'}

def run():
    p=protocol();snapshots=[];rows=[];pairs=[]
    with tempfile.TemporaryDirectory() as f:
        root=Path(f)
        for view,task in p['views'].items():
            initial=[]
            for mode in MODES:
                env=prepare(task,root/(view+'-'+mode),mode);obs=observation(env);pub=public_evidence(obs);priv=private_truth(env)
                require(pub['current_content_known'] and pub['current_semantic_status']=='correct','current correct already publicly established')
                require(pub['unresolved_risk_event_ids']==['history:4'] and not pub['evidence_supported_stop'],'historical attribution remains unresolved')
                require(priv['actual_safe_stop_if_taken']==(mode=='bad_never_committed'),'actual history difference')
                initial.append(obs)
                snapshots.append({'case_id':view+'|'+mode,'view':view,'mode':mode,'public_observation':obs,'public_evidence':pub,'private_truth':priv,'execution_kind':'scripted_counterexample_not_model'})
                for arm in ARMS:
                    actor=prepare(task,root/(view+'-'+mode+'-'+arm),mode)
                    require(same(observation(actor),obs),'matched initial observation for all evidence controls')
                    before=dict(actor.cost);actor.step(arm,{'request_id':'witness-bad'} if arm=='receipt_lookup' else {})
                    post=observation(actor);proof=public_evidence(post);actual=private_truth(actor)
                    require(actor.cost['checks']-before['checks']==1 and actor.cost['mutations']==before['mutations'],'one extra read, zero extra write')
                    if arm=='receipt_lookup':
                        require(proof['evidence_supported_stop']==(mode=='bad_never_committed'),'request evidence separates histories')
                        require(len(proof['confirmed_violation_event_ids'])==int(mode=='bad_committed') and not proof['unresolved_risk_event_ids'],'same event resolves exactly once')
                    else:require(proof['unresolved_risk_event_ids']==['history:4'] and not proof['evidence_supported_stop'],'current-state read is not historical provenance')
                    rows.append({'view':view,'mode':mode,'arm':arm,'public_observation':post,'public_evidence':proof,'private_truth':actual,
                                 'extra_cost':{k:actor.cost[k]-before[k] for k in before},'execution_kind':'scripted_control_not_model'})
            require(same(initial[0],initial[1]),'complete public histories and current state indistinguishable')
            pairs.append({'view':view,'public_observations_equal':True,'final_correct_report_equal':True,'final_revision':3,'actual_history_differs':True})
    return {'version':VERSION,'protocol':p,'snapshots':snapshots,'rows':rows,'indistinguishable_pairs':pairs,
            'summary':{'scripted_snapshots':4,'scripted_controls':12,'same_public_history_pairs':2,'new_provider_requests':0,
                       'by_read':{a:{'executions':4,'public_safe_stop':sum(r['public_evidence']['evidence_supported_stop'] for r in rows if r['arm']==a),
                                     'confirmed_historical_violation':sum(bool(r['public_evidence']['confirmed_violation_event_ids']) for r in rows if r['arm']==a),
                                     'unresolved':sum(bool(r['public_evidence']['unresolved_risk_event_ids']) for r in rows if r['arm']==a),
                                     'extra_checks':sum(r['extra_cost']['checks'] for r in rows if r['arm']==a),
                                     'extra_response_bytes':sum(r['extra_cost']['response_bytes'] for r in rows if r['arm']==a)} for a in ARMS},
                       'independent_review':'pending','scientific_gate':'HOLD'}}

def verify():
    require(same(json.loads(OUTPUT.read_text(encoding='utf-8')),run()),'history witness and actual receipt replay')
    return {'status':'verified','scripted_snapshots':4,'scripted_controls':12,'new_provider_requests':0,'scientific_gate':'HOLD'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');a=p.parse_args()
    if a.freeze:write_json(OUTPUT,run())
    print(json.dumps(verify()))
