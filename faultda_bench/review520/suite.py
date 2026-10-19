"""Read-only qualification on old scripted views, never a new model trial."""
import json
from . import VERSION, actor
from ..coherent395 import suite as old
from ..lineage375.semantics import public_evidence
from ..review515.intake import sha

SOURCE = old.OUTPUT


def build():
    source = json.loads(SOURCE.read_text(encoding='utf-8')); rows = []
    for r in source['rows']:
        obs = r['public_observation']; before = old.digest(obs)
        query = 'history:' + str(len(obs['history']) - 1)
        target = r['expected_receipt_facts']['receipt_event_id']
        view = actor.build_view(obs, query, target)
        if old.digest(obs) != before: raise ValueError('source observation mutated')
        # Permissions are checked OUTSIDE the prospective interface. No solver's
        # stop/violation answers are silently given to a future model as metadata.
        if public_evidence(obs) != r['public_evidence']:
            raise ValueError('legacy public permissions changed')
        rows.append({'row_id': r['row_id'], 'source_observation_sha256': before,
                     'structured_view': view,
                     'old_public_evidence_sha256': old.digest(r['public_evidence']),
                     'old_private_truth_sha256': old.digest(r['private_truth']),
                     'source_observation_unchanged': True,
                     'legacy_permissions_unchanged': True})
    return {'version': VERSION, 'source_sha256': sha(SOURCE), 'rows': rows,
            'summary': {'scripted_derived_views': len(rows),
                        'independent_task_clusters': 1,
                        'new_model_tool_executions': 0, 'new_physical_executions': 0,
                        'new_provider_requests': 0, 'old_primary_scores_replaced': False},
            'scope': 'Derived explicit request/event/actor bindings for existing pinned scripted observations. No new recovery execution, API answer, independent task or human interface-validity approval.',
            'scientific_gate': 'HOLD', 'new_interface_independent_review': 'pending'}
