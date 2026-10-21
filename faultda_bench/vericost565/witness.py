"""Gate 0: the exact expected regret of every fixed rule family against the DP oracle."""
import argparse
import json
import multiprocessing
import time
from pathlib import Path

from . import VERSION, certificate, costs, dp, instances, policies, simulator
from .canon import argmax_first, compact, fsum_, sha_json, write_json_once
from ..semantic.tasks import REPO, ROOT, sha

OUTPUT = {'rev1': ROOT / 'reports/vericost565/gate0_rev1_dev.json',
          'd1': ROOT / 'reports/vericost565/gate0_d1_dev.json'}
PREREG = ROOT / 'protocols/vericost_v1_prereg.json'
FIXTURE = REPO / 'tests/fixtures/vericost565_gate0_synthetic.json'
SCHEMA = 'vericost565.gate0.v1'
FIXTURE_SCHEMA = 'vericost565.gate0_fixture.v1'
SETS = (('dev_syn', 'synthetic'), ('dev_seen', 'seen_development'), ('all', None))
# Plan D1: DEV-SYN is the primary instance set, so it carries the pre-registered decision.
DECISION_SET = 'dev_syn'
SINGLE_ARMS = ('always_full_recompute', 'escalate_all', 'never_verify', 'static_semantic',
               'guarded_read')
ALIASES = {'static_semantic': 'always_full_recompute'}
EXTRA_METRICS = ('safe', 'cost', 'reads')


def prereg(path=None):
    path = Path(path or PREREG)
    return policies.cached(('prereg', str(path)),
                           lambda: json.loads(path.read_text(encoding='utf-8')))


# ---- one (profile, regime) cell -----------------------------------------------------------------
def cell(profile, regime_id, model):
    """Every arm's exact expected utility over the 66 public histories of one profile.

    F rules do not read the history, so U_f(latent) is computed once per latent and mixed by
    P(latent | history) with math.fsum (the factorization of design 1.5).
    """
    latents = simulator.latents(model, len(profile['parts']))
    rows = policies.program_rows(profile, regime_id, model)
    values = {name: tuple(row['u'] for row in rows[name]) for name in policies.PROGRAM_ARMS}
    buckets = {'u_star': 0.0, 'u_star_by_type': {kind: 0.0 for kind in simulator.TYPES},
               'arm_total': [0.0] * len(policies.PROGRAM_ARMS),
               'arm_by_type': {kind: [0.0] * len(policies.F_RULES) for kind in simulator.TYPES},
               'arm_by_counts': {}, 'extras': {name: {key: 0.0 for key in EXTRA_METRICS}
                                               for name in SINGLE_ARMS}}
    for history in simulator.history_states():
        counts, weight, kind = history['counts'], history['weight'], history['map_type']
        oracle = dp.Oracle(profile, counts, regime_id, model)
        optimum = oracle.compact_root()
        buckets['u_star'] += weight * optimum
        buckets['u_star_by_type'][kind] += weight * optimum
        prior = simulator.latent_prior(profile, counts, model)
        shares = [prior[latent] for latent in latents]
        mass = fsum_(shares)
        counts_row = buckets['arm_by_counts'].setdefault(policies.counts_key(counts),
                                                         [0.0] * len(policies.F_RULES))
        for index, name in enumerate(policies.PROGRAM_ARMS):
            expected = fsum_(share * value for share, value in zip(shares, values[name])) / mass
            certificate.c4_assert(name, profile, regime_id, expected, optimum)
            buckets['arm_total'][index] += weight * expected
            if index < len(policies.F_RULES):
                buckets['arm_by_type'][kind][index] += weight * expected
                counts_row[index] += weight * expected
        for name in SINGLE_ARMS:
            for key in EXTRA_METRICS:
                buckets['extras'][name][key] += weight * (
                    fsum_(share * row[key] for share, row in zip(shares, rows[name])) / mass)
    return buckets


