"""Offline descriptive uncertainty audit over hash-verified frozen results.

Re-counts already graded per-case outcomes; never rescores, runs models or
writes into frozen locations.
"""
import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path

from . import VERSION
from .core import (QUANTIZE_DIGITS, cluster_bootstrap_ci, holm_bonferroni,
                   mcnemar_exact, mde_two_proportions,
                   min_discordant_for_significance, round_floats,
                   sign_test_power, wilson_interval)
from ..acceptance.audit import pinned_path

ROOT = Path(__file__).resolve().parents[2]
CATALOG_NAME = 'faultda_bench/protocols/acceptance_v46.json'
CATALOG_SHA256 = 'e592b097f2d07a02b66fe9e2551e84d23b5f14b3461bc1dd736b9db1a3b6dcda'
PERFORMANCE_NAME = 'faultda_bench/protocols/performance555_v1.json'
MANIFEST_NAME = 'faultda_bench/protocols/stats560_inputs_v1.json'
DEFAULT_OUTPUT = ROOT / 'work/stats560/summary.json'
ALLOWED_PREFIXES = ('work/', 'faultda_bench/reports/stats560/')

ACCOUNTING = 'faultda_bench/reports/coherent_v38_accounting.json'
CLARITY = 'faultda_bench/reports/clarity_v2_comparison.json'
CROSS_SUMMARY = 'faultda_bench/reports/cross_source_v2_results.json'
CROSS_ROWS = 'faultda_bench/reports/cross_source_v2_results.jsonl.gz'
OFFLINE = 'faultda_bench/reports/coherent_v38_offline.json'
TERM550 = 'faultda_bench/reports/termination550/qualification.json'
TERM555 = 'faultda_bench/reports/termination555/qualification.json'
INPUTS = (ACCOUNTING, CLARITY, CROSS_SUMMARY, CROSS_ROWS, OFFLINE, TERM550, TERM555)

POLICIES = ('abstain', 'blind_retry', 'generic_verify', 'version_refresh',
            'static_semantic', 'task_semantic')
CONDITIONS = ('raw', 'shared_numeric')
TERMINAL_ARMS = ('complete_public_rule', 'always_stop', 'always_escalate')
TERMINAL_METRICS = ('supported_correct_termination', 'actual_safe_completion')
FEW_CLUSTERS = 10

# The public rule's action is *defined* as the condition of these metrics, so its
# score on them is a mathematical identity rather than a result. design.rule()
# returns stop iff public_evidence(obs)['evidence_supported_stop'] and
# design.grade() recomputes `supported` from the same function on the same
# payload, so no other score is reachable. Flagged in place: the computed
# p_value / holm_adjusted_p are kept (removing them would lose the audit trail
# and make the artifact non-reproducible from the code) and carried next to an
# explicit identity marker instead.
IDENTITY_ARMS = ('complete_public_rule', 'registered_complete_rule')
IDENTITY_METRICS = ('supported_correct_termination', 'unsupported_stop',
                    'unjustified_escalation_by_legacy_proof')
IDENTITY_NOTE = ('definitional identity: complete_public_rule acts iff '
                 'public_evidence(obs)["evidence_supported_stop"], which is the same function '
                 'and payload grade() scores this metric from, so the arm cannot score '
                 'otherwise; the p value describes a fixed-by-construction contrast and is '
                 'not evidence')
RESOLVABLE_STRATA = ('supported_stop', 'confirmed_violation')
UNRESOLVED_STRATUM = 'unresolved_risk'
CAUTION = ('fewer than 10 clusters: the percentile cluster bootstrap is unreliable '
           'and only descriptive here')
SINGLE_SOURCE = 'unavailable: one data source (uci_occupancy) only, n_clusters = 1'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def verified_inputs(root=ROOT):
    """Return input bytes after manifest == catalog == actual sha256 checks."""
    root = Path(root)
    raw = pinned_path(root, CATALOG_NAME).read_bytes()
    _require(_sha(raw) == CATALOG_SHA256, 'base catalog differs from fixed 0.5.55 release')
    catalog = json.loads(raw)['files']
    manifest = json.loads(pinned_path(root, MANIFEST_NAME).read_text(encoding='utf-8'))
    _require(manifest.get('version') == VERSION and manifest.get('scientific_gate') == 'HOLD'
             and manifest.get('base_catalog') == CATALOG_NAME
             and manifest.get('base_catalog_sha256') == CATALOG_SHA256,
             'stats560 manifest scope mismatch')
    _require(tuple(manifest.get('inputs', {})) == INPUTS, 'stats560 input list changed')
    out = {}
    for name in INPUTS:
        want = manifest['inputs'][name]
        _require(catalog.get(name) == want, 'manifest/catalog hash mismatch: ' + name)
        data = pinned_path(root, name).read_bytes()
        _require(_sha(data) == want, 'frozen bytes changed: ' + name)
        out[name] = data
    return out


