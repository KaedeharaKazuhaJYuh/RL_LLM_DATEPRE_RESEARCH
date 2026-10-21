"""Stdlib exact statistics and the O1/O2/O3 assembly; every threshold is read from the prereg."""
import argparse
import json
import math
import random
import time
from fractions import Fraction
from pathlib import Path
from statistics import NormalDist

from . import VERSION, certificate, costs, instances, policies, suite, witness
from .canon import QUANTIZE_DIGITS, compact, fsum_, sha_json, write_json_once
from ..multistep.suite import require
from ..semantic.tasks import REPO, ROOT, sha

OUTPUT = ROOT / 'reports/vericost565/analysis.json'
SCHEMA = 'vericost565.analysis.v1'
PREREG = ROOT / 'protocols/vericost_v1_prereg.json'
AMENDMENTS = ROOT / 'protocols/vericost_v1_amendments.json'
# The exact sign-flip enumerates 2**n sign vectors, so it is refused above twenty clusters.
MAX_CLUSTERS = 20
DZ_FORMULA = '(t_{1-alpha,n-1} + t_{0.8,n-1}) / sqrt(n)'
LEARNED_ARMS = ('q_only', 'thompson', 'linucb')
NOT_RUN = {
    'new_sources': 'rescope_no_downloads: no HTTP fetch, no UCI candidate screening, no '
                   'sources.py, no archive download, no sha pinning, no alias or family screen',
    'heldout_split': 'rescope_heldout_deferred_until_claim_decided: no seeded dev/held-out/reserve '
                     'split, no held-out task, no gate0_*_heldout.json, no dp_certificate_heldout, '
                     'no heldout_offline.json, no held-out freeze manifest',
    'pilot': 'owner_scope_no_live_runs: no pilot cells, packets, measures, pilot.json or '
             'projection amendment',
    'a': 'owner_scope_no_live_runs: live block A is not run',
    'b': 'owner_scope_no_live_runs: live block B (Direction B terminal packets) is not run',
    'p1': 'owner_scope_no_live_runs: probe P1 is not run',
    'p2': 'owner_scope_no_live_runs: probe P2 is not run',
    'provider_requests': 'rescope_no_provider_path: zero chat/completions and zero balance '
                         'requests; 0 API calls and CNY 0.000000',
    'provider_path': 'rescope_no_provider_path: client.py, prompts.py and mock.py are not '
                     'implemented, which is what audit --no-network asserts',
    'direction_b': 'terminal.py, its three packet states, SYSTEM_B, grade(), '
                   'terminal_packets.json and terminal_programs.json are not implemented',
    'hybrid_arm': 'the flash + Q gate arm, its accept/override rule and the gate_override history '
                  'fields are not implemented; q_only is kept as a standalone arm',
    'suite_modes': 'suite --dry-run/--live/--resume/--finalize-crashed/--verify/--render-prompts, '
                   'the vericost565.trace.v1 schema, OUT.requests.jsonl, crash/resume and live '
                   'preconditions (c),(d),(f),(g),(i) are not implemented',
    'hypotheses_live': 'H1, H2, H3 and their evaluators plus '
                       'analysis_dryrun_validation.json are not run; the hypotheses stay '
                       'pre-registered and pending_live',
    'second_model_and_training': 'P1/P2 probe subset, flash-thinking and v4-pro arms, LoRA, SFT, '
                                 'GRPO, any GPU or torch work and a second provider are not run',
    'generalization_claim': 'none: every record carries split=development, seen_cluster=true, '
                            'independent_test=false'}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


