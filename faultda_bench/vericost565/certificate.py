"""The INV-DP DP-optimality certificate C1-C5: aggregate only, fatal on any violation."""
import argparse
import hashlib
import json
import math
import multiprocessing
import sys
import time
from decimal import Decimal
from pathlib import Path

from . import VERSION, costs, dp, instances, simulator
from .canon import argmax_first, compact, fsum_, write_json_once
from .environment import VeriCostEnv, transcript
from ..semantic.tasks import REPO, ROOT, sha

OUTPUT = ROOT / 'reports/vericost565/dp_certificate_dev.json'
SCHEMA = 'vericost565.certificate.v1'
MI_THRESHOLD_BITS = 1e-12
MODELS = ('rev1', 'd1')
CODE = ('faultda_bench/vericost565/dp.py', 'faultda_bench/vericost565/environment.py',
        'faultda_bench/vericost565/certificate.py')
FREEZE_TIME = 'freeze_time'
FULL = 'full'
UNIT = 'unit'
PRIMARY_OFFPATH = 'primary_offpath'
# C1: six synthetic G = 3 profiles of 2-5 rows, mixed-sign integers and decimals, horizon 4.
C1_SHAPES = ((2, 2, 2), (2, 3, 4), (3, 3, 3), (2, 4, 5), (4, 4, 2), (5, 3, 2))
C1_HORIZON = 4
C1_REGIMES = ('k0.03_L1', 'k0.03_L3', 'k0.30_L1', 'k0.30_L3')
C1_READ_OFFSETS = (0, 1)
C1_READ_LIMITS = (1, 100)
C1_REQUEST_IDS = ('fresh', 'repeated')
C1_HISTORIES = (('A', {'clean': 8, 'single_part_discrepancy': 1, 'multi_part_discrepancy': 1}),
                ('B', {'clean': 1, 'single_part_discrepancy': 8, 'multi_part_discrepancy': 1}),
                ('C', {'clean': 1, 'single_part_discrepancy': 1, 'multi_part_discrepancy': 8}))
UNIT_C3_SHAPE = (3, 2, 2, 2)
C2_READ_LIMIT = 100
C3_READ_OFFSETS = (0, 100, 200)
PROGRAM_ARMS = ('escalate_all', 'never_verify', 'always_full_recompute')
REJECTED = {'ok': False, 'error': 'tool rejected request; inspect state before retry'}


def violated(part, case):
    """The one failure contract: the case identifier goes to stderr, no output file is written."""
    print(compact({'inv_dp_violated': part, 'case': case}), file=sys.stderr)
    return RuntimeError(f'INV-DP violated: {part}/{case}')


def c4_assert(arm, profile, regime, eu_arm, eu_star, tol=dp.TOL):
    """No realized expected regret may ever be negative: E[U_arm] <= E[U*] + tol."""
    name = profile['profile_id'] if isinstance(profile, dict) else profile
    if float(eu_arm) > float(eu_star) + tol:
        raise violated('C4', f'{arm}|{name}|{regime}|{float(eu_arm) - float(eu_star):.12g}')
    return True


def require(path=OUTPUT):
    """Every evaluator refuses to run without a passing certificate (design 2.8)."""
    path = Path(path)
    if not path.exists():
        raise RuntimeError('INV-DP certificate missing: ' + str(path))
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('status') != 'pass' or any(part['status'] != 'pass' for part in data['parts'].values()):
        raise RuntimeError('INV-DP certificate did not pass: ' + str(path))
    return data, sha(path)


# ---- certificate fixtures ----------------------------------------------------------------------
def _fixture_value(part, index):
    """Mixed-sign integers and decimals, so a read can expose an odd w_j among integers."""
    raw = ((part * 7 + index * 13) % 11) - 5
    if raw == 0:
        raw = part + 1
    return Decimal(raw) if index % 2 else Decimal(raw * 10 + 3) / 10


