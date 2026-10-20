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
            arms.append(b.arm(a, m, values, keys, condition))
        for m in TERMINAL_METRICS:
            for other in ('always_stop', 'always_escalate'):
                tests.append(b.paired('C4', 'complete_public_rule', out[('complete_public_rule', m)],
                                      other, out[(other, m)], m, keys, condition))
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
        'arms': [b.arm('registered_complete_rule', m, [graded[k][m] for k in order], pooled, 'pooled')
                 for m in TERMINAL_METRICS]}
    return c4, c5, tests


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
    c4, c5, t4 = _c4_c5(b, data)
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
        'holm_family_size': len(tests), 'unavailable': UNAVAILABLE,
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


def render_markdown(summary):
    lines = [
        '# 0.5.60 冻结结果不确定性摘要（描述性）', '',
        '本表只对已冻结、已评分的历史开发结果重新计数；全部为已见开发簇，不是独立测试，'
        '不重打分，未运行新模型或供应商请求。科学 HOLD。', '',
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
            lines.append(f"| {c['id']} | {a['arm']} | {_label(a)} | {a['successes']}/{a['n']} | "
                         f"[{_fmt(lo)}, {_fmt(hi)}] | {_ci_text(a['cluster_bootstrap'])} | {boundary} |")
    lines += ['', f"## 配对精确检验（Holm 族大小 {summary['holm_family_size']}）", '',
              '| 比较 | 臂 A vs 臂 B | 指标 | 配对 b/c | 差值 | 差值簇自助 95% | 精确 p | Holm p |',
              '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for t in summary['paired_tests']:
        lines.append(f"| {t['comparison']} | {t['arm_a']} vs {t['arm_b']} | {_label(t)} | "
                     f"{t['a_only']}/{t['b_only']} | {_fmt(t['difference'])} | "
                     f"{_ci_text(t['difference_cluster_bootstrap'])} | {t['p_value']:.3g} | "
                     f"{t['holm_adjusted_p']:.3g} |")
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