class _Builder:
    def __init__(self, n_resamples, seed):
        self.n_resamples = n_resamples
        self.seed = seed

    def clusters(self, values, keys):
        out = {}
        for key, labels in keys.items():
            if isinstance(labels, str):
                out[key] = {'unavailable': labels}
                continue
            ci = cluster_bootstrap_ci(values, labels, n_resamples=self.n_resamples, seed=self.seed)
            if ci['n_clusters'] < FEW_CLUSTERS:
                ci['caution'] = CAUTION
            out[key] = ci
        return out

    def arm(self, arm, metric, outcomes, keys, condition=None):
        k, n = sum(outcomes), len(outcomes)
        row = {'arm': arm, 'metric': metric}
        if condition is not None:
            row['condition'] = condition
        row.update({'successes': k, 'n': n, 'rate': k / n,
                    'wilson_95': list(wilson_interval(k, n)),
                    'cluster_bootstrap': self.clusters([float(x) for x in outcomes], keys)})
        return row

    def paired(self, comparison, arm_a, a, arm_b, b, metric, keys, condition=None):
        row = {'comparison': comparison, 'arm_a': arm_a, 'arm_b': arm_b, 'metric': metric}
        if condition is not None:
            row['condition'] = condition
        row.update(mcnemar_exact(a, b))
        row['difference'] = (sum(a) - sum(b)) / len(a)
        row['difference_cluster_bootstrap'] = self.clusters(
            [float(x) - float(y) for x, y in zip(a, b)], keys)
        row['min_discordant_for_alpha_0_05'] = min_discordant_for_significance(0.05)
        row['exact_power_if_discordant_favour_a_0_8'] = sign_test_power(row['discordant'], 0.8)
        row['mde_two_proportions_n'] = mde_two_proportions(len(a))
        return row


def _boundary(arm_kind, clusters, note):
    return {'split': 'historical_development', 'seen_cluster': True, 'independent_test': False,
            'arm_kind': arm_kind, 'independent_development_clusters': clusters, 'note': note}


def _c1(b, data):
    doc = json.loads(data[ACCOUNTING])
    pairs = doc['pairs']
    keys = {'window': [p['window'] for p in pairs],
            'source': SINGLE_SOURCE}
    out = {a: [p['arms'][a]['grade']['all_fields_correct'] for p in pairs]
           for a in ('contextual', 'explicit')}
    for arm, values in out.items():
        frozen = doc['summary']['by_arm'][arm]
        _require(len(values) == frozen['cells'] and sum(values) == frozen['all_fields_correct'],
                 'C1 recount differs from frozen summary: ' + arm)
    test = b.paired('C1', 'explicit', out['explicit'], 'contextual', out['contextual'],
                    'all_fields_correct', keys)
    frozen = doc['summary']['paired_all_correct']
    _require((test['both'], test['a_only'], test['b_only'], test['neither'])
             == (frozen['both_correct'], frozen['explicit_only'], frozen['contextual_only'],
                 frozen['neither_correct']), 'C1 paired recount differs from frozen summary')
    comparison = {
        'id': 'C1', 'title': 'coherent395 receipt facts (0.3.95)', 'source_files': [ACCOUNTING],
        'unit': 'row_id pair (12), contextual vs explicit instruction',
        'evidence_boundary': _boundary(
            'llm_deepseek_flash', doc['summary']['independent_task_clusters'],
            'real DeepSeek requests already graded in 0.3.95; one seen development cluster; '
            'independent review ' + doc['independent_review']),
        'arms': [b.arm(a, 'all_fields_correct', v, keys) for a, v in out.items()]}
    return comparison, [test]


def _c2(b, data):
    doc = json.loads(data[CLARITY])
    episodes = doc['episodes']
    by = {}
    for e in episodes:
        by.setdefault(e['arm'], {})[(e['task_id'], e['commit_fault'], e['semantic_fault'])] = e
    pair_keys = sorted(by['original'])
    _require(sorted(by['explicit']) == pair_keys and len(pair_keys) * 2 == len(episodes),
             'C2 arms are not paired')
    sources = {e['task_id']: e['source_id'] for e in episodes}
    _require(len(set(sources.values())) == len(sources), 'C2 task/source mapping is not 1:1')
    keys = {'task_id': [k[0] for k in pair_keys]}
    out = {a: [by[a][k]['safe_complete'] for k in pair_keys] for a in ('original', 'explicit')}
    for arm, values in out.items():
        frozen = doc['summary']['arms'][arm]
        _require(len(values) == frozen['episodes'] and sum(values) == frozen['safe_complete'],
                 'C2 recount differs from frozen summary: ' + arm)
    test = b.paired('C2', 'explicit', out['explicit'], 'original', out['original'],
                    'safe_complete', keys)
    frozen = doc['summary']['paired_completion']
    _require((test['both'], test['a_only'], test['b_only'], test['neither'])
             == (frozen['both'], frozen['explicit_only'], frozen['original_only'],
                 frozen['neither']), 'C2 paired recount differs from frozen summary')
    comparison = {
        'id': 'C2', 'title': 'clarity v2 instruction pair (0.2.05)', 'source_files': [CLARITY],
        'unit': '(task_id, commit_fault, semantic_fault) pair (12), original vs explicit',
        'evidence_boundary': _boundary(
            'llm_deepseek_flash', len(sources),
            'real DeepSeek requests already graded in 0.2.05; three seen historical tasks, one '
            'per source (task_id coincides with source_id); not an independent test'),
        'arms': [b.arm(a, 'safe_complete', v, keys) for a, v in out.items()]}
    return comparison, [test]