def _fixture(profile_id, shape):
    rows, first = [], 0
    for part, count in enumerate(shape):
        rows.append(tuple((str(first + index), str(part), _fixture_value(part, index))
                          for index in range(count)))
        first += count
    profile = instances._profile(profile_id, 'synthetic', 'certificate', 'version', 'snapshot',
                                {'source_id': 'certificate', 'path': 'generated'}, rows)
    profile['source']['sha256'] = profile['rows_sha256']
    # One full scan costs exactly kappa, so every operation price is non-trivial at G = 3.
    profile['b_ref'] = float(costs.profile_bytes(profile))
    profile['costs'] = {item['regime_id']: costs.operation_costs(profile, item['regime_id'])
                        for item in costs.REGIMES}
    return profile


def fixtures():
    return [_fixture(f'cert-g3-{index + 1}', shape) for index, shape in enumerate(C1_SHAPES)]


def unit_profile():
    return _fixture('cert-g4-1', UNIT_C3_SHAPE)


# ---- C1: the full-history expectimax over the complete action alphabet --------------------------
class Reference:
    """Reference environment semantics for one latent; byte-certified against VeriCostEnv in C1."""

    def __init__(self, profile, latent):
        self.profile = profile
        self.parts = len(profile['parts'])
        self.mat = instances.materialize(profile, latent)
        self.source = tuple(self.mat.source_strings)
        self.report = tuple(self.mat.report_strings)
        self.flagged = [part for part in range(self.parts)
                        if self.mat.engine_row_counts[part] != profile['parts'][part]['rows']]
        self.mismatched = [part for part in range(self.parts)
                           if self.mat.source_totals[part] != self.mat.report_totals[part]]

    def initial(self):
        return (0, 0, False, 'none', 1, self.report, (), dp.NO_PUBLISH)

    def _page(self, part, offset, limit):
        """Mirrors VeriCostEnv._page, including the 4,096-byte read cap."""
        rows, cursor = [], offset
        total = self.profile['parts'][part]['rows']
        for row in self.mat.page(part, offset, limit):
            trial = {'ok': True, 'part': part, 'rows': rows + [row], 'next_offset': cursor + 1,
                     'truncated': cursor + 1 < total}
            if rows and len(compact(trial).encode()) > 4096:
                break
            rows.append(row)
            cursor += 1
        return rows, cursor, cursor < total

    def respond(self, state, action, params):
        checked, mismatch, cc_done, full, revision, active, requests, pub = state
        if action == 'consistency_check':
            return ({'ok': True, 'flagged_parts': list(self.flagged)},
                    (checked, mismatch, True, full, revision, active, requests, pub))
        if action == 'spot_check':
            part = params['part']
            match = part not in self.mismatched
            return ({'ok': True, 'part': part, 'independent_total': self.source[part],
                     'report_total': self.report[part], 'match': match},
                    (checked | 1 << part, mismatch if match else mismatch | 1 << part, cc_done,
                     full, revision, active, requests, pub))
        if action == 'full_recompute':
            return ({'ok': True, 'match': not self.mismatched,
                     'mismatched_parts': list(self.mismatched), 'candidate_id': 'c1',
                     'independent_totals': list(self.source)},
                    (checked, mismatch, cc_done, 'mismatch' if self.mismatched else 'match',
                     revision, active, requests, pub))
        if action == 'read_rows':
            rows, next_offset, truncated = self._page(params['part'], params['offset'],
                                                      params['limit'])
            return ({'ok': True, 'part': params['part'], 'rows': rows,
                     'next_offset': next_offset, 'truncated': truncated}, state)
        if action in ('stop', 'escalate'):
            return {'ok': True, 'ended': True}, state
        return self._publish(state, params)

    def _publish(self, state, params):
        checked, mismatch, cc_done, full, revision, active, requests, pub = state
        candidate, mode = params['candidate_id'], params['write_mode']
        expected, request_id = params['expected_revision'], params['request_id']
        available = (candidate == 'c1' and full != 'none') or (candidate == 'patch' and mismatch)
        if not available or mode not in ('replace', 'append'):
            return REJECTED, state
        totals = (list(self.source) if candidate == 'c1'
                  else [self.source[part] if checked >> part & 1 else active[part]
                        for part in range(self.parts)])
        fingerprint = compact({'totals': totals, 'expected_revision': expected,
                               'write_mode': mode})
        for stored_id, stored_print, stored_revision in requests:
            if stored_id == request_id:
                if stored_print != fingerprint:
                    return REJECTED, state
                return {'ok': True, 'revision': stored_revision, 'deduplicated': True}, state
        if mode == 'replace' and expected != revision:
            return REJECTED, state
        return ({'ok': True, 'revision': revision + 1, 'deduplicated': False},
                (checked, mismatch, cc_done, full, revision + 1, tuple(totals),
                 requests + ((request_id, fingerprint, revision + 1),),
                 dp.publish_state(pub, candidate, mode, checked)))