def _unit(task):
    profile_id, regime_id, model = task
    profile = policies.worker_profiles()[profile_id]
    clock = time.perf_counter()
    result = cell(profile, regime_id, model)
    result.update({'profile_id': profile_id, 'regime_id': regime_id,
                   'cluster_id': profile['cluster_id'], 'kind': profile['kind'],
                   'size_bucket': profile['size_bucket'], 'seconds': time.perf_counter() - clock})
    return result


# ---- aggregation --------------------------------------------------------------------------------
def _add(into, key, values):
    row = into.setdefault(key, [0.0] * len(values))
    for index, value in enumerate(values):
        row[index] += value


def _accumulate(rows):
    """Merge worker results into per-(regime, cluster, cell) sums, in the order they were listed."""
    totals = {}
    for row in rows:
        regime = totals.setdefault(row['regime_id'], {
            'profiles': {}, 'u_star': {}, 'arm_total': {}, 'extras': {}, 'size_cells': {},
            'hist_cells': {}, 'plus_cells': {}, 'buckets': {}, 'kinds': {}, 'seconds': 0.0})
        cluster, bucket = row['cluster_id'], row['size_bucket']
        regime['profiles'][cluster] = regime['profiles'].get(cluster, 0) + 1
        regime['u_star'][cluster] = regime['u_star'].get(cluster, 0.0) + row['u_star']
        regime['kinds'][cluster] = row['kind']
        regime['buckets'].setdefault(cluster, set()).add(bucket)
        regime['seconds'] += row['seconds']
        _add(regime['arm_total'], cluster, row['arm_total'])
        _add(regime['size_cells'], (cluster, bucket), row['arm_total'][:len(policies.F_RULES)])
        for kind in simulator.TYPES:
            _add(regime['hist_cells'], (cluster, kind, bucket), row['arm_by_type'][kind])
        for counts, values in row['arm_by_counts'].items():
            _add(regime['plus_cells'], (counts, bucket), values)
        extras = regime['extras'].setdefault(cluster, {})
        for name, metrics in row['extras'].items():
            store = extras.setdefault(name, {key: 0.0 for key in EXTRA_METRICS})
            for key in EXTRA_METRICS:
                store[key] += metrics[key]
    return totals


def _sum_cells(cells, keys):
    out = None
    for key in keys:
        row = cells[key]
        if out is None:
            out = [0.0] * len(row)
        for index, value in enumerate(row):
            out[index] += value
    return out or []


def _best(cells):
    """Per-cell argmax over F with the earliest-listed tie-break; expectation is separable."""
    members, values = {}, []
    for cell_id in sorted(cells):
        row = cells[cell_id]
        member = argmax_first([(rule, row[index])
                               for index, rule in enumerate(policies.F_RULES)])
        members[cell_id] = member
        values.append(row[policies.RULE_INDEX[member]])
    return members, fsum_(values)


def _regret(u_star, value):
    return (u_star - value) / u_star