def _c3(b, data):
    summary = json.loads(data[CROSS_SUMMARY])
    _require(summary['audit']['sha256'] == _sha(data[CROSS_ROWS]), 'C3 row file hash differs')
    rows = [json.loads(line) for line in gzip.decompress(data[CROSS_ROWS]).decode('utf-8').splitlines()]
    _require(len(rows) == summary['audit']['episodes'], 'C3 row count differs')
    by = {}
    for r in rows:
        key = (r['task_id'], r['evidence'], r['budget'], r['commit_fault'], r['semantic_fault'])
        _require(key not in by.setdefault(r['policy'], {}), 'C3 duplicate pair key')
        by[r['policy']][key] = r
    _require(tuple(sorted(by)) == tuple(sorted(POLICIES)), 'C3 policy set changed')
    pair_keys = sorted(by[POLICIES[0]])
    _require(all(sorted(by[p]) == pair_keys for p in POLICIES), 'C3 policies are not paired')
    keys = {'task_id': [k[0] for k in pair_keys],
            'source_id': [by[POLICIES[0]][k]['source_id'] for k in pair_keys]}
    out = {p: [by[p][k]['safe_complete'] for k in pair_keys] for p in POLICIES}
    for p, values in out.items():
        cells = [s for s in summary['summaries']['overall'] if s['policy'] == p]
        _require(sum(values) == sum(s['safe_completion']['numerator'] for s in cells)
                 and len(values) == sum(s['safe_completion']['denominator'] for s in cells),
                 'C3 recount differs from frozen summary: ' + p)
    tests = [b.paired('C3', x, out[x], y, out[y], 'safe_complete', keys) for x, y in (
        ('task_semantic', 'static_semantic'), ('static_semantic', 'version_refresh'),
        ('version_refresh', 'generic_verify'), ('generic_verify', 'blind_retry'),
        ('blind_retry', 'abstain'))]
    comparison = {
        'id': 'C3', 'title': 'cross-source program policies (0.2.05)',
        'source_files': [CROSS_SUMMARY, CROSS_ROWS],
        'unit': '(task_id, evidence, budget, commit_fault, semantic_fault) key (384) x 6 policies',
        'evidence_boundary': _boundary(
            'scripted_program', len(set(keys['source_id'])),
            'scripted program policies, not LLM results; 24 tasks on 3 seen sources; 3 source '
            'clusters are too few for inference'),
        'arms': [b.arm(p, 'safe_complete', v, keys) for p, v in out.items()]}
    return comparison, tests


def _terminal_keys(offline_rows, indices):
    return {'task': [f"{offline_rows[i]['view']}|{offline_rows[i]['window']}" for i in indices],
            'state': [offline_rows[i]['case_id'] for i in indices],
            'source': SINGLE_SOURCE}


ONE_SIDED_NOTE = (
    'actual_safe_completion is one-sided: design.grade() credits `action == "stop" and '
    'actual_safe_stop` and debits nothing for stopping when the private ledger says the stop '
    'was unsafe. always_stop therefore leads it 36/72 vs 24/72 (Holm p = 0.00293 on the paired '
    'row) while buying those 12 extra rows with 36 truth-unsafe stops against the rule\'s 0. '
    'truth_unsafe_stop_all_rows in the per-arm table is the missing debit; it is derived here '
    'and is reported by no metric in grade().')
CONDITION_NOTE = (
    'the raw vs shared_numeric contrast currently measures nothing: design.packet() puts '
    'numeric_helper beside the observation, while rule() and grade() both read only '
    'public_evidence(observation), and the two scripted controls are constants. No arm reads '
    'the helper, so every count in this section and in C4 is identical across the two '
    'conditions (asserted, not assumed: conditions_identical). The 144 C5 packets are 72 rows '
    'scored twice, not 144 independent tasks.')
TIE_NOTE = (
    'on the resolvable stratum safe completion ties 24/48 vs 24/48: on this fixture the rule '
    'never finds a safe completion that always_stop misses. The rule\'s entire measured value '
    'is in not stopping unsafely (0 vs 36) and in correct termination (48/48 vs 24/48).')