def c1_alphabet(parts, rem=None):
    """cc, full, spots, every read page, every publish variant, stop and escalate."""
    out = [('consistency_check', {}), ('full_recompute', {})]
    out += [('spot_check', {'part': part}) for part in range(parts)]
    out += [('read_rows', {'part': part, 'offset': offset, 'limit': limit})
            for part in range(parts) for offset in C1_READ_OFFSETS for limit in C1_READ_LIMITS]
    out += [('publish', {'candidate_id': candidate,
                         'request_id': 'vc-repeat' if kind == 'repeated' else f'vc-{rem}',
                         'expected_revision': 1, 'write_mode': mode})
            for candidate in ('c1', 'patch') for mode in ('replace', 'append')
            for kind in C1_REQUEST_IDS]
    out += [('stop', {}), ('escalate', {})]
    return out


def _action_cost(oracle, action, params):
    if action in ('publish', 'stop', 'escalate'):
        return 0.0
    operation = {'consistency_check': 'consistency_check', 'full_recompute': 'full_recompute',
                 'spot_check': 'spot_check', 'read_rows': 'read_rows'}[action]
    return costs.cost(oracle.profile, oracle.regime_id, operation, params.get('part'))


def c1_full_history(oracle, references):
    """Expectimax whose state is the complete canonical transcript; nothing is abstracted.

    The memo key is the exact value-relevant environment state of every alive latent, which the
    transcript determines, so the memo shares subtrees without coarsening any state.
    """
    weights = oracle.weights
    cache = {}

    def payoff(nodes, stopped):
        terms = []
        for index, state in nodes:
            pub = state[7]
            if stopped:
                ok = oracle.correct(index, pub) and not oracle.forbidden(index, pub)
                terms.append(weights[index] * (costs.V if ok else -oracle.loss))
            elif oracle.forbidden(index, pub):
                terms.append(weights[index] * -oracle.loss)
        return fsum_(terms) / fsum_([weights[index] for index, _ in nodes])

    def value(nodes, rem):
        key = (nodes, rem)
        if key in cache:
            return cache[key]
        if rem <= 0:
            cache[key] = payoff(nodes, False)
            return cache[key]
        total = fsum_([weights[index] for index, _ in nodes])
        items = []
        for action, params in c1_alphabet(oracle.parts, rem):
            label = compact([action, params])
            if action == 'stop':
                items.append((label, payoff(nodes, True)))
                continue
            if action == 'escalate':
                items.append((label, payoff(nodes, False)))
                continue
            groups = {}
            for index, state in nodes:
                response, child = references[index].respond(state, action, params)
                entry = compact({'action': action, 'params': params, 'response': response})
                groups.setdefault(entry, []).append((index, child))
            terms = [-_action_cost(oracle, action, params)]
            for entry in sorted(groups):
                child = tuple(groups[entry])
                terms.append(fsum_([weights[index] for index, _ in child]) / total
                             * value(child, rem - 1))
            items.append((label, fsum_(terms)))
        chosen = argmax_first(items)
        cache[key] = next(value_ for label, value_ in items if label == chosen)
        return cache[key]

    root = tuple((index, references[index].initial()) for index in oracle.root)
    return value(root, oracle.horizon)


