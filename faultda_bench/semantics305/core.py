"""Public prompt interventions and independently scored timestamp facts."""
import copy
from datetime import datetime, timedelta, timezone

from ..rowdiag import boundary as prior
from ..multistep.suite import require

VIEWS=('utc_end','plus8_end','minus5_end','plus8_all')
ANALYSIS = ('Tool parameter clarification: deduplicate_keys collapses identical dimension key/group '
    'matches only for a group join; it never removes fact rows. It has no numerical effect for window '
    'or version sums. For this window sum, count every nonmissing fact row in [start,end) exactly once.')
IDEMPOTENCY = ('Publish feedback clarification: deduplicated is exclusively about request_id retry '
    'idempotency. False means a new request was applied, not that analysis rows were left duplicated. '
    'It provides no judgement about the numerical correctness of the report.')
CARRY = ('Maintain the earlier model-generated row verification as a working record tied to the '
    'supplied contract and version. Before stop or publish, compare the active report or exact candidate '
    'against that record and the retrieved raw evidence. Retain or revise the record only on the basis '
    'of public evidence; do not discard it merely because checks are exhausted. It is not an evaluator '
    'verdict and may itself be wrong. Never regard a matching tool flag as independent numerical proof.')
NORMALIZE = ('Use an explicit UTC conversion before the comparisons. Return exactly version, start_utc, '
    'end_utc, rows, total. Every row must contain exactly id, included, value, ge_start, lt_end, time_utc. '
    'The three UTC fields are ISO8601 strings with zero UTC offset representing the supplied instants. '
    'Compute ge_start and lt_end using these UTC instants. This schema replaces the previous schema.')


def view_task(base, view):
    require(view in VIEWS,'timezone view')
    task=copy.deepcopy(base); zone=timezone(timedelta(hours=8 if view!='minus5_end' else -5))
    if view!='utc_end':
        task['contract']['end']=datetime.fromisoformat(task['contract']['end']).astimezone(zone).isoformat()
    if view=='plus8_all':
        task['contract']['start']=datetime.fromisoformat(task['contract']['start']).astimezone(zone).isoformat()
        for rows in task['versions'].values():
            for row in rows: row['time']=datetime.fromisoformat(row['time']).astimezone(zone).isoformat()
    task['id']=base['id']+'-'+view
    return task


def diagnostic_body(obs, form):
    require(form in ('comparisons','normalized'),'diagnostic format')
    request=prior.row_body(obs,'comparisons')
    if form=='normalized': request['messages'][0]['content']+=' '+NORMALIZE
    return request


def diagnostic_score(answer, task, form):
    if form=='comparisons':
        result=prior.row_score(answer,task,'comparisons'); result['utc_facts']=None
        return result
    schema=(isinstance(answer,dict) and set(answer)=={'version','rows','total','start_utc','end_utc'}
        and isinstance(answer['start_utc'],str) and isinstance(answer['end_utc'],str)
        and isinstance(answer['rows'],list) and all(isinstance(r,dict)
        and set(r)=={'id','included','value','ge_start','lt_end','time_utc'}
        and isinstance(r['time_utc'],str) for r in answer['rows']))
    if not schema:
        result=prior.row_score(None,task,'comparisons'); result['utc_facts']=False; return result
    stripped={'version':answer['version'],'total':answer['total'],
        'rows':[{k:r[k] for k in ('id','included','value','ge_start','lt_end')} for r in answer['rows']]}
    result=prior.row_score(stripped,task,'comparisons')
    def instant_equal(text, original):
        try:
            instant=datetime.fromisoformat(text)
            return instant.tzinfo is not None and instant.utcoffset()==timedelta(0) and instant==datetime.fromisoformat(original)
        except (ValueError,TypeError): return False
    rows=task['versions'][prior.expected(task)['version']]
    result['utc_facts']=(result['schema'] and instant_equal(answer['start_utc'],task['contract']['start'])
        and instant_equal(answer['end_utc'],task['contract']['end']) and len(answer['rows'])==len(rows)
        and all(r['id']==source['id'] and instant_equal(r['time_utc'],source['time']) for r,source in zip(answer['rows'],rows)))
    return result


def action_body(obs, evidence, cell):
    request=prior.prior.request_body(obs,'action',evidence)
    request['messages'][0]['content']+=' The experiment permits at most six further tool actions; remaining horizon is supplied separately from tool budgets.'
    for flag,text in (('analysis',ANALYSIS),('idempotency',IDEMPOTENCY),('carry',CARRY)):
        require(type(cell[flag]) is bool,'factor type')
        if cell[flag]: request['messages'][0]['content']+=' '+text
    return request