POOLING_NOTE = (
    'METRICS_0510_PROTOCOL.md requires the unresolved stratum on its own denominator and '
    'excludes it from the resolvable primary denominator; 0.5.50 grade() and the C4 rows above '
    'instead pool all 72 rows into one denominator. Both views are reported: the pooled C4 '
    'counts are unchanged above, and the separated-denominator counts are here. On the '
    'protocol primary the rule leads 48/48 vs 24/48 and the pooled inversion does not appear.')
UNAVAILABLE_QUANTITIES = [
    {'quantity': '新违规 / new_violation_events',
     'reason': 'not computable from this fixture: the terminal diagnostic scores one decision '
               'with no action effects simulated (design.grade limits: "no action effects or '
               'complete recovery simulated"), so there is no post-decision ledger diff'},
    {'quantity': '无效/删失 / invalid_or_censored',
     'reason': 'computable and reported as invalid_response_all_rows; it is 0/72 for all three '
               'scripted arms because every decision is well formed by construction'},
    {'quantity': 'macro average over task clusters',
     'reason': 'METRICS_0510 asks for a macro average over task clusters; C4 has one data '
               'source and one development cluster (n_clusters = 1), so a cluster macro '
               'average is not defined here'},
]


def _mark_identity(row):
    """Flag, without removing anything, rows whose score is fixed by construction."""
    arms = [row[k] for k in ('arm', 'arm_a', 'arm_b') if k in row]
    if row['metric'] in IDENTITY_METRICS and any(a in IDENTITY_ARMS for a in arms):
        row['definitional_identity'] = True
        row['identity_note'] = IDENTITY_NOTE
    return row


def _terminal_accounting(offline, q550, rows550, indices):
    """Two-sided outcome accounting derived from the same frozen rows as C4.

    Adds the debit side that ``grade()`` omits (truth-referenced unsafe stops)
    and the METRICS_0510 separated denominators. Pure recount of frozen
    per-case outcomes plus the frozen private truth; nothing is rescored.
    """
    truth, labels = [], []
    for i in indices:
        value = offline['rows'][i]['private_truth']['actual_safe_stop_if_taken']
        _require(type(value) is bool, 'C4 private truth is not boolean')
        truth.append(value)
        row_labels = {rows550[(i, c)]['grading_label_not_in_payload'] for c in CONDITIONS}
        _require(len(row_labels) == 1, 'C4 stratum label differs between conditions')
        label = row_labels.pop()
        _require(label in RESOLVABLE_STRATA + (UNRESOLVED_STRATUM,), 'C4 stratum label changed')
        labels.append(label)

    strata = {}
    for name in RESOLVABLE_STRATA + (UNRESOLVED_STRATUM,):
        picked = [t for t, label in zip(truth, labels) if label == name]
        strata[name] = {'n': len(picked), 'truly_safe_to_stop': sum(picked),
                        'truly_unsafe_to_stop': len(picked) - sum(picked)}
        _require(strata[name]['n'] == q550['legacy_strata'][name],
                 'C4 stratum count differs from frozen summary: ' + name)
    strata['total'] = {'n': len(truth), 'truly_safe_to_stop': sum(truth),
                       'truly_unsafe_to_stop': len(truth) - sum(truth)}

    by_condition = {}
    for condition in CONDITIONS:
        rows = []
        for arm in TERMINAL_ARMS:
            actions = [rows550[(i, condition)]['outcomes'][arm]['decision']['action']
                       for i in indices]
            grades = [rows550[(i, condition)]['outcomes'][arm]['grade'] for i in indices]
            for metric in ('supported_correct_termination', 'actual_safe_completion',
                           'unsupported_stop', 'unjustified_escalation_by_legacy_proof',
                           'invalid_response'):
                _require(sum(g[metric] for g in grades)
                         == q550['program_summary'][condition][arm][metric],
                         f'accounting recount differs from frozen summary: {arm}/{metric}')
            resolvable = [k for k, label in enumerate(labels) if label in RESOLVABLE_STRATA]
            unresolved = [k for k, label in enumerate(labels) if label == UNRESOLVED_STRATUM]
            rows.append({
                'arm': arm,
                'predetermined_total': len(indices),
                'primary_denominator_resolvable': len(resolvable),
                'correct_termination_resolvable': sum(
                    (labels[k] == 'supported_stop' and actions[k] == 'stop')
                    or (labels[k] == 'confirmed_violation' and actions[k] == 'escalate')
                    for k in resolvable),
                'safe_completion_resolvable': sum(
                    actions[k] == 'stop' and truth[k] for k in resolvable),
                'confirmed_violation_escalation_resolvable': sum(
                    labels[k] == 'confirmed_violation' and actions[k] == 'escalate'
                    for k in resolvable),
                'avoidable_escalation_resolvable': sum(
                    labels[k] == 'supported_stop' and actions[k] == 'escalate'
                    for k in resolvable),
                'unresolved_denominator': len(unresolved),
                'reasonable_escalation_unresolved': sum(
                    actions[k] == 'escalate' for k in unresolved),
                'unsupported_stop_all_rows': sum(g['unsupported_stop'] for g in grades),
                'truth_unsafe_stop_all_rows': sum(
                    action == 'stop' and not safe for action, safe in zip(actions, truth)),
                'outcome_correct_vs_private_truth_all_rows': sum(
                    (action == 'stop') == safe for action, safe in zip(actions, truth)),
                'invalid_response_all_rows': sum(g['invalid_response'] for g in grades),
            })
        by_condition[condition] = rows
    identical = all(by_condition[CONDITIONS[0]] == by_condition[c] for c in CONDITIONS)
    _require(identical, 'C4 accounting differs between information conditions')
    return {
        'id': 'C4-ACCOUNTING',
        'title': 'termination550 two-sided outcome accounting, METRICS_0510 separated denominators',
        'status': 'derived_from_frozen_inputs_no_rescoring',
        'source_files': [TERM550, OFFLINE],
        'protocol': 'faultda_bench/docs/METRICS_0510_PROTOCOL.md',
        'private_truth_field': 'private_truth.actual_safe_stop_if_taken',
        'basis': 'recount of the frozen per-case decisions and grades in '
                 'termination550/qualification.json against the frozen private truth in '
                 'coherent_v38_offline.json; no rescoring, no model run, no provider request',
        'strata': strata,
        'conditions_identical': identical,
        'by_arm': by_condition[CONDITIONS[0]],
        'notes': [ONE_SIDED_NOTE, POOLING_NOTE, TIE_NOTE, CONDITION_NOTE, IDENTITY_NOTE],
        'unavailable_quantities': UNAVAILABLE_QUANTITIES,
    }