def _first_per_tool(alphabet):
    """One first action per tool, so even the reduced responder check still covers publish."""
    seen, out = set(), []
    for action, params in alphabet:
        if action in ('stop', 'escalate') or action in seen:
            continue
        seen.add(action)
        out.append((action, params))
    return out


def _verify_reference(profile, model, references, pairs):
    """Every reference response is byte-identical to VeriCostEnv over singles and ordered pairs."""
    parts = len(profile['parts'])
    singles = c1_alphabet(parts, C1_HORIZON)
    seconds = singles if pairs else _first_per_tool(singles)
    sequences = [(first,) for first in singles] + [(first, second) for first in seconds
                                                   for second in singles]
    counts = instances.VALIDATION_COUNTS
    done = 0
    for index, latent in enumerate(simulator.latents(model, parts)):
        reference = references[index]
        for sequence in sequences:
            env = VeriCostEnv(instances.materialize(profile, latent), counts=counts,
                              regime=costs.PRIMARY)
            state, entries = reference.initial(), []
            for action, params in sequence:
                if env.terminal:
                    break
                env.step(action, params)
                response, state = reference.respond(state, action, params)
                entries.append({'action': action, 'params': params, 'response': response})
            if transcript(env) != compact(entries):
                env.close()
                raise violated('C1', f'responder|{profile["profile_id"]}|'
                                     f'{simulator.latent_id(latent)}|{compact(sequence)}')
            env.close()
            done += 1
    return done


def c1(profile, scope=FULL, tol=dp.TOL):
    """The compact root value equals the exhaustive full-history optimum, for every case."""
    parts = len(profile['parts'])
    histories = C1_HISTORIES if scope == FULL else C1_HISTORIES[:1]
    regimes = C1_REGIMES if scope == FULL else C1_REGIMES[2:]
    counts = {'cases': 0, 'responder_sequences': 0, 'alphabet': len(c1_alphabet(parts, 0))}
    worst = 0.0
    for model in MODELS:
        references = [Reference(profile, latent) for latent in simulator.latents(model, parts)]
        counts['responder_sequences'] += _verify_reference(profile, model, references,
                                                           scope == FULL)
        for label, history in histories:
            for regime_id in regimes:
                oracle = dp.Oracle(profile, history, regime_id, model, C1_HORIZON)
                exhaustive = c1_full_history(oracle, references)
                root = oracle.compact_root()
                counts['cases'] += 1
                worst = max(worst, exhaustive - root)
                if abs(exhaustive - root) > tol:
                    raise violated('C1', f'{profile["profile_id"]}|{model}|{label}|{regime_id}|'
                                         f'{exhaustive - root:.12g}')
    return {'case_counts': counts, 'max_violation': worst}


# ---- C2: information equivalence ----------------------------------------------------------------
def c2_actions(parts):
    out = [('consistency_check', {}), ('full_recompute', {})]
    out += [('spot_check', {'part': part}) for part in range(parts)]
    out += [('read_rows', {'part': part, 'offset': 0, 'limit': C2_READ_LIMIT})
            for part in range(parts)]
    out += [('publish', {'candidate_id': candidate, 'request_id': 'vc-c2',
                         'expected_revision': 1, 'write_mode': 'replace'})
            for candidate in ('c1', 'patch')]
    out += [('stop', {}), ('escalate', {})]
    return out


def _probe(action, params):
    return (action,) if 'part' not in params else (action, params['part'])


def _env_compact_state(env, rem):
    cc = dp.CC_NONE if not env.cc_done else (dp.CC_OK if env.flag is None else env.flag)
    return (cc, dp.mask_of(env.checked), dp.mask_of(env.mismatch), env.full, rem)