# ---- exact sign-flip ----------------------------------------------------------------------------
def signflip_p(diffs, stat='mean', denom=None):
    """Exact one-sided p over all 2**n sign vectors: P(T(s*d) >= T(d)) under symmetry about 0.

    `mean` divides by n; `pooled` divides by `denom` (default n), the ratio-of-sums form in which
    the denominator is fixed across sign vectors. The divisor cancels in the comparison, so the
    two statistics give the same p and `pooled` with denom = n equals `mean` exactly.
    """
    values = [float(value) for value in diffs]
    require(stat in ('mean', 'pooled'), 'unknown sign-flip statistic: ' + str(stat))
    if not values:
        raise ValueError('the sign-flip test needs at least one cluster difference')
    if len(values) > MAX_CLUSTERS:
        raise ValueError('the exact sign-flip test is limited to %d clusters, got %d'
                         % (MAX_CLUSTERS, len(values)))
    divisor = float(len(values)) if stat == 'mean' else float(len(values) if denom is None
                                                              else denom)
    require(divisor != 0.0, 'the pooled sign-flip denominator must not be zero')
    observed = round(fsum_(values) / divisor, QUANTIZE_DIGITS)
    hits = 0
    for mask in range(1 << len(values)):
        flipped = [value if mask >> index & 1 else -value
                   for index, value in enumerate(values)]
        if round(fsum_(flipped) / divisor, QUANTIZE_DIGITS) >= observed:
            hits += 1
    return hits / (1 << len(values))


def signflip_gt(diffs, theta, alpha, stat='mean', denom=None):
    """Test inversion: is the centre of `diffs` above `theta` at level `alpha`?"""
    return signflip_p([float(value) - float(theta) for value in diffs], stat, denom) < float(alpha)


def signflip_lt(diffs, theta, alpha, stat='mean', denom=None):
    """Test inversion: is the centre of `diffs` below `theta` at level `alpha`?"""
    return signflip_p([float(theta) - float(value) for value in diffs], stat, denom) < float(alpha)


# ---- the cluster bootstrap (descriptive only) ---------------------------------------------------
def percentile(values, fraction):
    """Linear-interpolation percentile, the convention the design's intervals were planned with."""
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError('no bootstrap draws')
    position = float(fraction) * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[int(position)]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def cluster_bootstrap(rows, kind, draws, seed, level=0.95):
    """Percentile cluster bootstrap over (numerator, denominator) pairs; never reads a verdict.

    `ratio` resamples clusters and recomputes the summed numerator over the summed denominator;
    `macro` averages the per-cluster ratios. The choice is made once, before the loop, so it is
    fixed inside every resample.
    """
    require(kind in ('ratio', 'macro'), 'unknown bootstrap statistic: ' + str(kind))
    pairs = [(float(num), float(den)) for num, den in rows]
    require(bool(pairs), 'the bootstrap needs at least one cluster')
    if kind == 'ratio':
        def statistic(sample):
            return fsum_([num for num, _ in sample]) / fsum_([den for _, den in sample])
    else:
        def statistic(sample):
            return fsum_([num / den for num, den in sample]) / len(sample)
    rng = random.Random(seed)
    size = len(pairs)
    drawn = []
    for _ in range(int(draws)):
        sample = [pairs[rng.randrange(size)] for _ in range(size)]
        drawn.append(statistic(sample))
    tail = (1.0 - float(level)) / 2
    return {'kind': kind, 'draws': int(draws), 'seed': seed, 'level': float(level),
            'point': statistic(pairs), 'lo': percentile(drawn, tail),
            'hi': percentile(drawn, 1.0 - tail), 'clusters': size,
            'degenerate': percentile(drawn, tail) == percentile(drawn, 1.0 - tail),
            'role': 'descriptive only; no verdict condition reads a bootstrap bound'}


# ---- exact counting tests -----------------------------------------------------------------------
def cluster_binomial_p(successes, trials, probability=Fraction(1, 2)):
    """Exact one-sided upper-tail binomial probability P(X >= successes), via Fraction."""
    require(0 <= successes <= trials, 'successes must lie in [0, trials]')
    share = Fraction(probability)
    total = Fraction(0)
    for count in range(successes, trials + 1):
        total += (Fraction(math.comb(trials, count)) * share ** count
                  * (1 - share) ** (trials - count))
    return float(total)


def wilson(successes, total, confidence=0.95):
    """Wilson score interval, clipped to [0, 1]; reproduces stats560.wilson_interval exactly."""
    require(type(successes) is int and successes >= 0, 'successes must be a non-negative int')
    require(type(total) is int and total > 0, 'total must be a positive int')
    require(successes <= total, 'successes exceeds the total')
    z = NormalDist().inv_cdf(1 - (1 - float(confidence)) / 2)
    share = successes / total
    denominator = 1 + z * z / total
    centre = (share + z * z / (2 * total)) / denominator
    half = z / denominator * math.sqrt(share * (1 - share) / total + z * z / (4 * total * total))
    return max(0.0, centre - half), min(1.0, centre + half)