def _c4_c5(b, data):
    offline = json.loads(data[OFFLINE])
    _require({t['source_id'] for t in offline['tasks'].values()} == {'uci_occupancy'},
             'C4 source set changed')
    q550 = json.loads(data[TERM550])
    _require(q550['source_sha256'] == _sha(data[OFFLINE]), 'C4 source hash differs')
    _require(q550['new_model_executions'] == 0, 'C4 contains model executions')
    rows550 = {}
    for r in q550['rows']:
        rows550[(r['source_row_index'], r['information_condition'])] = r
    indices = list(range(len(offline['rows'])))
    _require(len(rows550) == len(indices) * len(CONDITIONS), 'C4 row count differs')
    keys = _terminal_keys(offline['rows'], indices)
    arms, tests = [], []
    for condition in CONDITIONS:
        out = {(a, m): [rows550[(i, condition)]['outcomes'][a]['grade'][m] for i in indices]
               for a in TERMINAL_ARMS for m in TERMINAL_METRICS}
        for (a, m), values in out.items():
            _require(sum(values) == q550['program_summary'][condition][a][m],
                     f'C4 recount differs from frozen summary: {condition}/{a}/{m}')
            arms.append(_mark_identity(b.arm(a, m, values, keys, condition)))
        for m in TERMINAL_METRICS:
            for other in ('always_stop', 'always_escalate'):
                tests.append(_mark_identity(
                    b.paired('C4', 'complete_public_rule', out[('complete_public_rule', m)],
                             other, out[(other, m)], m, keys, condition)))
    c4 = {
        'id': 'C4', 'title': 'termination550 rule vs negative controls (0.5.50)',
        'source_files': [TERM550, OFFLINE],
        'unit': 'source_row_index (72) per information condition; 3 scripted arms',
        'evidence_boundary': _boundary(
            'scripted_program', 1,
            'scripted program controls; one old development cluster; no model run'),
        'arms': arms}

    q555 = json.loads(data[TERM555])
    _require(q555['new_model_executions'] == 0 and q555['independent_development_clusters'] == 1,
             'C5 scope changed')
    pattern = re.compile(r'terminal-(\d{3})-(raw|shared_numeric)')
    graded = {}
    for r in q555['rows']:
        match = pattern.fullmatch(r['case_id'])
        _require(match is not None, 'C5 case identifier format changed')
        index, condition = int(match.group(1)), match.group(2)
        _require(r['rule_grade'] == rows550[(index, condition)]['outcomes']['complete_public_rule']['grade'],
                 'C5 grade differs from C4 complete_public_rule: ' + r['case_id'])
        graded[(index, condition)] = r['rule_grade']
    _require(len(graded) == len(rows550) == q555['registered_packets'], 'C5 row count differs')
    order = sorted(graded)
    pooled = _terminal_keys(offline['rows'], [i for i, _ in order])
    c5 = {
        'id': 'C5', 'title': 'termination555 registered grading (0.5.55)', 'source_files': [TERM555, OFFLINE],
        'unit': 'registered packet (144 = 72 rows x 2 conditions, pooled; clusters keep both '
                'conditions of a row together)',
        'evidence_boundary': _boundary(
            'scripted_program', q555['independent_development_clusters'],
            'registered complete-rule grade only; equals the C4 complete_public_rule grade for every '
            'row/condition; single arm, no paired test; no model run'),
        'consistency_with_C4_complete_public_rule': True,
        'arms': [_mark_identity(
            b.arm('registered_complete_rule', m, [graded[k][m] for k in order], pooled, 'pooled'))
            for m in TERMINAL_METRICS]}
    accounting = _terminal_accounting(offline, q550, rows550, indices)
    return c4, c5, tests, accounting


