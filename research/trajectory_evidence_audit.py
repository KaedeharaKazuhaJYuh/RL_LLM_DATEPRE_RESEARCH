"""Read-only index of six historical API series. No new provider execution.

Run: python research/trajectory_evidence_audit.py > an external output path.
Pointers bind original bytes, not provider authenticity or causal attribution.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ('live_v29_deepseek.json', 'state_v30_deepseek.json',
           'stop_v31_deepseek.json', 'receipt_v35_deepseek.json',
           'postreceipt_v36_deepseek.json', 'coherent_v38_deepseek.json')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def indices(row):
    if 'request_indices' in row:
        return row['request_indices']
    if 'request_index' in row:
        return [row['request_index']]
    return [d['request_index'] for d in row['decisions']]


def audit():
    sources, rows, ready, resolved, cards = [], [], [], [], []
    for name in SOURCES:
        path = ROOT / 'faultda_bench' / 'reports' / name
        raw = path.read_bytes()
        data = json.loads(raw)
        requests = data['requests']
        reqs = []
        for i, q in enumerate(requests):
            response = q['receipt'].get('response', {})
            choices = response.get('choices', [])
            contents = [c.get('message', {}).get('content') for c in choices]
            reqs.append({'request_index': i, 'body_sha256': sha(canonical(q['body'])),
                         'response_sha256': sha(canonical(response)),
                         'response_content_preserved': any(isinstance(c, str) and c for c in contents),
                         'usage': response.get('usage'),
                         'request_sent': q['receipt'].get('request_sent')})
        linked = set()
        for i, row in enumerate(data['rows']):
            ids = indices(row)
            assert all(type(j) is int and 0 <= j < len(requests) for j in ids)
            linked.update(ids)
            item = {'source': str(path.relative_to(ROOT)).replace('\\', '/'),
                    'row_index': i, 'row_sha256': sha(canonical(row)),
                    'request_indices': ids,
                    'scope': ('actual_model_actions_on_scripted_handoff'
                              if name == 'receipt_v35_deepseek.json' else
                              'single_action_on_scripted_snapshot'
                              if name == 'stop_v31_deepseek.json' else
                              'fact_question_over_scripted_history'
                              if name in ('postreceipt_v36_deepseek.json',
                                          'coherent_v38_deepseek.json') else
                              'model_action_trajectory_with_scripted_setup'),
                    'causal_attribution': 'not_identified',
                    'independent_new_mechanism_evidence': False}
            rows.append(item)
            if name == 'stop_v31_deepseek.json' and row['predecision_evidence']['evidence_supported_stop']:
                ready.append({**item, 'arm': row['arm'], 'view': row['view'],
                              'profile': row['profile'],
                              'action': row['classification']['decision']['action'],
                              'scope_note': 'legacy scorer ready; one decision only, not eventual failure'})
            if name == 'receipt_v35_deepseek.json':
                g = row['grade']
                resolved.append({**item, 'view': row['view'],
                                 'terminal': g['terminal'],
                                 'legacy_public_stop_supported': g['public_final']['evidence_supported_stop'],
                                 'actions': [v['classification'].get('decision', {}).get('action')
                                             for v in row['decisions']]})
            if (name, i) in {('stop_v31_deepseek.json', 0),
                            ('receipt_v35_deepseek.json', 0),
                            ('receipt_v35_deepseek.json', 3)}:
                cards.append({**item, 'selection': 'purposeful diagnostic cards, not statistical sample',
                              'stored_model_contents': [
                                  {'request_index': j, 'choices':
                                   requests[j]['receipt'].get('response', {}).get('choices', [])}
                                  for j in ids],
                              'request_bodies_remain_in_original_source': True,
                              'human_review_status': 'not_arranged'})
        unlinked = sorted(set(range(len(requests))) - linked)
        generations = sorted(v['request_index'] for v in data.get('record_generations', []))
        assert unlinked == generations, 'unexplained unlinked requests'
        sources.append({'path': str(path.relative_to(ROOT)).replace('\\', '/'),
                        'sha256': sha(raw), 'rows': len(data['rows']),
                        'requests': reqs,
                        'unlinked_request_indices': unlinked,
                        'unlinked_note': 'verified exactly equal to shared-record generation indices',
                        'historical_summary': data['summary']})
    return {'schema': 'historical-trajectory-index-v1', 'sources': sources,
            'rows': rows, 'ready_snapshot_actions': ready,
            'receipt_recovery_outcomes': resolved, 'focused_cards': cards,
            'summary': {'source_series': len(sources), 'indexed_rows': len(rows),
                        'stored_requests': sum(len(s['requests']) for s in sources),
                        'ready_snapshot_rows': len(ready),
                        'ready_snapshot_stop_actions': sum(r['action'] == 'stop' for r in ready),
                        'receipt_supported_stop_but_escalate': sum(
                            r['legacy_public_stop_supported'] and r['terminal'] == 'escalate'
                            for r in resolved),
                        'new_api_calls': 0, 'scientific_gate': 'HOLD'},
            'limits': ['Selected six historical series, not exhaustive repository audit',
                       'Old scores preserved, not re-adjudicated under a new protocol',
                       'Response text presence is not authenticated provider provenance',
                       'No independent tasks or new causal effect identified',
                       'No comparison of aggregate scores across incompatible protocols']}


if __name__ == '__main__':
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