def mcnemar_exact(first, second):
    """Two-sided exact McNemar on the discordant counts, computed with Fraction."""
    require(type(first) is int and type(second) is int and min(first, second) >= 0,
            'discordant counts must be non-negative ints')
    total = first + second
    if total == 0:
        return 1.0
    smaller = min(first, second)
    tail = sum(Fraction(math.comb(total, index)) for index in range(smaller + 1))  # int-sum
    return float(min(Fraction(1), 2 * tail / Fraction(2) ** total))


def holm(pvalues):
    """Holm step-down adjusted p-values in input order; reproduces stats560.holm_bonferroni."""
    values = [float(value) for value in pvalues]
    require(all(0 <= value <= 1 for value in values), 'p-values must lie in [0, 1]')
    adjusted = [0.0] * len(values)
    running = 0.0
    for rank, index in enumerate(sorted(range(len(values)), key=lambda item: values[item])):
        running = max(running, min(1.0, (len(values) - rank) * values[index]))
        adjusted[index] = running
    return adjusted


def icc_anova(groups):
    """One-way ANOVA intraclass correlation, clamped at 0 when between-group variance vanishes."""
    rows = [[float(value) for value in group] for group in groups]
    require(len(rows) >= 2, 'the ICC needs at least two groups')
    sizes = {len(row) for row in rows}
    require(sizes and 0 not in sizes and len(sizes) == 1, 'the ICC needs equal non-empty groups')
    size = sizes.pop()
    flat = [value for row in rows for value in row]
    grand = fsum_(flat) / len(flat)
    means = [fsum_(row) / size for row in rows]
    between = fsum_([size * (mean - grand) ** 2 for mean in means]) / (len(rows) - 1)
    within_df = len(rows) * (size - 1)
    if within_df == 0:
        return 1.0 if between > 0 else 0.0
    within = fsum_([(value - means[index]) ** 2
                    for index, row in enumerate(rows) for value in row]) / within_df
    denominator = between + (size - 1) * within
    if denominator == 0:
        return 0.0
    return max(0.0, (between - within) / denominator)


def logistic_slope(x, y, iterations=100, tol=1e-12):
    """Newton fit of logit P(y=1) = a + b*x; descriptive, with an explicit degeneracy flag."""
    xs = [float(value) for value in x]
    ys = [float(value) for value in y]
    require(len(xs) == len(ys) and xs, 'logistic_slope needs matching non-empty vectors')
    require(all(value in (0.0, 1.0) for value in ys), 'the response must be 0 or 1')
    if len(set(ys)) == 1 or len(set(xs)) == 1:
        return {'intercept': None, 'slope': None, 'iterations': 0, 'converged': False,
                'degenerate': True, 'n': len(xs)}
    intercept, slope = 0.0, 0.0
    for step in range(1, iterations + 1):
        probabilities = [1 / (1 + math.exp(-(intercept + slope * value))) for value in xs]
        gradient = (fsum_([ys[index] - probabilities[index] for index in range(len(xs))]),
                    fsum_([xs[index] * (ys[index] - probabilities[index])
                           for index in range(len(xs))]))
        weights = [probability * (1 - probability) for probability in probabilities]
        h00 = fsum_(weights)
        h01 = fsum_([weights[index] * xs[index] for index in range(len(xs))])
        h11 = fsum_([weights[index] * xs[index] ** 2 for index in range(len(xs))])
        determinant = h00 * h11 - h01 * h01
        if determinant == 0:
            return {'intercept': intercept, 'slope': slope, 'iterations': step,
                    'converged': False, 'degenerate': True, 'n': len(xs)}
        delta = ((h11 * gradient[0] - h01 * gradient[1]) / determinant,
                 (h00 * gradient[1] - h01 * gradient[0]) / determinant)
        intercept += delta[0]
        slope += delta[1]
        if max(abs(delta[0]), abs(delta[1])) < tol:
            return {'intercept': intercept, 'slope': slope, 'iterations': step, 'converged': True,
                    'degenerate': False, 'n': len(xs)}
    return {'intercept': intercept, 'slope': slope, 'iterations': iterations, 'converged': False,
            'degenerate': False, 'n': len(xs)}