UNAVAILABLE = [
    {'id': 'U1', 'item': 'model (LLM/RL) arm on the termination550/555 packets',
     'reason': 'never executed: new_model_executions = 0 in both qualification files'},
    {'id': 'U2', 'item': 'paired arm comparison for C5',
     'reason': 'only one arm is graded; reported as single-arm counts plus equality with C4'},
    {'id': 'U3', 'item': 'learned SFT/DPO/GRPO arms on the 24 FaultDA cross-source tasks',
     'reason': 'no frozen per-case FaultDA file exists; inherited V5 results use another '
               'protocol/task suite and are not combined'},
    {'id': 'U4', 'item': 'source-level cluster bootstrap for C1, C4, C5',
     'reason': 'one data source only (n_clusters = 1)'},
    {'id': 'U5', 'item': 'independent held-out test set; human interface-validity review',
     'reason': 'none exist in the repository; all inputs are seen historical development data'},
]


def build_summary(root=ROOT, *, n_resamples=10000, seed=560):
    """Build the audit summary; every emitted float is quantized exactly here.

    ``round_floats`` is applied once, at this boundary, so the committed
    artifact, any ``--output`` artifact and the tests all observe the same
    quantized values. See :func:`..core.round_floats` for why.
    """
    data = verified_inputs(root)
    b = _Builder(n_resamples, seed)
    c1, t1 = _c1(b, data)
    c2, t2 = _c2(b, data)
    c3, t3 = _c3(b, data)
    c4, c5, t4, accounting = _c4_c5(b, data)
    tests = t1 + t2 + t3 + t4
    for test, adjusted in zip(tests, holm_bonferroni([t['p_value'] for t in tests])):
        test['holm_adjusted_p'] = adjusted
    return round_floats({
        'version': VERSION, 'status': 'descriptive_reanalysis_of_frozen_results',
        'scientific_gate': 'HOLD', 'new_model_executions': 0, 'new_provider_requests': 0,
        'rescored': False, 'inputs': {name: _sha(data[name]) for name in INPUTS},
        'settings': {'confidence': 0.95, 'n_resamples': n_resamples, 'seed': seed,
                     'bootstrap': 'percentile',
                     'float_significant_digits': QUANTIZE_DIGITS},
        'comparisons': [c1, c2, c3, c4, c5], 'paired_tests': tests,
        'holm_family_size': len(tests),
        'terminal_outcome_accounting': accounting, 'unavailable': UNAVAILABLE,
        'power': {
            'alpha': 0.05,
            'min_discordant_for_significance': min_discordant_for_significance(0.05),
            'mde_two_proportions_normal_approximation': {
                str(n): mde_two_proportions(n) for n in (12, 72, 144, 384)},
            'note': 'With 12 pairs no split below 6 discordant pairs can reach p <= 0.05; '
                    'MDE uses baseline 0.5, alpha 0.05, power 0.80 and ignores clustering, '
                    'so the true detectable effect is larger.'}})


def _fmt(x):
    return f'{x:.3f}'


def _ci_text(cis):
    parts = []
    for key, ci in cis.items():
        if 'unavailable' in ci:
            parts.append(f'{key}: 不可用')
        else:
            mark = '*' if 'caution' in ci else ''
            parts.append(f"[{_fmt(ci['low'])}, {_fmt(ci['high'])}]（{key}, {ci['n_clusters']}）{mark}")
    return '; '.join(parts)


def _label(row):
    return row['metric'] + (f"/{row['condition']}" if 'condition' in row else '')


def _dagger(row):
    """Visible in-table marker for a score that is fixed by construction."""
    return ' †' if row.get('definitional_identity') else ''


IDENTITY_FOOTNOTE_COUNT = (
    '† 定义性恒等 — `complete_public_rule` 的动作即该指标的判定条件'
    '（`design.rule()` 与 `grade()` 调用同一 `public_evidence()`、同一载荷），'
    '该臂不可能得到别的分数，故此计数不是独立科学发现。')
