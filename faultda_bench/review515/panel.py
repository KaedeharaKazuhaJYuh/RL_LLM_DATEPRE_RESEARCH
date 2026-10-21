"""Prospective common-panel checks, not a scientific or API approval service."""
from copy import deepcopy

TARGETS = {'safe_completion', 'confirmed_history_escalation', 'unresolved_escalation'}


def qualify(cases):
    """Require independently justified design eligibility, before any arm runs.

    Evidence declarations are checked structurally; this function cannot authenticate
    reviewers or their reasoning. No policy output or reference-policy prediction is
    accepted as the reason to include/exclude a case.
    """
    if not isinstance(cases, list) or not cases:
        raise ValueError('nonempty common case panel required')
    seen = set(); included = []; excluded = []; pending = []
    for c in cases:
        if not isinstance(c, dict) or not isinstance(c.get('case_id'), str) or not c['case_id'].strip():
            raise ValueError('case identifier required')
        if c['case_id'] in seen:
            raise ValueError('duplicate case')
        seen.add(c['case_id'])
        if not isinstance(c.get('cluster_id'), str) or not c['cluster_id'].strip():
            raise ValueError('source-lineage cluster required')
        verdict = c.get('design_verdict')
        if verdict not in ('include', 'exclude', 'pending'):
            raise ValueError('explicit pre-outcome design verdict required')
        if verdict == 'pending':
            pending.append(c['case_id']); continue
        e = c.get('eligibility_evidence', {})
        if (not isinstance(e, dict) or e.get('basis') != 'independent_task_review'
                or e.get('frozen_before_any_policy_outcome') is not True
                or e.get('independent_of_compared_solver') is not True
                or not isinstance(e.get('reference'), str) or not e['reference'].strip()):
            raise ValueError('eligibility cannot come from solver or observed answers')
        if verdict == 'exclude':
            if not isinstance(c.get('design_defect'), str) or not c['design_defect'].strip():
                raise ValueError('design defect required for common exclusion')
            excluded.append(c['case_id']); continue
        if c.get('interface_unambiguous') is not True or c.get('terminal_target') not in TARGETS:
            raise ValueError('unambiguous target and interface required')
        included.append(deepcopy(c))
    return {'status': 'pending_design_review' if pending else 'declarations_complete_not_authenticated',
            'common_included_cases': included, 'common_excluded_case_ids': excluded,
            'pending_case_ids': pending, 'scientific_gate': 'HOLD',
            'scientific_admission_granted': False, 'approved_transport_requests': 0}


def check_outcome_coverage(panel, arms, outcomes):
    """Prevent arm-specific deletion; invalid/role-error/censored rows stay scheduled."""
    if panel.get('pending_case_ids') or panel.get('status') != 'declarations_complete_not_authenticated':
        raise ValueError('unresolved design eligibility')
    if not isinstance(arms, list) or not arms or any(not isinstance(a, str) or not a.strip() for a in arms) or len(set(arms)) != len(arms):
        raise ValueError('unique prespecified arms required')
    cases = panel['common_included_cases']
    if not cases:
        raise ValueError('no eligible cases; no ability score')
    expected = {(a, c['case_id']) for a in arms for c in cases}
    keys = [(o['arm'], o['case_id']) for o in outcomes]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError('all arms must retain every scheduled included case exactly once')
    for o in outcomes:
        if o.get('execution_kind') not in ('scripted_program_not_model', 'model_tool_execution'):
            raise ValueError('fact diagnostics are not executed terminal actions')
    if len({o['execution_kind'] for o in outcomes}) != 1:
        raise ValueError('program and model cohorts must remain separate')
    return {'scheduled_per_arm': {a: len(cases) for a in arms},
            'declared_lineage_cluster_count': len({c['cluster_id'] for c in cases}),
            'cluster_independence_authenticated': False,
            'confidence_interval': None, 'inference': 'descriptive only; no interval implemented',
            'scientific_admission_granted': False, 'approved_transport_requests': 0}