# ---- Student t and the minimum detectable effect ------------------------------------------------
def _beta_fraction(a, b, x, iterations=300, tiny=1e-300):
    """Lentz continued fraction for the incomplete beta function."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = tiny if abs(d) < tiny else d
    d = 1.0 / d
    h = d
    for index in range(1, iterations + 1):
        m2 = 2 * index
        numerator = index * (b - index) * x / ((qam + m2) * (a + m2))
        d = 1.0 + numerator * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + numerator / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        h *= d * c
        numerator = -(a + index) * (qab + index) * x / ((a + m2) * (qap + m2))
        d = 1.0 + numerator * d
        d = tiny if abs(d) < tiny else d
        c = 1.0 + numerator / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        step = d * c
        h *= step
        if abs(step - 1.0) < 1e-16:
            break
    return h


def incomplete_beta(a, b, x):
    """The regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                     + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_fraction(a, b, x) / a
    return 1.0 - front * _beta_fraction(b, a, 1.0 - x) / b


def student_cdf(t, df):
    """P(T <= t) for Student's t with `df` degrees of freedom, through incomplete_beta."""
    t, df = float(t), float(df)
    tail = 0.5 * incomplete_beta(df / 2, 0.5, df / (df + t * t))
    return 1.0 - tail if t > 0 else tail


def student_quantile(probability, df, tol=1e-13):
    """The t quantile by bisection on the exact CDF (no table, no approximation)."""
    probability = float(probability)
    require(0.0 < probability < 1.0, 'the quantile probability must lie in (0, 1)')
    low, high = -1000.0, 1000.0
    for _ in range(200):
        middle = (low + high) / 2
        if student_cdf(middle, df) < probability:
            low = middle
        else:
            high = middle
        if high - low < tol:
            break
    return (low + high) / 2


def dz_mde(n, alpha, power=0.8, sd=None, formula=None):
    """d_z = (t_{1-alpha,n-1} + t_{power,n-1}) / sqrt(n), and the MDE in the units of `sd`."""
    require(int(n) >= 2, 'the MDE needs at least two clusters')
    if formula is not None:
        require(formula == DZ_FORMULA, 'the pre-registered d_z formula changed: ' + str(formula))
    df = int(n) - 1
    upper = student_quantile(1 - float(alpha), df)
    second = student_quantile(float(power), df)
    dz = (upper + second) / math.sqrt(int(n))
    out = {'n': int(n), 'alpha': float(alpha), 'power': float(power), 'df': df,
           'formula': DZ_FORMULA, 't_quantiles': [upper, second], 'dz': dz}
    if sd is not None:
        out['sd'] = float(sd)
        out['mde'] = dz * float(sd)
    return out


def dominated(candidate, reference, keys=('expected_safe', 'expected_cost_units')):
    """Is `candidate` dominated by `reference` on (safety up, cost down) at twelve digits?"""
    safe_key, cost_key = keys
    safe = round(reference[safe_key] - candidate[safe_key], QUANTIZE_DIGITS)
    cost = round(candidate[cost_key] - reference[cost_key], QUANTIZE_DIGITS)
    return safe >= 0 and cost >= 0 and (safe > 0 or cost > 0)


# ---- aggregation of the offline evaluation ------------------------------------------------------
def _totals(offline):
    """Sums of E[U*] and of every arm's expectations, per regime and per (regime, cluster)."""
    optimum, by_regime, by_cluster = {}, {}, {}
    for row in offline['optimum']:
        optimum[row['regime_id']] = optimum.get(row['regime_id'], 0.0) + row['expected_u_star']
        key = (row['regime_id'], row['cluster_id'])
        by_cluster.setdefault(key, {'u_star': 0.0, 'arms': {}, 'profiles': 0})
        by_cluster[key]['u_star'] += row['expected_u_star']
        by_cluster[key]['profiles'] += 1
    profiles = {}
    for row in offline['expected']:
        regime, arm = row['regime_id'], row['arm']
        block = by_regime.setdefault(regime, {}).setdefault(arm, {
            'expected_u': 0.0, 'expected_safe': 0.0, 'expected_cost_units': 0.0,
            'expected_decisions': 0.0, 'fallback_rule_rate': 0.0, 'dominated_reads': 0.0,
            'profiles': 0})
        cluster = by_cluster[(regime, row['cluster_id'])]['arms'].setdefault(arm, {
            'expected_u': 0.0, 'expected_safe': 0.0, 'expected_cost_units': 0.0})
        for key in ('expected_u', 'expected_safe', 'expected_cost_units'):
            block[key] += row[key]
            cluster[key] += row[key]
        for key in ('expected_decisions', 'fallback_rule_rate', 'dominated_reads'):
            block[key] += row[key]
        block['profiles'] += 1
        profiles[regime] = max(profiles.get(regime, 0), block['profiles'])
    return {'u_star': optimum, 'regimes': by_regime, 'clusters': by_cluster,
            'profiles': profiles}