def c2(profile, model='rev1', scope=FULL, tol=dp.TOL):
    """Static invariance, byte-identical transcripts per observe group, and state sufficiency."""
    parts = len(profile['parts'])
    actions = instances._single_actions(parts) if scope == FREEZE_TIME else c2_actions(parts)
    sequences = [(first,) for first in actions]
    if scope != FREEZE_TIME:
        sequences += [(first, second) for first in actions for second in actions]
    latents = simulator.latents(model, parts)
    oracle = dp.Oracle(profile, instances.VALIDATION_COUNTS, costs.PRIMARY, model)
    static, steps, runs = None, 0, {}
    for index, latent in enumerate(latents):
        mat = instances.materialize(profile, latent)
        for sequence in sequences:
            env = VeriCostEnv(mat, counts=instances.VALIDATION_COUNTS, regime=costs.PRIMARY)
            signature = instances._static_signature(env.observation())
            if static is None:
                static = signature
            elif signature != static:
                env.close()
                raise violated('C2', f'static|{profile["profile_id"]}|'
                                     f'{simulator.latent_id(latent)}')
            observed = []
            for action, params in sequence:
                if env.terminal:
                    break
                env.step(action, params)
                steps += 1
                observed.append(list(simulator.observe(profile, latent, _probe(action, params))))
            key = compact(sequence)
            runs.setdefault(key, []).append(
                (index, compact(observed), transcript(env),
                 _env_compact_state(env, oracle.horizon - len(env.history))))
            env.close()
    equivalence = _c2_groups(profile, oracle, sequences, runs, scope)
    return {'case_counts': {'latents': len(latents), 'sequences': len(sequences),
                            'env_steps': steps, 'observe_groups': equivalence['groups'],
                            'alive_subset': equivalence['subset'],
                            'alive_exact': equivalence['exact'],
                            'state_sufficiency': equivalence['sufficiency']},
            'static_sha256': hashlib.sha256(static.encode()).hexdigest(),
            'max_violation': equivalence['worst']}


def _c2_groups(profile, oracle, sequences, runs, scope=FULL):
    """Group latents by their observe sequence and compare transcripts and alive sets."""
    groups, subset, exact, sufficiency, worst = 0, 0, 0, 0, 0.0
    for sequence in sequences:
        key = compact(sequence)
        buckets = {}
        for index, observed, text, state in runs[key]:
            buckets.setdefault(observed, []).append((index, text, state))
        groups += len(buckets)
        by_text = {}
        for members in buckets.values():
            if len({text for _, text, _ in members}) != 1:
                raise violated('C2', f'group|{profile["profile_id"]}|{key}')
            for index, text, state in members:
                by_text.setdefault(text, []).append((index, state))
        names = [action for action, _ in sequence]
        if 'read_rows' in names:  # a read restricts alive without entering the compact state
            continue
        for text, members in sorted(by_text.items()):
            alive = tuple(index for index, _ in members)
            state = members[0][1]
            possible = oracle.alive_of(*state[:4])
            if not set(alive) <= set(possible):
                raise violated('C2', f'alive_subset|{profile["profile_id"]}|{key}')
            subset += 1
            if 'full_recompute' not in names:
                if alive != possible:
                    raise violated('C2', f'alive_exact|{profile["profile_id"]}|{key}')
                exact += 1
            if scope == FREEZE_TIME or state[4] < 1 or {'publish', 'stop', 'escalate'} & set(names):
                continue
            general = oracle.general(alive, state[1], state[0] != dp.CC_NONE, state[3],
                                     dp.NO_PUBLISH, state[4])
            gap = abs(general - oracle.compact(*state))
            worst = max(worst, gap)
            sufficiency += 1
            if gap > dp.TOL:
                raise violated('C2', f'sufficiency|{profile["profile_id"]}|{key}|{gap:.12g}')
    return {'groups': groups, 'subset': subset, 'exact': exact, 'sufficiency': sufficiency,
            'worst': worst}


# ---- C3: best-response deviation search, and the C4 sign assertion ------------------------------
def deviations(parts):
    out = [('escalate',), ('stop',), ('cc',), ('full',)]
    out += [('spot', part) for part in range(parts)]
    out += [('read', part, offset) for part in range(parts) for offset in C3_READ_OFFSETS]
    out += [('publish', candidate, mode) for candidate in ('c1', 'patch')
            for mode in ('replace', 'append')]
    return out