def _family_blocks(regime, clusters, u_star):
    """The nine Gate 0 families with their best member, exact regret and expected utility."""
    profiles = sum(regime['profiles'][cluster] for cluster in clusters)  # int-sum
    flat = _sum_cells(regime['arm_total'], clusters)
    buckets = sorted({bucket for cluster in clusters for bucket in regime['buckets'][cluster]})
    member = argmax_first([(rule, flat[index]) for index, rule in enumerate(policies.F_RULES)])
    blocks, cells = {}, {}
    blocks['F'] = {'regret': _regret(u_star, flat[policies.RULE_INDEX[member]]),
                   'expected_u': flat[policies.RULE_INDEX[member]] / profiles,
                   'best_member': member}
    cells['F'] = 1
    for family in ('F_size', 'F_hist', 'F_hist_plus'):
        grouped = {}
        if family == 'F_size':
            for bucket in buckets:
                keys = [(cluster, bucket) for cluster in clusters
                        if (cluster, bucket) in regime['size_cells']]
                grouped[bucket] = _sum_cells(regime['size_cells'], keys)
        elif family == 'F_hist':
            for bucket in buckets:
                for kind in simulator.TYPES:
                    keys = [(cluster, kind, bucket) for cluster in clusters
                            if (cluster, kind, bucket) in regime['hist_cells']]
                    if keys:
                        grouped[f'{kind}|{bucket}'] = _sum_cells(regime['hist_cells'], keys)
        else:
            for (counts, bucket), row in regime['plus_cells'].items():
                if bucket in buckets:
                    grouped[f'{counts}|{bucket}'] = row
        members, value = _best(grouped)
        blocks[family] = {'regret': _regret(u_star, value), 'expected_u': value / profiles,
                          'best_member': members}
        cells[family] = len(members)
    for name in SINGLE_ARMS:
        total = flat[policies.PROGRAM_ARMS.index(name)]
        blocks[name] = {'regret': _regret(u_star, total), 'expected_u': total / profiles}
        if name in ALIASES:
            blocks[name]['alias_of'] = ALIASES[name]
        extras = {key: fsum_(regime['extras'][cluster][name][key] for cluster in clusters)
                  / profiles for key in EXTRA_METRICS}
        blocks[name]['expected_safe'] = extras['safe']
        blocks[name]['expected_cost_units'] = extras['cost']
        if name == 'guarded_read':
            blocks[name]['dominated_reads'] = extras['reads']
    return blocks, cells, flat, profiles


def _cluster_blocks(regime, clusters, blocks):
    """The set-selected members re-scored on each cluster (design 1.4 cluster form)."""
    out = {}
    for cluster in clusters:
        u_star = regime['u_star'][cluster]
        values = {'F': regime['arm_total'][cluster][policies.RULE_INDEX[blocks['F']['best_member']]]}
        for family, keys in (('F_size', regime['size_cells']), ('F_hist', regime['hist_cells'])):
            members, total = blocks[family]['best_member'], []
            for cell_id, member in members.items():
                parts = cell_id.split('|')
                key = (cluster, parts[0]) if family == 'F_size' else (cluster, parts[0], parts[1])
                if key in keys:
                    total.append(keys[key][policies.RULE_INDEX[member]])
            values[family] = fsum_(total)
        for name in SINGLE_ARMS:
            index = policies.PROGRAM_ARMS.index(name)
            values[name] = regime['arm_total'][cluster][index]
        out[cluster] = {'expected_u_star': u_star / regime['profiles'][cluster],
                        'expected_u_star_total': u_star, 'profiles': regime['profiles'][cluster],
                        'families': {name: _regret(u_star, value)
                                     for name, value in values.items()}}
    return out


def _single_rule(flat, u_star, epsilon):
    """The literal reading: does this one rule stay within epsilon at this regime?"""
    members = [(rule, _regret(u_star, flat[index]))
               for index, rule in enumerate(policies.F_RULES)]
    within = [rule for rule, regret in members if regret <= epsilon]
    return {'within_epsilon': bool(within), 'member': within[0] if within else None,
            'members': len(within)}


def _set_rows(totals, clusters, registration):
    """Every regime row of one instance set, in the pre-registered regime order."""
    epsilon = registration['gate0']['epsilon']
    rows, flats = [], {}
    for item in costs.REGIMES:
        regime_id = item['regime_id']
        regime = totals[regime_id]
        u_star = fsum_(regime['u_star'][cluster] for cluster in clusters)
        blocks, cells, flat, profiles = _family_blocks(regime, clusters, u_star)
        flats[regime_id] = flat
        fixed = [(family, blocks[family]['expected_u'] * profiles)
                 for family in ('F', 'F_size', 'F_hist')]
        argmin = argmax_first(fixed)
        rows.append({'regime_id': regime_id, 'kappa': item['kappa'], 'L': item['L'],
                     'primary': item['primary'], 'profiles': profiles,
                     'expected_u_star': u_star / profiles,
                     'admissible': costs.admissible(u_star / profiles, registration),
                     'min_fixed_r': min(blocks[family]['regret']
                                        for family in ('F', 'F_size', 'F_hist')),
                     'argmin': {'family': argmin, 'member': blocks[argmin]['best_member']},
                     'families': blocks, 'cells': cells,
                     'single_rule_literal': _single_rule(flat, u_star, epsilon),
                     'per_cluster': _cluster_blocks(regime, clusters, blocks)})
    return rows, flats