def _regret(u_star, value):
    return (u_star - value) / u_star


def _per_profile(block, profiles):
    return {'expected_u': block['expected_u'] / profiles,
            'expected_safe': block['expected_safe'] / profiles,
            'expected_cost_units': block['expected_cost_units'] / profiles,
            'expected_decisions': block['expected_decisions'] / profiles,
            'fallback_rule_rate': block['fallback_rule_rate'] / profiles,
            'dominated_reads': block['dominated_reads'] / profiles}


# ---- O1: the Gate 0 regime map tables -----------------------------------------------------------
def o1_tables(maps, registration):
    """The Gate 0 reading per instance set and model; the numbers come from the committed maps."""
    epsilon = registration['gate0']['epsilon']
    out = {}
    for model, data in sorted(maps.items()):
        out[model] = {'decision_set': data['decision_set'], 'decision': data['decision'], 'sets': {}}
        for label, item in sorted(data['sets'].items()):
            rows = []
            for row in item['regimes']:
                argmin = row['argmin']
                member = argmin['member']
                rows.append({'regime_id': row['regime_id'], 'kappa': row['kappa'], 'L': row['L'],
                             'primary': row['primary'], 'expected_u_star': row['expected_u_star'],
                             'admissible': row['admissible'], 'min_fixed_r': row['min_fixed_r'],
                             'within_epsilon': row['min_fixed_r'] <= epsilon,
                             'argmin_family': argmin['family'],
                             'argmin_member': member if isinstance(member, str) else None,
                             'argmin_cells': None if isinstance(member, str) else len(member),
                             'families': {name: block['regret']
                                          for name, block in sorted(row['families'].items())},
                             'single_rule_literal': row['single_rule_literal']})
            out[model]['sets'][label] = {
                'clusters': item['clusters'], 'profiles': item['profiles'],
                'size_buckets_present': item['size_buckets_present'],
                'single_rule_literal': item['single_rule_literal'],
                'decision': item['decision'], 'regimes': rows}
    return {'epsilon': epsilon, 'models': out,
            'scope': maps['rev1']['decision']['scope'],
            'hard_stop': maps['rev1']['decision']['hard_stop'],
            'trigger': maps['rev1']['decision']['trigger'],
            'note': 'the three instance sets disagree; every set carries its own decision block '
                    'and the pre-registered decision set is dev_syn (plan D1)'}


# ---- O2 and O3 ----------------------------------------------------------------------------------
def _cluster_deltas(totals, regime_id, arm, reference='bf'):
    """Per-cluster difference of cluster totals, the input of the exact sign-flip test."""
    rows = {}
    for (regime, cluster), block in sorted(totals['clusters'].items()):
        if regime != regime_id:
            continue
        rows[cluster] = {'delta_u': block['arms'][arm]['expected_u']
                         - block['arms'][reference]['expected_u'],
                         'delta_safe': block['arms'][arm]['expected_safe']
                         - block['arms'][reference]['expected_safe'],
                         'delta_cost': block['arms'][arm]['expected_cost_units']
                         - block['arms'][reference]['expected_cost_units'],
                         'expected_u_star': block['u_star']}
    return rows