def _offpath(oracle, state, action):
    """The general states one deviation off a given state."""
    alive, checked, cc_done, full, pub, rem = state
    kind = action[0]
    if kind in ('escalate', 'stop'):
        return []
    if kind == 'publish':
        available = ((full != 'none') if action[1] == 'c1'
                     else bool(oracle.affected[alive[0]] & checked))
        nxt = dp.publish_state(pub, action[1], action[2], checked) if available else pub
        return [(alive, checked, cc_done, full, nxt, rem - 1)]
    part = action[1] if kind in ('spot', 'read') else None
    out = []
    for key, members in oracle.groups(kind, part, alive):
        next_checked = checked | (1 << part) if kind == 'spot' else checked
        next_full = ('mismatch' if key else 'match') if kind == 'full' else full
        out.append((members, next_checked, cc_done or kind == 'cc', next_full, pub, rem - 1))
    return out


def _check_deviations(oracle, state, label, tol):
    """Q_dev <= V_DP(h) + tol for every action of the extended alphabet."""
    value = oracle.general(*state)
    worst = 0.0
    for action in deviations(oracle.parts):
        gap = oracle.q_value(*state, action) - value
        worst = max(worst, gap)
        if gap > tol:
            raise violated('C3', f'{label}|{compact(list(action))}|{gap:.12g}')
    return worst


def _program_arms(oracle):
    """Exact expected utilities of the three priced program arms, for the C4 sign assertion."""
    total = oracle.mass(oracle.root)
    clean = fsum_([oracle.weights[index] for index in oracle.root
                   if not oracle.affected[index]]) / total
    return {'escalate_all': 0.0,
            'never_verify': clean * costs.V - (1 - clean) * oracle.loss,
            'always_full_recompute': costs.V - oracle.full_cost}


def c3(profile, model, scope=FULL, c3_scope=FULL, tol=dp.TOL):
    """On-path and one-deviation-off-path best-response search, plus C4 on the program arms."""
    regimes = costs.REGIME_IDS if scope == FULL else (costs.PRIMARY,)
    kinds = simulator.TYPES if scope == FULL else simulator.TYPES[:1]
    histories = [(kind, simulator.episode(profile, kind)['counts']) for kind in kinds]
    counts = {'on_path': 0, 'off_path': 0, 'deviations': 0, 'compact_vs_general': 0}
    c4 = {'checks': 0}
    worst, worst_c4, worst_state = 0.0, 0.0, 0.0
    for kind, history in histories:
        for regime_id in regimes:
            oracle = dp.Oracle(profile, history, regime_id, model)
            root = oracle.compact_root()
            for arm, expected in _program_arms(oracle).items():
                c4_assert(arm, profile, regime_id, expected, root, tol)
                c4['checks'] += 1
                worst_c4 = max(worst_c4, expected - root)
            depth2 = c3_scope == FULL or regime_id == costs.PRIMARY
            for compact_state in oracle.onpath():
                alive = oracle.alive_of(*compact_state[:4])
                rem = compact_state[4]
                if not alive or rem < 1:
                    continue
                state = (alive, compact_state[1], compact_state[0] != dp.CC_NONE,
                         compact_state[3], dp.NO_PUBLISH, rem)
                label = f'{profile["profile_id"]}|{model}|{kind}|{regime_id}|{compact_state}'
                gap = abs(oracle.general(*state) - oracle.compact(*compact_state))
                worst_state = max(worst_state, gap)
                counts['compact_vs_general'] += 1
                if gap > tol:
                    raise violated('C3', f'compact|{label}|{gap:.12g}')
                counts['on_path'] += 1
                worst = max(worst, _check_deviations(oracle, state, 'on|' + label, tol))
                counts['deviations'] += len(deviations(oracle.parts))
                if not depth2:
                    continue
                for action in deviations(oracle.parts):
                    for child in _offpath(oracle, state, action):
                        if not child[0] or child[5] < 1:
                            continue
                        counts['off_path'] += 1
                        counts['deviations'] += len(deviations(oracle.parts))
                        worst = max(worst, _check_deviations(oracle, child, 'off|' + label, tol))
    return {'case_counts': counts, 'max_violation': worst, 'max_state_gap': worst_state,
            'c4': c4, 'max_c4_violation': worst_c4}


