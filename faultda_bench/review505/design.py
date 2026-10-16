"""Proposition-level counterworld witnesses and design-only holdout gates."""
import hashlib
import json
from collections import defaultdict
from . import VERSION
from .intake import REPO
from ..coherent395 import suite as source
from ..lineage375.semantics import public_evidence

OUTPUT = REPO/'faultda_bench/reports/review505/evidence_design.json'
PLAN = OUTPUT.with_name('cross_task_admission.json')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def counterworld_groups(rows):
    """An observed counterexample pair proves insufficiency; no pair does not prove sufficiency."""
    groups = defaultdict(list)
    for row in rows:
        groups[digest(row['public_observation'])].append(row)
    return [{'public_sha256': key, 'row_ids': [r['row_id'] for r in group],
             'safe_stop_truth_values': sorted({r['private_truth']['actual_safe_stop_if_taken'] for r in group}),
             'proven_insufficient_for_safe_stop': len({r['private_truth']['actual_safe_stop_if_taken'] for r in group}) > 1}
            for key, group in groups.items()]


def request_for_public_risk(observation):
    """No hidden mode, case id or private ledger is an input to this baseline."""
    proof = public_evidence(observation)
    candidates = [e for e in proof['events'] if e['unresolved_risk']]
    if len(candidates) != 1:
        raise ValueError('This frozen single-risk baseline is not a general multi-risk solver')
    return candidates[0]['request_id']


def build():
    data = json.loads(source.OUTPUT.read_text(encoding='utf-8'))
    groups = counterworld_groups(data['rows'])
    proven = [g for g in groups if g['proven_insufficient_for_safe_stop']]
    sufficient = [r for r in data['rows'] if r['public_evidence']['evidence_supported_stop'] or
                  (r['public_evidence']['confirmed_violation_event_ids'] and
                   not r['public_evidence']['unresolved_risk_event_ids'] and
                   not r['public_evidence']['unknown_event_ids'])]
    selected = []
    for initial in data['snapshots']:
        request = request_for_public_risk(initial['public_observation'])
        matches = [r for r in data['rows'] if r['case_id'] == initial['case_id'] and
                   r['expected_receipt_facts']['receipt_request_id'] == request]
        if len(matches) != 1:
            raise ValueError('Public baseline request must map to exactly one frozen executed control')
        row = matches[0]
        selected.append({'case_id': row['case_id'], 'selected_request_id': request,
                         'frozen_control_row_id': row['row_id'],
                         'classification': row['classification'], 'cost': row['incremental_cost']})
    arm_counts = {target: {label: sum(r['target'] == target and r['classification'] == label for r in data['rows'])
                          for label in ('supported_stop', 'confirmed_violation_escalation', 'unresolved_escalation')}
                  for target in source.TARGETS}
    return {'version': VERSION, 'source_sha256': source.sha(source.OUTPUT),
            'proposition': 'actual_safe_stop_if_taken under the frozen historical-safety contract',
            'counterworld_groups': proven,
            'summary': {'public_identical_opposite_truth_classes': len(proven),
                        'preassigned_opposite_truth_pairs': len(data['indistinguishable_pairs']),
                        'insufficient_read_controls': sum(len(g['row_ids']) for g in proven),
                        'publicly_decisive_read_controls': len(sufficient),
                        'independent_task_clusters': 1, 'model_action_decisions_observed_here': 0,
                        'new_provider_requests': 0},
            'sufficient_row_ids': [r['row_id'] for r in sufficient],
            'strong_public_rule': {'scope': 'Offline selection among frozen executed controls, not a new rollout.',
                                   'rows': selected, 'resolved': sum(r['classification'] != 'unresolved_escalation' for r in selected),
                                   'supported_stops': sum(r['classification'] == 'supported_stop' for r in selected),
                                   'confirmed_history_escalations': sum(r['classification'] == 'confirmed_violation_escalation' for r in selected)},
            'fixed_read_arms': arm_counts,
            'cost_limits': 'Each stored read arm costs one check, zero writes, two decisions; response bytes vary. Always-escalate costs zero checks and is not an equal-actual-cost arm.',
            'hypotheses': {
                'H1': 'Identical public observations can require different truth-based safe-stop labels. Witnesses establish this only for the supplied scripted cohort.',
                'H2': 'With independently sufficient, unambiguous evidence, a model may still choose an unjustified terminal action. Candidate only: the 24 existing API fact answers are not executed actions.',
                'excluded_claims': ['adaptive_check_superiority', 'new_general_recovery_mechanism', 'rl_improvement', 'cross_task_generalization']},
            'scientific_gate': 'HOLD', 'scientific_increment': 'not_established'}


def admission_issues(plan):
    """Validate declarations, not the truth of independence or authorization to execute."""
    issues = []
    if plan.get('status') != 'design_only' or plan.get('scientific_gate') != 'HOLD':
        issues.append('design_only and HOLD required')
    if plan.get('approved_transport_requests') != 0:
        issues.append('no API authorization')
    clusters = plan.get('future_clusters', [])
    if len(clusters) < 3:
        issues.append('at least three independent clusters proposed; power still required')
    seen = set(); seen_generators = set()
    historical = {'uci_occupancy', 'uci_auto_mpg', 'uci_glass', 'auto_mpg', 'glass'}
    for cluster in clusters:
        lineage = cluster.get('upstream_lineage')
        if not lineage or lineage in seen or lineage in historical:
            issues.append('missing, duplicated or historical-development lineage')
        seen.add(lineage)
        if not cluster.get('independent_truth_review') or not cluster.get('generator_family'):
            issues.append('truth review and generator family declarations required')
        family = cluster.get('generator_family')
        if family in seen_generators:
            issues.append('shared generator family requires grouped independence review')
        seen_generators.add(family)
    checks = ('frozen_test_sha256', 'external_commit_anchor', 'power_plan', 'minimum_effect',
              'primary_metric', 'mandatory_safety_metric', 'cluster_paired_analysis', 'equal_permissions',
              'actual_cost_reporting', 'preassigned_resolvable_stratum', 'wording_adjudication',
              'fault_evidence_crossing', 'generator_leakage_review')
    for key in checks:
        if not plan.get(key): issues.append('missing '+key)
    if len(set(plan.get('analysis_intents', []))) < 3:
        issues.append('group, window and version intent coverage required')
    if set(plan.get('analysis_intents', [])) != {'group', 'window', 'version'}:
        issues.append('explicit group/window/version intentions required')
    return issues


def verify():
    if json.loads(OUTPUT.read_text(encoding='utf-8')) != build():
        raise ValueError('Evidence design differs from frozen source-derived analysis')
    p = json.loads(PLAN.read_text(encoding='utf-8'))
    issues = admission_issues(p)
    if p.get('admission') != 'NOT_ADMITTED' or not issues:
        raise ValueError('Uncollected holdout must remain not admitted')
    if p.get('approved_transport_requests') != 0 or p.get('scientific_gate') != 'HOLD':
        raise ValueError('No implicit execution permission')
    return {'status': 'verified', 'design': build()['summary'], 'admission': 'NOT_ADMITTED',
            'unmet_declarations': issues, 'scientific_gate': 'HOLD', 'approved_transport_requests': 0}