def o2_verdict(point, rules, under_powered, reason):
    """The pre-registered O2 rule: no verdict condition reads a bootstrap bound (plan D9)."""
    alpha = rules['alpha_O2']
    if point['delta_u'] <= 0 or point['dominated']:
        verdict = 'FALSIFIED'
    elif point['signflip_p'] < alpha and point['delta_u'] > 0 and not point['dominated']:
        verdict = 'SUPPORTED'
    else:
        verdict = 'INCONCLUSIVE'
    return {'verdict': verdict, 'alpha': alpha, 'under_powered': under_powered, 'reason': reason}


def o2_block(totals, regime_id, arm, rules, min_attainable, reference='bf'):
    """One arm against the development-selected best fixed rule at one regime."""
    deltas = _cluster_deltas(totals, regime_id, arm, reference)
    values = [deltas[cluster]['delta_u'] for cluster in sorted(deltas)]
    profiles = totals['profiles'][regime_id]
    candidate = _per_profile(totals['regimes'][regime_id][arm], profiles)
    base = _per_profile(totals['regimes'][regime_id][reference], profiles)
    mean = fsum_(values) / len(values)
    wins = sum(1 for value in values if round(value, QUANTIZE_DIGITS) > 0)  # int-sum
    point = {'arm': arm, 'reference': reference, 'regime_id': regime_id,
             'delta_u': mean, 'delta_u_total': fsum_(values),
             'delta_u_by_cluster': {cluster: deltas[cluster]['delta_u']
                                    for cluster in sorted(deltas)},
             'delta_safe': candidate['expected_safe'] - base['expected_safe'],
             'delta_cost': candidate['expected_cost_units'] - base['expected_cost_units'],
             'expected_u': candidate['expected_u'], 'reference_expected_u': base['expected_u'],
             'regret': _regret(totals['u_star'][regime_id],
                               totals['regimes'][regime_id][arm]['expected_u']),
             'reference_regret': _regret(totals['u_star'][regime_id],
                                         totals['regimes'][regime_id][reference]['expected_u']),
             'dominated': dominated(candidate, base),
             'clusters_with_positive_delta': wins, 'n_clusters': len(values),
             'signflip_p': signflip_p(values),
             'cluster_binomial_p': cluster_binomial_p(wins, len(values))}
    rows = [(deltas[cluster]['delta_u'], deltas[cluster]['expected_u_star'])
            for cluster in sorted(deltas)]
    bootstrap = {kind: cluster_bootstrap(rows, kind, rules['bootstrap']['draws'],
                                         rules['bootstrap']['seed'])
                 for kind in ('ratio', 'macro')}
    reason = ('the exact one-sided cluster sign-flip floor over %d clusters is %s > alpha_O2 %s, '
              'so no p value can clear alpha; the verdict is decided by the point estimate and '
              'dominance alone (plan R7/D9)' % (len(values), min_attainable, rules['alpha_O2']))
    verdict = o2_verdict(point, rules, True, reason)
    if verdict['verdict'] == 'FALSIFIED':
        verdict['reason'] = ('falsified by the point estimate: mean cluster delta U is %.12g and '
                             'dominated is %s. ' % (point['delta_u'], point['dominated'])) + reason
    return dict(point, bootstrap_ci=bootstrap, **verdict)


def o3_block(totals, rules, registration):
    """Regret by arm, the gap recovered over bf and the cost/safety frontier at every regime."""
    gap_floor = rules['gap_floor']
    regret, gap, frontier = {}, {}, []
    for regime_id in costs.REGIME_IDS:
        block = totals['regimes'][regime_id]
        profiles = totals['profiles'][regime_id]
        u_star = totals['u_star'][regime_id]
        regret[regime_id] = {arm: _regret(u_star, block[arm]['expected_u'])
                             for arm in sorted(block)}
        base = block['bf']['expected_u']
        denominator = u_star - base
        gap[regime_id] = {}
        for arm in LEARNED_ARMS:
            if denominator < gap_floor:
                gap[regime_id][arm] = None
            else:
                gap[regime_id][arm] = (block[arm]['expected_u'] - base) / denominator
        gap[regime_id]['denominator'] = denominator
        gap[regime_id]['gap_floor'] = gap_floor
        gap[regime_id]['undefined'] = denominator < gap_floor
        for arm in suite.ARMS:
            row = _per_profile(block[arm], profiles)
            frontier.append({'arm': arm, 'regime_id': regime_id,
                             'expected_safe': row['expected_safe'],
                             'expected_cost_units': row['expected_cost_units'],
                             'expected_u': row['expected_u'],
                             'regret': regret[regime_id][arm]})
    for row in frontier:
        peers = [item for item in frontier if item['regime_id'] == row['regime_id']
                 and item['arm'] != row['arm']]
        row['dominated_by'] = sorted(item['arm'] for item in peers if dominated(row, item))
        row['pareto'] = not row['dominated_by']
    return {'regret_by_arm': regret, 'gap_recovered': gap, 'frontier': frontier,
            'gap_recovered_rule': registration['hypotheses_offline']['O3']['gap_recovered']}


