"""Content binding from public receipts; deliberately no numerical checker."""
import copy

def binding(obs):
    records = None; revision = None; stages = {}; unresolved = False; origin = None
    publications = []
    for i,h in enumerate(obs['history']):
        action,r,params=h['action'],h['response'],h['params']
        if action=='stage' and r.get('ok') is True:
            stages[r['stage_id']] = copy.deepcopy(r)
        if action=='publish':
            publications.append({'history_index':i,'params':copy.deepcopy(params),'response':copy.deepcopy(r),
                                 'candidate':copy.deepcopy(stages.get(params.get('stage_id')))})
        if action=='inspect' and r.get('ok') is True and type(r.get('revision')) is int:
            records=copy.deepcopy(r['records']);revision=r['revision'];unresolved=False
            origin={'kind':'inspect','history_index':i}
        elif action=='publish':
            if r.get('ok') is not True:
                # Conservative unknown: do not infer whether a failed/timeout attempt committed.
                records=None;revision=None;unresolved=True;origin=None
            elif r.get('deduplicated') is False and type(r.get('revision')) is int:
                candidate=stages.get(params.get('stage_id'))
                if params.get('mode')=='replace' and candidate is not None:
                    records=[copy.deepcopy(candidate)];revision=r['revision'];unresolved=False
                    origin={'kind':'acknowledged_replace','history_index':i,'stage_id':params['stage_id']}
                else:records=None;revision=r['revision'];unresolved=True;origin=None
            # A dedup receipt alone cannot resolve an already unknown current report.
    return {'source':'program_reconstruction_from_public_history','active_record_evidence':records,
            'bound_revision':revision,'content_origin':origin,'unresolved_publication':unresolved,
            'all_publication_attempts':publications,
            'limits':'Assumes immutable sources, no concurrent writers, trusted ledger metadata and acknowledged CAS replace semantics. Values copied from stage/inspect remain numerically unverified. No arithmetic, private oracle, stop recommendation or history erasure.'}