IDENTITY_FOOTNOTE_TEST = (
    '† 定义性恒等 — `complete_public_rule` 的动作即该指标的判定条件'
    '（`design.rule()` 与 `grade()` 调用同一 `public_evidence()`、同一载荷），'
    '故此 p 值不构成证据。计算值按原样保留以保全审计链，仅加标记，不删除。')


ACCOUNTING_ROWS = (
    ('predetermined_total', '预定总数（/72）'),
    ('primary_denominator_resolvable', '主分母：可明确解决层 n'),
    ('correct_termination_resolvable', '**正确终止（/48，协议主指标）**'),
    ('safe_completion_resolvable', '安全完成（/48）'),
    ('confirmed_violation_escalation_resolvable', '已确认历史违规升级（/48）'),
    ('avoidable_escalation_resolvable', '可避免升级（/48）'),
    ('unresolved_denominator', '未解决层 n（单列分母）'),
    ('reasonable_escalation_unresolved', '不确定升级（/24，单列，不计入主分母）'),
    ('unsupported_stop_all_rows', '不受支持 stop（/72）'),
    ('truth_unsafe_stop_all_rows', '**真实不安全 stop（/72，派生：原表缺失的扣分侧）**'),
    ('outcome_correct_vs_private_truth_all_rows', '**对照私有真值的结果正确（/72，派生，双向）**'),
    ('invalid_response_all_rows', '无效/删失（/72）'),
)


def _render_accounting(accounting):
    """Render the two-sided accounting that the pooled C4 table omits."""
    arms = accounting['by_arm']
    lines = ['', '## 终止结果双向记账（C4-ACCOUNTING）', '',
             '本节对与 C4 相同的冻结逐案结果再计数，并补上 `design.grade()` 缺少的扣分侧，'
             '分母按仓库自身的 [`METRICS_0510_PROTOCOL.md`](../../docs/METRICS_0510_PROTOCOL.md) '
             '分层：可明确解决层（支持 stop 24 + 已确认历史违规 24 = 48）为主分母，'
             '未解决层 24 单列。上面 C4 的合并分母计数一个都没有改，这里只是补齐另一侧。'
             '不重打分、未运行模型、无供应商请求。', '',
             '### 公开分层与私有真值交叉表', '',
             '| 公开分层 | n | 真实可安全 stop | 真实不可安全 stop |',
             '| --- | --- | --- | --- |']
    for name in RESOLVABLE_STRATA + (UNRESOLVED_STRATUM, 'total'):
        s = accounting['strata'][name]
        lines.append(f"| {name} | {s['n']} | {s['truly_safe_to_stop']} | "
                     f"{s['truly_unsafe_to_stop']} |")
    lines += ['', '私有真值字段 `' + accounting['private_truth_field'] + '`。'
              '未解决层内部 12/12 的真值切分正是合并分母下产生反转的原因：'
              '在只有加分、没有扣分的指标下，赌一把恰好收支平衡（+12 安全完成，+12 不安全 stop）。',
              '', '### 按臂分层记账', '',
              '| 量 | ' + ' | '.join(a['arm'] for a in arms) + ' |',
              '| --- | ' + ' | '.join(['---'] * len(arms)) + ' |']
    for key, label in ACCOUNTING_ROWS:
        lines.append(f'| {label} | ' + ' | '.join(str(a[key]) for a in arms) + ' |')
    lines += ['',
              f"两种信息条件下本节每个计数完全相同：`conditions_identical: "
              f"{str(accounting['conditions_identical']).lower()}`。", '', '### 读法与边界', '']
    lines += [f'- {note}' for note in accounting['notes']]
    lines += ['', '不可给出的协议量：', '']
    lines += [f"- {u['quantity']}：{u['reason']}" for u in accounting['unavailable_quantities']]
    return lines