# ---- realized-episode diagnostics ---------------------------------------------------------------
def realized_blocks(offline, regime_id):
    """Wilson intervals, the exact McNemar pairing and the descriptive logistic and ICC fits."""
    rows = [row for row in offline['realized'] if row['regime_id'] == regime_id]
    by_arm = {}
    for row in rows:
        by_arm.setdefault(row['arm'], []).append(row)
    clusters = {}
    for row in offline['optimum']:
        clusters[row['profile_id']] = row['cluster_id']
    out = {}
    for arm, episodes in sorted(by_arm.items()):
        safe = sum(int(item['safe_complete']) for item in episodes)  # int-sum
        low, high = wilson(safe, len(episodes))
        grouped = {}
        for item in episodes:
            grouped.setdefault(clusters[item['cell_id'].split('|')[0]], []).append(item['u'])
        size = min(len(values) for values in grouped.values())
        out[arm] = {'episodes': len(episodes), 'safe_complete': safe,
                    'safe_rate': safe / len(episodes), 'wilson_95': [low, high],
                    'cluster_icc_u': icc_anova([values[:size]
                                                for _, values in sorted(grouped.items())]),
                    'logistic_safe_on_cost': logistic_slope(
                        [item['cost_units'] for item in episodes],
                        [item['safe_complete'] for item in episodes])}
    paired = {}
    for arm in LEARNED_ARMS:
        first = {item['cell_id']: item['safe_complete'] for item in by_arm[arm]}
        second = {item['cell_id']: item['safe_complete'] for item in by_arm['bf']}
        wins = sum(1 for cell in first if first[cell] > second[cell])  # int-sum
        losses = sum(1 for cell in first if first[cell] < second[cell])  # int-sum
        paired[arm] = {'arm_only': wins, 'bf_only': losses,
                       'discordant': wins + losses,
                       'mcnemar_exact_p': mcnemar_exact(wins, losses),
                       'method': 'exact_mcnemar_two_sided'}
    return {'regime_id': regime_id, 'by_arm': out, 'mcnemar_vs_bf': paired,
            'role': 'descriptive; the realized episodes are three frozen cells per profile'}


# ---- the report ---------------------------------------------------------------------------------
def inputs(offline_path=None):
    paths = {'prereg': PREREG, 'amendments': AMENDMENTS, 'instances_index': instances.INDEX,
             'golden_fixture': instances.GOLDEN, 'certificate': certificate.OUTPUT,
             'gate0_rev1': witness.OUTPUT['rev1'], 'gate0_d1': witness.OUTPUT['d1'],
             'learned_policies': policies.LEARNED, 'learned_policies_d1': policies.LEARNED_D1,
             'learned_eval': policies.EVALUATION, 'plan': suite.PLAN,
             'offline_eval': Path(offline_path or suite.OFFLINE)}
    return {name: sha(path) for name, path in sorted(paths.items()) if Path(path).exists()}