def single_rule_literal(rows, flats, registration):
    """Does one f in F have regret <= epsilon in every admissible regime (design 1.5)?"""
    epsilon = registration['gate0']['epsilon']
    admissible = [row for row in rows if row['admissible']]
    qualified = []
    for index, rule in enumerate(policies.F_RULES):
        if all(_regret(row['expected_u_star'] * row['profiles'], flats[row['regime_id']][index])
               <= epsilon for row in admissible):
            qualified.append(rule)
    return {'within_epsilon_all_admissible': bool(qualified),
            'member': qualified[0] if qualified else None, 'members': len(qualified),
            'admissible_regimes': [row['regime_id'] for row in admissible]}


def decision(rows, registration, model, rev1_trigger=None):
    """The pre-registered Gate 0 decision quantities and the live-round verdict (design 1.5)."""
    epsilon = registration['gate0']['epsilon']
    admissible = [row for row in rows if row['admissible']]
    hard_stop = all(row['min_fixed_r'] <= epsilon for row in admissible)
    primary = next(row for row in rows if row['primary'])
    primary_inadmissible = not costs.admissible(primary['expected_u_star'], registration)
    trigger = hard_stop or primary_inadmissible
    scope = ('mechanism' if not primary_inadmissible and primary['min_fixed_r'] > epsilon
             else 'measurement')
    trigger_rev1 = trigger if model == 'rev1' else rev1_trigger
    if trigger_rev1 is None:
        model_used, verdict = 'unresolved', 'unresolved'
    else:
        model_used = 'd1' if trigger_rev1 else 'rev1'
        if model_used == model:
            verdict = 'FAIL_NEGATIVE' if trigger else 'PASS'
        elif model_used == 'rev1':
            verdict = 'PASS'
        else:  # design 1.5: the D1 map carries the verdict of the selected model
            verdict = 'pending_d1'
    return {'hard_stop': hard_stop, 'primary_inadmissible': primary_inadmissible,
            'trigger': trigger, 'scope': scope, 'live_round_verdict': verdict,
            'model_used': model_used, 'model': model, 'epsilon': epsilon,
            'admissible_regimes': len(admissible),
            'min_fixed_r_primary': primary['min_fixed_r'],
            'trigger_rev1': trigger_rev1}