def c4_self_check():
    """The guard must fire: a hand-built arm with E[U] above the DP's is refused, not recorded."""
    try:
        c4_assert('hand_built_super_optimal', 'cert-g3-1', costs.PRIMARY, 0.9, 0.5)
    except RuntimeError as error:
        return 'INV-DP violated: C4/' in str(error)
    return False


# ---- C5: class-independence of magnitudes -------------------------------------------------------
def _signature(profile, mat, part):
    """The observable fault signature of one part: discrepancy bucket plus read-row bytes."""
    discrepancy = abs(mat.report_totals[part] - mat.source_totals[part])
    bucket = round(math.log10(float(discrepancy)), 1)
    rows = mat.page(part, 0, profile['parts'][part]['rows'])
    return compact([bucket, hashlib.sha256(compact(rows).encode()).hexdigest()])


def _latent_class(latent):
    if latent[0] == 'global':
        return 'global'
    return 'local_visible' if latent[2] else 'local_invisible'


def mutual_information(pairs):
    """Empirical MI in bits between the latent class and the observable signature."""
    joint, left, right = {}, {}, {}
    for first, second in pairs:
        joint[(first, second)] = joint.get((first, second), 0) + 1
        left[first] = left.get(first, 0) + 1
        right[second] = right.get(second, 0) + 1
    total = len(pairs)
    terms = []
    for (first, second), count in sorted(joint.items()):
        share = count / total
        terms.append(share * math.log2(share / (left[first] / total * right[second] / total)))
    return fsum_(terms)


def c5(profile, models=MODELS, threshold=MI_THRESHOLD_BITS):
    parts = len(profile['parts'])
    worst, population = 0.0, 0
    for model in models:
        pairs = []
        for latent in simulator.latents(model, parts):
            if latent[0] == 'none':
                continue
            mat = instances.materialize(profile, latent)
            for part in sorted(mat.affected):
                pairs.append((_latent_class(latent), _signature(profile, mat, part)))
        information = mutual_information(pairs)
        population += len(pairs)
        worst = max(worst, information)
        if information > threshold:
            raise violated('C5', f'{profile["profile_id"]}|{model}|{information:.12g}')
    return {'case_counts': {'population': population, 'profiles': 1}, 'max_violation': worst}


# ---- the run ------------------------------------------------------------------------------------
_WORK = {}


def _unit(task):
    part, name, model, scope, c3_scope = task
    profile = _WORK[name]
    clock = time.perf_counter()
    if part == 'C1':
        result = c1(profile, scope)
    elif part == 'C2':
        result = c2(profile, model, FULL)
    elif part == 'C3':
        result = c3(profile, model, scope, c3_scope)
    else:
        result = c5(profile)
    result['seconds'] = time.perf_counter() - clock
    return part, result


def _merge(part, into, result, seconds):
    for key, value in result['case_counts'].items():
        into['case_counts'][key] = into['case_counts'].get(key, 0) + value
    into['max_violation'] = max(into['max_violation'], result['max_violation'])
    seconds[part] = seconds[part] + result['seconds']
    if part == 'C3':
        into['c4']['checks'] = into['c4']['checks'] + result['c4']['checks']
        into['c4']['max_violation'] = max(into['c4']['max_violation'], result['max_c4_violation'])
        into['max_state_gap'] = max(into['max_state_gap'], result['max_state_gap'])