def report(offline_path=None):
    """Assemble analysis.json; every threshold, seed and draw count comes from the prereg."""
    registration = load(PREREG)
    rules = registration['verdict_rules']
    offline = load(offline_path or suite.OFFLINE)
    require(offline['schema'] == suite.OFFLINE_SCHEMA, 'unexpected offline evaluation schema')
    learned = load(policies.EVALUATION)
    maps = {model: load(path) for model, path in sorted(witness.OUTPUT.items())}
    certified = load(certificate.OUTPUT)
    totals = _totals(offline)
    clusters = sorted({cluster for _, cluster in totals['clusters']})
    n_clusters = len(clusters)
    min_attainable = 0.5 ** n_clusters
    primary = costs.PRIMARY
    power = dz_mde(n_clusters, rules['alpha_O2'], 0.8,
                   learned['power_inputs']['sd_delta_u'], rules['power']['dz_formula'])
    confirmatory = o2_block(totals, primary, 'q_only', rules, min_attainable)
    data = {'schema': SCHEMA, 'version': VERSION, 'split': 'development', 'seen_cluster': True,
            'independent_test': False, 'generalization_claim': 'none',
            'inputs': inputs(offline_path),
            'code_sha256': {'faultda_bench/vericost565/analysis.py': sha(Path(__file__)),
                            'faultda_bench/vericost565/suite.py': sha(Path(__file__).with_name(
                                'suite.py'))},
            'clusters': clusters, 'n_clusters': n_clusters,
            'min_attainable_signflip_p': min_attainable,
            'profiles': totals['profiles'][primary], 'arms': list(suite.ARMS),
            'primary_regime': primary,
            'under_power_declaration': registration['hypotheses_offline']['under_power_declaration'],
            'power': power,
            'O1': o1_tables(maps, registration),
            'O2': confirmatory,
            'O2_exploratory': {arm: dict(o2_block(totals, primary, arm, rules, min_attainable),
                                         label='exploratory')
                               for arm in ('thompson', 'linucb')},
            'O3': o3_block(totals, rules, registration),
            'realized': realized_blocks(offline, primary),
            'counts_by_arm': offline['counts_by_arm'],
            'certificate': {'status': certified['status'], 'tol': certified['tol'],
                            'mi_threshold_bits': certified['mi_threshold_bits'],
                            'parts': {name: {'status': part['status'],
                                             'max_violation': part['max_violation']}
                                      for name, part in sorted(certified['parts'].items())},
                            'c3_scope': certified['parts']['C3']['c3_scope'],
                            'sha256': sha(certificate.OUTPUT)},
            'hypotheses_live': {name: {'status': 'pending_live',
                                       'statement_en': registration['hypotheses_live_pending']
                                       [name]['statement_en'],
                                       'supported_iff': registration['hypotheses_live_pending']
                                       [name]['supported_iff']}
                                for name in ('H1', 'H2', 'H3')},
            'ci_test_scope': rules['ci_test_scope'], 'not_run': dict(NOT_RUN),
            'api_calls': 0, 'cny_spent': '0.000000'}
    cross = {}
    for cluster in clusters:
        block = learned['per_cluster'][primary][cluster]['expected_u']
        cross[cluster] = block['q_only'] - block['bf']
    data['O2']['cross_check_learned_eval'] = {
        'delta_u_by_cluster': cross, 'mean_delta_u': learned['power_inputs']['mean_delta_u'],
        'sd_delta_u': learned['power_inputs']['sd_delta_u'],
        'note': 'learned_eval.json evaluates the same arms independently of offline_eval.json; '
                'the two per-cluster delta U vectors must agree'}
    data['holm_exploratory'] = dict(zip(
        LEARNED_ARMS, holm([data['O2']['signflip_p']]
                           + [data['O2_exploratory'][arm]['signflip_p']
                              for arm in ('thompson', 'linucb')])))
    return data


def run(output=None, offline_path=None):
    data = report(offline_path)
    write_json_once(Path(output or OUTPUT), data)
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    parser.add_argument('--offline', type=Path)
    args = parser.parse_args()
    clock = time.perf_counter()
    produced = run(args.output, args.offline)
    print(compact({'analysis': str(args.output or OUTPUT), 'sha256': sha_json(produced),
                   'n_clusters': produced['n_clusters'],
                   'min_attainable_signflip_p': produced['min_attainable_signflip_p'],
                   'O2': {key: produced['O2'][key] for key in
                          ('arm', 'delta_u', 'signflip_p', 'dominated', 'verdict',
                           'under_powered')},
                   'O1': {'hard_stop': produced['O1']['hard_stop'],
                          'trigger': produced['O1']['trigger'],
                          'scope': produced['O1']['scope']},
                   'api_calls': produced['api_calls'], 'cny_spent': produced['cny_spent'],
                   'seconds_wall': round(time.perf_counter() - clock, 1)}))