def regime_map(model, profiles, workers=1, registration=None, regimes=None, rev1_trigger=None,
               progress=False):
    """The body of one Gate 0 map: every family against the DP over the regime grid."""
    registration = registration or prereg()
    regimes = tuple(regimes or costs.REGIME_IDS)
    chosen = sorted(profiles, key=lambda profile: profile['profile_id'])
    previous = policies.set_worker_profiles(chosen)
    tasks = [(profile['profile_id'], regime_id, model)
             for regime_id in regimes for profile in chosen]
    try:
        if workers > 1:
            with multiprocessing.Pool(workers) as pool:
                results = list(pool.imap(_unit, tasks, chunksize=1))
        else:
            results = []
            for task in tasks:
                results.append(_unit(task))
                if progress:
                    print(compact({'cell': list(task[:2]),
                                   'seconds': round(results[-1]['seconds'], 1)}), flush=True)
    finally:
        policies.restore_worker_profiles(previous)
    if progress and workers > 1:
        for result in results:
            print(compact({'cell': [result['profile_id'], result['regime_id']],
                           'seconds': round(result['seconds'], 1)}), flush=True)
    # Results are merged in the task order above, before any summation (design 1.5).
    totals = _accumulate(results)
    body = {'schema': FIXTURE_SCHEMA, 'model': model, 'epsilon': registration['gate0']['epsilon'],
            'regimes_computed': list(regimes), 'sets': {}}
    for label, kind in SETS:
        clusters = sorted({result['cluster_id'] for result in results
                           if kind is None or result['kind'] == kind})
        if not clusters:
            continue
        rows, flats = _set_rows(totals, clusters, registration)
        body['sets'][label] = {
            'clusters': clusters,
            'profiles': rows[0]['profiles'],
            'size_buckets_present': sorted({bucket for cluster in clusters
                                            for bucket in totals[regimes[0]]['buckets'][cluster]}),
            'single_rule_literal': single_rule_literal(rows, flats, registration),
            'decision': decision(rows, registration, model, rev1_trigger),
            'regimes': rows}
    body['decision_set'] = DECISION_SET if DECISION_SET in body['sets'] else 'all'
    body['decision'] = body['sets'][body['decision_set']]['decision']
    body['seconds_cpu'] = fsum_(totals[regime_id]['seconds'] for regime_id in regimes)
    return body


def run(model='rev1', workers=1, output=None, profiles=None, regimes=None, progress=False,
        certificate_path=None):
    """Write one Gate 0 map; refuses to run without a passing INV-DP certificate (design 2.8)."""
    certified, certificate_sha = certificate.require(certificate_path or certificate.OUTPUT)
    registration = prereg()
    chosen = profiles or instances.build_profiles(instances.load())
    rev1_trigger = None
    if model != 'rev1' and Path(OUTPUT['rev1']).exists():
        rev1_trigger = policies.load_gate0('rev1')['decision']['trigger']
    body = regime_map(model, chosen, workers, registration, regimes, rev1_trigger, progress)
    data = {'schema': SCHEMA, 'version': VERSION, 'model': model, 'split': 'development',
            'seen_cluster': True, 'independent_test': False, 'generalization_claim': 'none',
            'epsilon': body['epsilon'], 'workers': workers,
            'certificate_sha256': certificate_sha, 'certificate_status': certified['status'],
            'instances_index_sha256': sha(instances.INDEX), 'prereg_sha256': sha(PREREG),
            'families': list(registration['gate0']['families']),
            'learned_values': registration['gate0']['learned_values'],
            'decision_set': body['decision_set'], 'sets': body['sets'],
            'decision': body['decision'], 'seconds_cpu': body['seconds_cpu'],
            'api_calls': 0, 'cny_spent': '0.000000'}
    write_json_once(Path(output or OUTPUT[model]), data)
    return data


def fixture(workers=1):
    """The committed worker-independence fixture: two tiny synthetic profiles, rev-1, all regimes.

    Measured CPU time is dropped, exactly as `instances --check` excludes
    validation.env_steps_per_second, so the remaining bytes must not depend on the worker count.
    """
    body = regime_map('rev1', certificate.fixtures()[:2], workers)
    body.pop('seconds_cpu')
    return body


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='rev1', choices=('rev1', 'd1'))
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--fixture', action='store_true')
    args = parser.parse_args()
    clock = time.perf_counter()
    if args.fixture:
        produced = fixture(args.workers)
        write_json_once(args.output or FIXTURE, produced)
        print(compact({'fixture': str(args.output or FIXTURE), 'sha256': sha_json(produced)}))
    else:
        report = run(args.model, args.workers, args.output, progress=True)
        print(compact({'gate0': str(args.output or OUTPUT[args.model]),
                       'sha256': sha_json(report), 'decision': report['decision'],
                       'min_fixed_r': {label: [row['min_fixed_r'] for row in item['regimes']]
                                       for label, item in report['sets'].items()},
                       'seconds_cpu': round(report['seconds_cpu'], 1),
                       'seconds_wall': round(time.perf_counter() - clock, 1)}))