def _tasks(scope, c3_scope, profiles):
    """Work units in a fixed order; results are merged by part, never by completion order."""
    tasks = []
    chosen = fixtures() if scope == FULL else fixtures()[:2]
    for position, profile in enumerate(chosen):
        _WORK[profile['profile_id']] = profile
        if scope == FULL or position == 0:
            tasks.append(('C1', profile['profile_id'], None, scope, c3_scope))
        tasks.append(('C5', profile['profile_id'], None, scope, c3_scope))
    if scope == FULL:
        first = {}
        for profile in profiles:
            _WORK[profile['profile_id']] = profile
            first.setdefault(profile['kind'], profile['profile_id'])
            tasks.append(('C2', profile['profile_id'], 'rev1', scope, c3_scope))
            tasks.append(('C5', profile['profile_id'], None, scope, c3_scope))
            for model in MODELS:
                tasks.append(('C3', profile['profile_id'], model, scope, c3_scope))
        for name in sorted(first.values()):  # every D1 mask on the first profile of each kind
            tasks.append(('C2', name, 'd1', scope, c3_scope))
    else:
        unit = unit_profile()
        _WORK[unit['profile_id']] = unit
        for profile in chosen:
            tasks.append(('C2', profile['profile_id'], 'd1', scope, c3_scope))
        for model in MODELS:
            tasks.append(('C3', unit['profile_id'], model, scope, c3_scope))
    return sorted(tasks, key=lambda task: tuple(str(field) for field in task))


def run(split='development', workers=1, c3_scope=FULL, scope=FULL, output=OUTPUT):
    """Run every part; write the aggregate certificate only after all five have passed."""
    if split != 'development':
        raise ValueError('this version certifies the development split only')
    profiles = instances.build_profiles(instances.load()) if scope == FULL else []
    tasks = _tasks(scope, c3_scope, profiles)
    parts = {name: {'status': 'pass', 'case_counts': {}, 'max_violation': 0.0}
             for name in ('C1', 'C2', 'C3', 'C4', 'C5')}
    parts['C2']['c2_scope'] = FULL
    parts['C3']['c3_scope'] = c3_scope
    parts['C3']['max_state_gap'] = 0.0
    parts['C3']['c4'] = {'checks': 0, 'max_violation': 0.0}
    seconds = {name: 0.0 for name in parts}
    if workers > 1:
        with multiprocessing.Pool(workers) as pool:  # chunksize 1: balanced, still input-ordered
            results = pool.map(_unit, tasks, chunksize=1)
    else:
        results = [_unit(task) for task in tasks]
    for part, result in results:
        _merge(part, parts[part], result, seconds)
    if not c4_self_check():
        raise violated('C4', 'guard_disabled|c4_assert accepted an arm above the DP optimum')
    parts['C4']['case_counts'] = {'arms': len(PROGRAM_ARMS), 'checks': parts['C3']['c4']['checks'],
                                  'guard_rejections': 1}
    parts['C4']['max_violation'] = parts['C3']['c4']['max_violation']
    parts['C3'].pop('c4')
    data = {'schema': SCHEMA, 'version': VERSION, 'split': split, 'status': 'pass',
            'parts': parts, 'tol': dp.TOL, 'mi_threshold_bits': MI_THRESHOLD_BITS,
            'code_sha256': {name: sha(REPO / name) for name in CODE},
            'instances_index_sha256': sha(instances.INDEX)}
    write_json_once(output, data)
    return data, seconds


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--split', default='development')
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--c3-scope', default=FULL, choices=(FULL, PRIMARY_OFFPATH))
    parser.add_argument('--scope', default=FULL, choices=(FULL, UNIT))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    clock = time.perf_counter()
    report, spent = run(args.split, args.workers, args.c3_scope, args.scope, args.output or OUTPUT)
    print(compact({'status': report['status'], 'workers': args.workers,
                   'parts': {name: part['case_counts'] for name, part in report['parts'].items()},
                   'max_violation': {name: part['max_violation']
                                     for name, part in report['parts'].items()},
                   'seconds_cpu_per_part': {name: round(value, 1) for name, value in spent.items()},
                   'seconds_wall': round(time.perf_counter() - clock, 1)}))