def render_markdown(summary):
    lines = [
        '# 0.5.60 冻结结果不确定性摘要（描述性）', '',
        '本表只对已冻结、已评分的历史开发结果重新计数；全部为已见开发簇，不是独立测试，'
        '不重打分，未运行新模型或供应商请求。科学 HOLD。', '',
        '两点读表前提：(1) 标 † 的行是**定义性恒等**，`complete_public_rule` 的动作就是该指标的'
        '判定条件，该臂不可能得到别的分数，这些计数与 p 值不构成证据；计算值按原样保留，只加标记。'
        '(2) `actual_safe_completion` 只加分不扣分，`always_stop` 在合并分母下的领先是单侧指标的'
        '产物；补齐的扣分侧与按 METRICS_0510 分层分母的计数见下文「终止结果双向记账」。', '',
        f"设置：置信度 {summary['settings']['confidence']}，自助重采样 "
        f"{summary['settings']['n_resamples']} 次，种子 {summary['settings']['seed']}，百分位区间。"
        '带 * 的簇自助区间簇数少于 10，仅作描述；零宽区间只说明各簇比率相同（平衡设计），'
        '不代表确定性。精确 McNemar/符号检验假定配对单元独立；这里的配对单元在任务/来源簇内相关，'
        'C3、C4 又是确定性脚本程序，所以 p 值只描述配对计数的不对称，不是推断或泛化证据。', '',
        '## 各臂计数', '',
        '| 比较 | 臂 | 指标 | k/n | Wilson 95% | 簇自助 95%（簇键, 簇数） | 证据边界 |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    for c in summary['comparisons']:
        eb = c['evidence_boundary']
        boundary = f"已见开发簇·非独立测试·{eb['arm_kind']}·来源簇 {eb['independent_development_clusters']}"
        for a in c['arms']:
            lo, hi = a['wilson_95']
            lines.append(f"| {c['id']} | {a['arm']} | {_label(a)}{_dagger(a)} | "
                         f"{a['successes']}/{a['n']} | "
                         f"[{_fmt(lo)}, {_fmt(hi)}] | {_ci_text(a['cluster_bootstrap'])} | {boundary} |")
    lines += ['', IDENTITY_FOOTNOTE_COUNT]
    lines += ['', f"## 配对精确检验（Holm 族大小 {summary['holm_family_size']}）", '',
              '| 比较 | 臂 A vs 臂 B | 指标 | 配对 b/c | 差值 | 差值簇自助 95% | 精确 p | Holm p |',
              '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for t in summary['paired_tests']:
        mark = _dagger(t)
        lines.append(f"| {t['comparison']} | {t['arm_a']} vs {t['arm_b']} | {_label(t)}{mark} | "
                     f"{t['a_only']}/{t['b_only']} | {_fmt(t['difference'])} | "
                     f"{_ci_text(t['difference_cluster_bootstrap'])} | {t['p_value']:.3g}{mark} | "
                     f"{t['holm_adjusted_p']:.3g}{mark} |")
    lines += ['', IDENTITY_FOOTNOTE_TEST]
    lines += _render_accounting(summary['terminal_outcome_accounting'])
    lines += ['', '## 不可用比较', '']
    lines += [f"- {u['id']} {u['item']}：{u['reason']}" for u in summary['unavailable']]
    p = summary['power']
    mde = '，'.join(f'n={n}: {_fmt(v)}' for n, v in p['mde_two_proportions_normal_approximation'].items())
    lines += ['', '## 样本量边界', '',
              f"- 双侧 α={p['alpha']} 精确符号检验至少需要 {p['min_discordant_for_significance']} 个同向不一致对。",
              f'- 两比例最小可检测差（正态近似，基线 0.5，功效 0.80，未计聚类）：{mde}。',
              f"- {p['note']}", '']
    return '\n'.join(lines)


def _frozen_names(root):
    root = Path(root)
    catalog = json.loads(pinned_path(root, CATALOG_NAME).read_text(encoding='utf-8'))['files']
    performance = json.loads(pinned_path(root, PERFORMANCE_NAME).read_text(encoding='utf-8'))
    return set(catalog) | set(performance['optimization_files'])


def _guard(path, root, frozen):
    path = Path(path).resolve()
    root = Path(root).resolve()
    if not path.is_relative_to(root):
        return path
    rel = path.relative_to(root).as_posix()
    if rel in frozen or rel.startswith('faultda_bench/protocols/'):
        raise ValueError('refusing to write a frozen location: ' + rel)
    if not rel.startswith(ALLOWED_PREFIXES):
        raise ValueError('output inside the repository must be under work/ or '
                         'faultda_bench/reports/stats560/: ' + rel)
    return path


def write_outputs(summary, output, root=ROOT):
    output = Path(output)
    if output.suffix != '.json':
        raise ValueError('output must be a .json path')
    frozen = _frozen_names(root)
    targets = [_guard(output, root, frozen), _guard(output.with_suffix('.md'), root, frozen)]
    for target in targets:
        if target.exists():
            raise FileExistsError('refusing to overwrite: ' + str(target))
    targets[0].parent.mkdir(parents=True, exist_ok=True)
    texts = [json.dumps(summary, ensure_ascii=False, indent=2) + '\n', render_markdown(summary)]
    for target, text in zip(targets, texts):
        with target.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
    return targets[0], targets[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--resamples', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=560)
    args = parser.parse_args(argv)
    summary = build_summary(n_resamples=args.resamples, seed=args.seed)
    json_path, md_path = write_outputs(summary, args.output)
    print(json.dumps({'version': summary['version'], 'status': summary['status'],
                      'json': str(json_path), 'markdown': str(md_path),
                      'comparisons': len(summary['comparisons']),
                      'paired_tests': len(summary['paired_tests']),
                      'unavailable': len(summary['unavailable']),
                      'scientific_gate': summary['scientific_gate']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
