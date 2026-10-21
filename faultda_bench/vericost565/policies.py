"""Program rule families, the CPU-learned arms and their exact expected utilities."""
import argparse
import json
import math
import multiprocessing
import random
import time
from pathlib import Path

from . import VERSION, certificate, costs, dp, instances, simulator
from .canon import argmax_first, compact, fsum_, sha_json, write_json_once
from ..semantic.tasks import ROOT, sha

LEARNED = ROOT / 'reports/vericost565/learned_policies.json'
LEARNED_D1 = ROOT / 'reports/vericost565/learned_policies_d1.json'
EVALUATION = ROOT / 'reports/vericost565/learned_eval.json'
GATE0 = {'rev1': ROOT / 'reports/vericost565/gate0_rev1_dev.json',
         'd1': ROOT / 'reports/vericost565/gate0_d1_dev.json'}
LEARNED_SCHEMA = 'vericost565.learned.v1'
EVALUATION_SCHEMA = 'vericost565.learned_eval.v1'
# F: the 246 outcome-reactive rules of design 1.5, in the design's fixed order.
ORDERS = ('desc_rows', 'asc_rows', 'smallest_then_desc')
REACTIONS_MIS = ('full', 'patch', 'confirm', 'confirm_escalate', 'escalate')
REACTIONS_FLAG = ('full', 'patch', 'escalate')
SPECIAL_RULES = ('escalate_all', 'never_verify', 'always_full_recompute')
ADAPTED_ARMS = ('static_semantic', 'guarded_read')
FAMILIES = ('F', 'F_size', 'F_hist', 'F_hist_plus')
MAX_SPOTS = 4
# Learned arms (design 2.6): episode counts, seeds and hyper-parameters are pre-registered.
EPISODES_Q_PRIMARY = 400000
EPISODES_Q_OTHER = 100000
EPISODES_THOMPSON = 500000
EPISODES_LINUCB = 50000
SEEDS = {'q': 565001, 'thompson': 565002, 'linucb': 565003}
SEED_RULE = 'random.Random("vericost565|<learner>|<seed>|<regime_id>|<model>")'
EXPLORATION_START, EXPLORATION_END = 0.3, 0.02
DISCOUNT = 1.0
LEARNING_RATE_POWER = 0.6
NIG_PRIOR = {'mu0': 0.0, 'kappa0': 1.0, 'a0': 1.0, 'b0': 1.0}
LINUCB_DIM = 6
LINUCB_FEATURES = ('bias', 'p_none', 'p_local', 'p_global', 'log10(N/5000)', 'max_part_share')
LINUCB_TRAIN_WEIGHT = 1.0
LINUCB_EVAL_WEIGHT = 0.0
REFERENCE_ROWS = costs.REFERENCE_ROWS
VeriCostLinUCB = None  # built by linucb_class(): agent.bandit imports numpy eagerly (plan D5)


def _rule_specs():
    """The 246 rule names: three specials, then 60 (cc=0) + 3 (k=0) + 180 parameterized."""
    specs = {name: None for name in SPECIAL_RULES}
    for check in (0, 1):
        for spots in range(MAX_SPOTS + 1):
            if not check and spots == 0:
                continue
            for r_mis in (REACTIONS_MIS if spots else ('none',)):
                for r_flag in (REACTIONS_FLAG if check else ('none',)):
                    for order in (ORDERS if spots else (ORDERS[0],)):
                        name = f'cc{check}_k{spots}_{order}_mis-{r_mis}_flag-{r_flag}'
                        specs[name] = (check, spots, order, r_mis, r_flag)
    return specs


RULE_SPECS = _rule_specs()
F_RULES = tuple(RULE_SPECS)
RULE_INDEX = {name: index for index, name in enumerate(F_RULES)}
PROGRAM_ARMS = F_RULES + ADAPTED_ARMS
_ORDERS = {}


def part_order(profile, order):
    """The rule's spot order over parts; ties go to the lower part index (design 1.5)."""
    rows = tuple(part['rows'] for part in profile['parts'])
    key = (profile['profile_id'], rows, order)
    if key not in _ORDERS:
        descending = sorted(range(len(rows)), key=lambda part: (-rows[part], part))
        ascending = sorted(range(len(rows)), key=lambda part: (rows[part], part))
        if order == 'desc_rows':
            chosen = descending
        elif order == 'asc_rows':
            chosen = ascending
        else:
            chosen = [ascending[0]] + [part for part in descending if part != ascending[0]]
        _ORDERS[key] = tuple(chosen)
    return _ORDERS[key]


def counts_key(counts):
    return '-'.join(str(counts[key]) for key in simulator.COUNT_KEYS)


def size_cell(state):
    return state['profile']['size_bucket']


def hist_cell(state):
    """The F_hist cell: MAP deployment type of the public history x size bucket."""
    return simulator.map_type(state['counts']) + '|' + state['profile']['size_bucket']


def hist_plus_cell(state):
    return counts_key(state['counts']) + '|' + state['profile']['size_bucket']


# ---- the program rules: pure functions of the public state --------------------------------------
def _post_full(state):
    """After a full_recompute: publish c1 on a mismatch while a decision remains, then stop."""
    if state['full'] == 'mismatch' and state['published'] != 'c1':
        return 'publish_c1' if state['rem'] >= 2 else 'escalate'
    return 'stop'


def _full_reaction(state):
    """full: recompute while two decisions remain (publish plus stop), else escalate."""
    return 'full' if state['rem'] >= 2 else 'escalate'


def _patch_reaction(state):
    if state['published'] == 'patch':
        return 'stop'
    return 'publish_patch' if state['rem'] >= 2 else 'escalate'


def _flag_reaction(spec, state):
    """The reaction to a consistency-check flag of part j."""
    r_flag = spec[4]
    if r_flag == 'escalate':
        return 'escalate'
    if r_flag == 'full':
        return _full_reaction(state)
    flag = state['flag']
    if flag not in state['checked']:
        return ('spot', flag) if state['rem'] >= 3 else 'escalate'
    # The flagged part always mismatches under the latent model; a match leaves nothing to patch.
    return _patch_reaction(state) if flag in state['mismatch'] else 'stop'


def _mismatch_reaction(spec, state):
    """The reaction to a spot mismatch, including the two confirm variants."""
    _, spots, order, r_mis, _ = spec
    if r_mis == 'escalate':
        return 'escalate'
    if r_mis == 'full':
        return _full_reaction(state)
    if r_mis == 'patch':
        return _patch_reaction(state)
    if state['published'] == 'patch':
        return 'stop'
    sequence = part_order(state['profile'], order)
    position = {part: index for index, part in enumerate(sequence)}
    confirmed = (len(state['mismatch']) >= 2
                 or max(position[part] for part in state['checked'])
                 > max(position[part] for part in state['mismatch']))
    if confirmed:
        if len(state['mismatch']) >= 2:  # the confirming spot mismatched too
            return _full_reaction(state) if r_mis == 'confirm' else 'escalate'
        return _patch_reaction(state)
    following = next((part for part in sequence if part not in state['checked']), None)
    if state['rem'] >= 3 and following is not None:
        return ('spot', following)
    return _full_reaction(state) if r_mis == 'confirm' else 'escalate'


def _special_action(rule, state):
    if rule == 'escalate_all':
        return 'escalate'
    if rule == 'never_verify':
        return 'stop'
    return 'full' if state['full'] == 'none' else _post_full(state)


def _program_action(spec, state):
    check, spots, order, _, _ = spec
    if state['full'] != 'none':
        return _post_full(state)
    if state['flag'] is not None:
        return _flag_reaction(spec, state)
    if state['mismatch']:
        return _mismatch_reaction(spec, state)
    if check and state['cc'] == 'none':
        return 'cc'
    planned = min(spots, len(state['profile']['parts']))
    if len(state['checked']) < planned and state['rem'] >= 2:
        following = next((part for part in part_order(state['profile'], order)
                          if part not in state['checked']), None)
        if following is not None:
            return ('spot', following)
    return 'stop'


def rule_action(rule, state):
    """The next action of one F rule: the first applicable item of design 1.5."""
    spec = RULE_SPECS[rule]
    return _special_action(rule, state) if spec is None else _program_action(spec, state)


def gate_equivalents(action, state):
    """Every gate action that executes the same concrete decision (design 2.6 coverage claim)."""
    if not isinstance(action, tuple):
        return (action,) if action in simulator.GATE_ACTIONS else ()
    if action[0] != 'spot':
        return ()
    return tuple(name for name in ('spot_flagged', 'spot_small', 'spot_large')
                 if simulator._resolve_part(state, name) == action[1])


def legal_actions(state):
    """The gate's legal actions, in the pre-registered tie-break order of design 2.6."""
    allowed = {'escalate', 'stop'}
    if state['rem'] >= 2:
        if state['mismatch']:
            allowed.add('publish_patch')
        if state['full'] != 'none':
            allowed.add('publish_c1')
        if state['cc'] == 'none':
            allowed.add('cc')
        if state['flag'] is not None and state['flag'] not in state['checked']:
            allowed.add('spot_flagged')
        if len(state['checked']) < len(state['profile']['parts']):
            allowed.update(('spot_small', 'spot_large'))
        if state['full'] == 'none':
            allowed.add('full')
    return tuple(name for name in simulator.GATE_ACTIONS if name in allowed)


# ---- arms ---------------------------------------------------------------------------------------
class Arm:
    """A deterministic policy over the public state; `name` identifies it in every artifact."""

    family = 'F'
    reads_history = False

    def __init__(self, name):
        self.name = name
        self.fallbacks = 0

    def action(self, state):
        raise NotImplementedError


class RuleArm(Arm):
    def __init__(self, rule, name=None, family='F'):
        super().__init__(name or rule)
        self.rule = rule
        self.family = family

    def action(self, state):
        return rule_action(self.rule, state)


class CellArm(Arm):
    """A per-cell lookup program: F_size, F_hist, F_hist_plus and the Thompson cell selector."""

    reads_history = True

    def __init__(self, name, family, mapping, key):
        super().__init__(name)
        self.family = family
        self.mapping = dict(mapping)
        self.key = key
        self.reads_history = key is not size_cell

    def member(self, state):
        return self.mapping[self.key(state)]

    def action(self, state):
        return rule_action(self.member(state), state)


class GuardedRead(Arm):
    """Plan D4: recompute, then pay one dominated read of the first mismatched part before c1."""

    family = 'guarded_read'

    def __init__(self):
        super().__init__('guarded_read')

    def action(self, state):
        if state['full'] == 'none':
            return 'full'
        if state['full'] == 'match' or state['published'] == 'c1':
            return 'stop'
        if not state.get('reads'):
            target = state['full_parts'][0]
            return ('read', target) if state['rem'] >= 3 else 'escalate'
        return 'publish_c1' if state['rem'] >= 2 else 'escalate'


def f_size(mapping):
    return CellArm('F_size', 'F_size', mapping, size_cell)


def f_hist(mapping):
    return CellArm('F_hist', 'F_hist', mapping, hist_cell)


def f_hist_plus(mapping):
    return CellArm('F_hist_plus', 'F_hist_plus', mapping, hist_plus_cell)


def program_arm(name):
    """One evaluable program arm; static_semantic coincides with always_full_recompute (plan D4)."""
    if name == 'static_semantic':
        return RuleArm('always_full_recompute', 'static_semantic', 'static_semantic')
    if name == 'guarded_read':
        return GuardedRead()
    arm = RuleArm(name)
    if name in SPECIAL_RULES:
        arm.family = name
    return arm


def family_arm(family, member):
    """Rebuild the evaluable arm of a family member recorded in a Gate 0 map."""
    if family in ('F', 'static_semantic', 'guarded_read') or family in SPECIAL_RULES:
        return program_arm(member if family == 'F' else family)
    if family == 'F_size':
        return f_size(member)
    if family == 'F_hist':
        return f_hist(member)
    if family == 'F_hist_plus':
        return f_hist_plus(member)
    raise ValueError('unknown family: ' + str(family))


# ---- exact expected utilities -------------------------------------------------------------------
def _read_step(state, part):
    """A paged read: billed the full part scan, and the abstract state never changes (design 2.6)."""
    new = dict(state)
    new['rem'] = state['rem'] - 1
    new['spent'] = state['spent'] + costs.cost(state['profile'], state['regime'], 'read_rows', part)
    new['reads'] = state.get('reads', 0) + 1
    if new['rem'] <= 0 and not new['terminal']:
        new['terminal'] = 'horizon'
    return new


def _certified(state):
    """Does the public history certify completion (design 2.4, as environment.certified_complete)?"""
    if state['full'] == 'match' or state['published'] == 'c1':
        return True
    return (state['published'] == 'patch'
            and len(state['checked']) == len(state['profile']['parts']))


def play(arm, profile, regime_id, counts, latent):
    """One deterministic episode of an arm against one latent; the arm sees public state only."""
    state = simulator.initial_state(profile, counts, regime_id)
    started = arm.fallbacks
    while not state['terminal']:
        action = arm.action(state)
        if isinstance(action, tuple) and action[0] == 'read':
            state = _read_step(state, action[1])
            continue
        state, _ = simulator.step_abstract(state, action, latent)
        if state['full'] != 'none' and 'full_parts' not in state:
            # The full_recompute response publicly lists the mismatched parts (design 2.3).
            state['full_parts'] = tuple(sorted(simulator.affected_parts(
                latent, len(profile['parts']))))
    outcome = state['outcome']
    return {'u': simulator.utility_of(state), 'safe': 1.0 if outcome['safe_complete'] else 0.0,
            'false_completion': 1.0 if outcome['false_completion'] else 0.0,
            'forbidden_effect': 1.0 if outcome['forbidden_effect'] else 0.0,
            'cost': state['spent'], 'reads': float(state.get('reads', 0)),
            'fallback': float(arm.fallbacks - started),
            'unsupported_escalation': 1.0 if state['terminal'] == 'escalate' and _certified(state)
            else 0.0, 'decisions': float(simulator.HORIZON - state['rem'])}


METRICS = ('u', 'safe', 'false_completion', 'forbidden_effect', 'cost', 'reads', 'fallback',
           'unsupported_escalation', 'decisions')


def mix(weights, rows):
    """Mix per-latent metrics by a belief; math.fsum is the only float accumulator."""
    total = fsum_(weights)
    return {key: fsum_([weight * row[key] for weight, row in zip(weights, rows)]) / total
            for key in METRICS}


def latent_rows(arm, profile, regime_id, model, counts):
    """The arm's metrics under every latent of the model, in simulator.latents order."""
    return [play(arm, profile, regime_id, counts, latent)
            for latent in simulator.latents(model, len(profile['parts']))]


def expected(arm, profile, regime_id, counts, model='rev1', rows=None):
    """The exact expectation over latents given one public history."""
    prior = simulator.latent_prior(profile, counts, model)
    latents = simulator.latents(model, len(profile['parts']))
    if rows is None:
        rows = latent_rows(arm, profile, regime_id, model, counts)
    return mix([prior[latent] for latent in latents], rows)


def expected_u(arm, profile, regime_id, counts, model='rev1', eu_star=None):
    """E[U] of one arm by exact enumeration; c4_assert fires before the caller aggregates."""
    arm = arm if isinstance(arm, Arm) else program_arm(arm)
    value = expected(arm, profile, regime_id, counts, model)['u']
    if eu_star is not None:
        certificate.c4_assert(arm.name, profile, regime_id, value, eu_star)
    return value


def program_rows(profile, regime_id, model, counts=None):
    """Per-latent metrics of all 248 program arms; F rules never read the history, so one pass
    serves every cell of the regime map (the factorization of design 1.5)."""
    counts = counts or instances.VALIDATION_COUNTS
    return {name: latent_rows(program_arm(name), profile, regime_id, model, counts)
            for name in PROGRAM_ARMS}


# ---- the learned arms ---------------------------------------------------------------------------
def _require_development(profiles):
    for profile in profiles:
        if profile.get('split') != 'development':
            raise ValueError('non-development profile in training')
    return sorted(profiles, key=lambda profile: profile['profile_id'])


def _seeded(learner, regime_id, model):
    return random.Random(f'vericost565|{learner}|{SEEDS[learner]}|{regime_id}|{model}')


def training_latent(draw, profile, model):
    """The latent of one training draw; rev-1 and D1 share the draw (simulator._draw)."""
    if draw['latent_class'] == 'none':
        return ('none',)
    if draw['latent_class'] == 'local':
        return ('local', draw['part'], draw['cc_visible'])
    mask = draw['mask'] if model == 'd1' else (1 << len(profile['parts'])) - 1
    return ('global', mask)


def thompson_cells(profiles):
    """The F_hist cells of the training set: MAP type x size bucket, in sorted order."""
    buckets = sorted({profile['size_bucket'] for profile in profiles})
    return tuple(f'{kind}|{bucket}' for bucket in buckets for kind in simulator.TYPES)


def train_q(profiles, regime_id, episodes, model='rev1'):
    """Tabular Q over the abstract state with the nine gate actions (design 2.6)."""
    profiles = _require_development(profiles)
    by_id = {profile['profile_id']: profile for profile in profiles}
    rng = _seeded('q', regime_id, model)
    table, visits, updates = {}, {}, 0
    span = max(1, episodes - 1)
    for episode in range(episodes):
        explore = EXPLORATION_START + (EXPLORATION_END - EXPLORATION_START) * episode / span
        draw = simulator.sample_episode(rng, profiles)
        profile = by_id[draw['profile_id']]
        latent = training_latent(draw, profile, model)
        state = simulator.initial_state(profile, draw['counts'], regime_id)
        while not state['terminal']:
            key = simulator.state_key(state)
            actions = legal_actions(state)
            row = table.setdefault(key, {})
            if rng.random() < explore:
                action = actions[rng.randrange(len(actions))]
            else:
                action = argmax_first([(name, row.get(name, 0.0)) for name in actions])
            following, reward = simulator.step_abstract(state, action, latent)
            target = reward
            if not following['terminal']:
                next_row = table.get(simulator.state_key(following), {})
                next_actions = legal_actions(following)
                target += DISCOUNT * max([next_row.get(name, 0.0) for name in next_actions])
            count = visits.get((key, action), 0) + 1
            visits[(key, action)] = count
            rate = 1 / (1 + count) ** LEARNING_RATE_POWER
            row[action] = row.get(action, 0.0) + rate * (target - row.get(action, 0.0))
            updates += 1
            state = following
    return {'q': {key: table[key] for key in sorted(table)},
            'stats': {'episodes': episodes, 'states': len(table), 'pairs': len(visits),
                      'updates': updates}}


def nig_update(posterior, reward):
    """One Normal-Inverse-Gamma observation: (mu, kappa, a, b, n) -> the updated posterior."""
    mu, kappa, shape, scale, count = posterior
    kappa_n = kappa + 1
    return (mu + (reward - mu) / kappa_n, kappa_n, shape + 0.5,
            scale + kappa * (reward - mu) ** 2 / (2 * kappa_n), count + 1)


def nig_posterior(count):
    """kappa_n and a_n are determined by the pull count, so the artifact stores mu_n, b_n and n."""
    return NIG_PRIOR['kappa0'] + count, NIG_PRIOR['a0'] + count / 2


def train_thompson(profiles, regime_id, episodes, model='rev1'):
    """One Normal-Inverse-Gamma arm per (F_hist cell, rule): 9 cells x 246 rules (design 2.6)."""
    profiles = _require_development(profiles)
    by_id = {profile['profile_id']: profile for profile in profiles}
    rng = _seeded('thompson', regime_id, model)
    prior = (NIG_PRIOR['mu0'], NIG_PRIOR['kappa0'], NIG_PRIOR['a0'], NIG_PRIOR['b0'], 0)
    cells = {cell: [prior] * len(F_RULES) for cell in thompson_cells(profiles)}
    utility, pulls = {}, 0
    for _ in range(episodes):
        draw = simulator.sample_episode(rng, profiles)
        profile = by_id[draw['profile_id']]
        latent = training_latent(draw, profile, model)
        cell = simulator.map_type(draw['counts']) + '|' + profile['size_bucket']
        row = cells[cell]
        best, score = 0, None
        for index, (mu, kappa, shape, scale, _) in enumerate(row):
            variance = 1 / rng.gammavariate(shape, 1 / scale)
            sample = rng.gauss(mu, math.sqrt(variance / kappa))
            if score is None or sample > score:
                best, score = index, sample
        key = (draw['profile_id'], best, simulator.latent_id(latent))
        if key not in utility:
            utility[key] = play(program_arm(F_RULES[best]), profile, regime_id, draw['counts'],
                                latent)['u']
        row[best] = nig_update(row[best], utility[key])
        pulls += 1
    table = {}
    for cell in sorted(cells):
        table[cell] = {F_RULES[index]: [item[0], item[3], item[4]]
                       for index, item in enumerate(cells[cell]) if item[4]}
    return {'thompson': table,
            'stats': {'episodes': episodes, 'cells': len(cells), 'arms': len(cells) * len(F_RULES),
                      'arms_pulled': sum(len(row) for row in table.values()),  # int-sum
                      'pulls': pulls}}


def linucb_class():
    """Build the subclass lazily: `select` is re-implemented because the parent's ucb is a
    closure (review-5 NIT 6), and agent.bandit imports numpy at module level (plan D5)."""
    global VeriCostLinUCB
    if VeriCostLinUCB is None:
        import numpy
        from agent.bandit import LinUCBBandit

        class VeriCostLinUCB(LinUCBBandit):
            """LinUCB with the pre-registered tie-break: earliest-listed wins at round(., 12)."""

            def select(self, x):
                items = []
                for action in self.actions:
                    inverse = numpy.linalg.inv(self.A[action])
                    theta = inverse @ self.b[action]
                    items.append((action, float(theta @ x + self.alpha
                                                * numpy.sqrt(x @ inverse @ x))))
                return argmax_first(items)

    return VeriCostLinUCB


def context(profile, counts):
    """x = [1, p_none, p_local, p_global, log10(N/5000), max_part_share] (design 2.6)."""
    none, local, glob = simulator.predictive(counts)
    return [1.0, none, local, glob, math.log10(profile['n'] / REFERENCE_ROWS),
            max(part['share'] for part in profile['parts'])]


def _solve(matrix, vector):
    """Gaussian elimination with partial pivoting; the stdlib path of plan D5."""
    size = len(vector)
    rows = [[float(matrix[row][column]) for column in range(size)] + [float(vector[row])]
            for row in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(rows[row][column]))
        if abs(rows[pivot][column]) == 0.0:
            raise ValueError('singular design matrix')
        rows[column], rows[pivot] = rows[pivot], rows[column]
        for row in range(size):
            if row == column:
                continue
            factor = rows[row][column] / rows[column][column]
            if factor:
                rows[row] = [rows[row][index] - factor * rows[column][index]
                             for index in range(size + 1)]
    return [rows[row][size] / rows[row][row] for row in range(size)]


def linucb_score(matrix, vector, x, alpha):
    """theta.x + alpha*sqrt(x.A^-1.x) without numpy, so every evaluator runs stdlib-only."""
    theta = _solve(matrix, vector)
    spread = _solve(matrix, list(x))
    mean = fsum_([theta[index] * x[index] for index in range(len(x))])
    width = fsum_([x[index] * spread[index] for index in range(len(x))])
    return mean + alpha * math.sqrt(max(0.0, width))


def train_linucb(profiles, regime_id, episodes, model='rev1'):
    """The LinUCB rule selector; numpy and agent.bandit are imported here and nowhere else."""
    profiles = _require_development(profiles)
    by_id = {profile['profile_id']: profile for profile in profiles}
    import numpy
    bandit = linucb_class()(LINUCB_DIM, list(F_RULES), LINUCB_TRAIN_WEIGHT)
    rng = _seeded('linucb', regime_id, model)
    utility, selections = {}, {}
    for _ in range(episodes):
        draw = simulator.sample_episode(rng, profiles)
        profile = by_id[draw['profile_id']]
        latent = training_latent(draw, profile, model)
        x = numpy.asarray(context(profile, draw['counts']), dtype=float)
        rule = bandit.select(x)
        key = (draw['profile_id'], rule, simulator.latent_id(latent))
        if key not in utility:
            utility[key] = play(program_arm(rule), profile, regime_id, draw['counts'], latent)['u']
        bandit.update(rule, x, utility[key])
        selections[rule] = selections.get(rule, 0) + 1
    matrices, vectors = {}, {}
    for rule in F_RULES:
        if rule not in selections:
            continue  # untouched actions keep A = I and b = 0, recorded in the artifact header
        matrices[rule] = [float(bandit.A[rule][row][column]) for row in range(LINUCB_DIM)
                          for column in range(row, LINUCB_DIM)]
        vectors[rule] = [float(value) for value in bandit.b[rule]]
    return {'linucb': {'a_upper': matrices, 'b': vectors},
            'stats': {'episodes': episodes, 'rules_selected': len(selections)}}


def numpy_config():
    """The numpy/BLAS summary audit.py compares before attempting a byte-identical replay."""
    import numpy
    summary = {'numpy': numpy.__version__, 'blas': 'unknown', 'lapack': 'unknown'}
    try:
        config = numpy.show_config(mode='dicts') or {}
    except TypeError:  # pragma: no cover - older numpy without the dict mode
        return summary
    for key, label in (('Build Dependencies', 'blas'), ('Build Dependencies', 'lapack')):
        entry = (config.get(key) or {}).get(label) or {}
        if entry:
            summary[label] = f"{entry.get('name', 'unknown')} {entry.get('version', '')}".strip()
    return summary


def expand_matrix(upper, size=LINUCB_DIM):
    """Rebuild the symmetric A from its stored upper triangle."""
    matrix = [[0.0] * size for _ in range(size)]
    index = 0
    for row in range(size):
        for column in range(row, size):
            matrix[row][column] = matrix[column][row] = upper[index]
            index += 1
    return matrix


class QArm(Arm):
    """Greedy tabular Q; an unseen state falls back to the dev-selected F_hist member."""

    family = 'q_only'
    reads_history = True

    def __init__(self, table, fallback):
        super().__init__('q_only')
        self.table = table
        self.fallback = dict(fallback)

    def action(self, state):
        row = self.table.get(simulator.state_key(state))
        if row is None:
            self.fallbacks += 1
            return rule_action(self.fallback[hist_cell(state)], state)
        return argmax_first([(name, row.get(name, 0.0)) for name in legal_actions(state)])


class LinUCBArm(Arm):
    """The LinUCB selector at alpha = 0, scored through the stdlib linucb_score (plan D5)."""

    family = 'linucb'
    reads_history = True

    def __init__(self, upper, vectors, alpha=LINUCB_EVAL_WEIGHT):
        super().__init__('linucb')
        self.identity = [[1.0 if row == column else 0.0 for column in range(LINUCB_DIM)]
                         for row in range(LINUCB_DIM)]
        self.matrices = {rule: expand_matrix(upper[rule]) for rule in upper}
        self.vectors = dict(vectors)
        self.alpha = alpha
        self.choice = {}

    def member(self, state):
        key = (state['profile']['profile_id'], counts_key(state['counts']))
        if key not in self.choice:
            x = context(state['profile'], state['counts'])
            self.choice[key] = argmax_first(
                [(rule, linucb_score(self.matrices.get(rule, self.identity),
                                     self.vectors.get(rule, [0.0] * LINUCB_DIM), x, self.alpha))
                 for rule in F_RULES])
        return self.choice[key]

    def action(self, state):
        return rule_action(self.member(state), state)


def thompson_arm(table):
    """Posterior-mean argmax per cell, ties in F order (design 2.6)."""
    mapping = {}
    for cell, row in table.items():
        mapping[cell] = argmax_first([(rule, row[rule][0] if rule in row else NIG_PRIOR['mu0'])
                                      for rule in F_RULES])
    return CellArm('thompson', 'thompson', mapping, hist_cell)


_CACHE = {}


def cached(key, builder):
    """Per-process memo so a multiprocessing worker rebuilds profiles and artifacts once."""
    if key not in _CACHE:
        _CACHE[key] = builder()
    return _CACHE[key]


def worker_profiles():
    return cached('profiles', lambda: {profile['profile_id']: profile
                                       for profile in instances.build_profiles(instances.load())})


def set_worker_profiles(profiles):
    """Seed the per-process memo before a Pool forks; returns the mapping it replaced."""
    previous = _CACHE.get('profiles')
    _CACHE['profiles'] = {profile['profile_id']: profile for profile in profiles}
    return previous


def restore_worker_profiles(previous):
    if previous is None:
        _CACHE.pop('profiles', None)
    else:
        _CACHE['profiles'] = previous


def load_gate0(model, path=None):
    """The committed Gate 0 map of one model; no learned value is ever read from it."""
    path = Path(path or GATE0[model])
    if not path.exists():
        raise RuntimeError('gate 0 map missing: ' + str(path))
    return cached(('gate0', str(path)),
                  lambda: json.loads(path.read_text(encoding='utf-8')))


def _regime_row(data, regime_id, instance_set):
    return next(row for row in data['sets'][instance_set]['regimes']
                if row['regime_id'] == regime_id)


def best_fixed(regime_id, model='rev1', instance_set='all', path=None):
    """bf: the development-selected best fixed rule, i.e. Gate 0's argmin over F, F_size, F_hist."""
    row = _regime_row(load_gate0(model, path), regime_id, instance_set)
    family = row['argmin']['family']
    return {'family': family, 'member': row['argmin']['member'],
            'expected_u': row['families'][family]['expected_u'],
            'regret': row['families'][family]['regret']}


def f_hist_members(regime_id, model='rev1', instance_set='all', path=None):
    """The per-regime F_hist member map used as the Q gate's unseen-state fallback."""
    row = _regime_row(load_gate0(model, path), regime_id, instance_set)
    return row['families']['F_hist']['best_member']


def learned_arms(artifact, regime_id, fallback):
    """Rebuild the three learned arms of one regime from a committed training artifact."""
    regime = artifact['regimes'][regime_id]
    return [QArm(regime['q'], fallback), thompson_arm(regime['thompson']),
            LinUCBArm(regime['linucb']['a_upper'], regime['linucb']['b'])]


# ---- training and evaluation runs ---------------------------------------------------------------
def q_episodes(regime_id):
    return EPISODES_Q_PRIMARY if regime_id == costs.PRIMARY else EPISODES_Q_OTHER


def _train_unit(task):
    regime_id, model, learners, scale = task
    profiles = list(worker_profiles().values())
    clock = time.perf_counter()
    out = {'regime_id': regime_id, 'stats': {}}
    episodes = {'q': max(1, int(q_episodes(regime_id) * scale)),
                'thompson': max(1, int(EPISODES_THOMPSON * scale)),
                'linucb': max(1, int(EPISODES_LINUCB * scale))}
    for learner, trainer in (('q', train_q), ('thompson', train_thompson),
                             ('linucb', train_linucb)):
        if learner not in learners:
            continue
        result = trainer(profiles, regime_id, episodes[learner], model)
        out[learner] = result[learner]
        out['stats'][learner] = result['stats']
    out['stats']['seconds'] = time.perf_counter() - clock
    return out


def train(model='rev1', workers=1, regimes=None, learners=('q', 'thompson', 'linucb'), scale=1.0,
          progress=False):
    """Every learned artifact of one model: one independent, seeded run per regime (design 2.6)."""
    regimes = tuple(regimes or costs.REGIME_IDS)
    tasks = [(regime_id, model, learners, scale) for regime_id in regimes]
    if workers > 1:
        with multiprocessing.Pool(workers) as pool:
            results = list(pool.imap(_train_unit, tasks, chunksize=1))
        if progress:
            for result in results:
                print(compact({'trained': result['regime_id'],
                               'seconds': round(result['stats']['seconds'], 1)}), flush=True)
    else:
        results = []
        for task in tasks:
            results.append(_train_unit(task))
            if progress:
                print(compact({'trained': results[-1]['regime_id'],
                               'seconds': round(results[-1]['stats']['seconds'], 1)}), flush=True)
    data = {'schema': LEARNED_SCHEMA, 'version': VERSION, 'model': model, 'split': 'development',
            'seen_cluster': True, 'independent_test': False, 'generalization_claim': 'none',
            'learners': list(learners), 'scale': scale,
            'episodes': {name: value for name, value in (
                ('q', {regime_id: max(1, int(q_episodes(regime_id) * scale))
                       for regime_id in regimes}),
                ('thompson', max(1, int(EPISODES_THOMPSON * scale))),
                ('linucb', max(1, int(EPISODES_LINUCB * scale)))) if name in learners},
            'seeds': {name: SEEDS[name] for name in learners}, 'seed_rule': SEED_RULE,
            'gate_actions': list(simulator.GATE_ACTIONS),
            'q_hyperparameters': {'q0': 0.0, 'gamma': DISCOUNT,
                                  'epsilon': [EXPLORATION_START, EXPLORATION_END],
                                  'learning_rate': '1/(1+n(s,a))**0.6'},
            'thompson_prior': dict(NIG_PRIOR),
            'thompson_storage': 'stored arms carry [mu_n, b_n, n]; kappa_n = kappa0 + n and '
                                'a_n = a0 + n/2; unpulled arms keep the prior',
            'linucb_config': {'dim': LINUCB_DIM, 'features': list(LINUCB_FEATURES),
                              'alpha_train': LINUCB_TRAIN_WEIGHT,
                              'alpha_eval': LINUCB_EVAL_WEIGHT,
                              'a_storage': 'upper triangle row-major; A = I and b = 0 when a rule '
                                           'was never selected'},
            'numpy_config': numpy_config() if 'linucb' in learners else {},
            'instances_index_sha256': sha(instances.INDEX),
            'regimes': {}, 'stats': {}}
    for result in results:
        regime_id = result['regime_id']
        data['regimes'][regime_id] = {key: result[key] for key in ('q', 'thompson', 'linucb')
                                      if key in result}
        data['stats'][regime_id] = result['stats']
    return data


def _evaluate_unit(task):
    profile_id, regime_id, model, instance_set, artifact_path = task
    profile = worker_profiles()[profile_id]
    artifact = cached(('learned', artifact_path),
                      lambda: json.loads(Path(artifact_path).read_text(encoding='utf-8')))
    fallback = f_hist_members(regime_id, model, instance_set)
    bf = best_fixed(regime_id, model, instance_set)
    arms = learned_arms(artifact, regime_id, fallback) + [family_arm(bf['family'], bf['member'])]
    arms[-1].name = 'bf'
    totals = {arm.name: {key: 0.0 for key in METRICS} for arm in arms}
    u_star, clock = 0.0, time.perf_counter()
    for history in simulator.history_states():
        counts, weight = history['counts'], history['weight']
        oracle = dp.Oracle(profile, counts, regime_id, model)
        value = oracle.compact_root()
        u_star += weight * value
        for arm in arms:
            row = expected(arm, profile, regime_id, counts, model)
            certificate.c4_assert(arm.name, profile, regime_id, row['u'], value)
            for key in METRICS:
                totals[arm.name][key] += weight * row[key]
    return {'profile_id': profile_id, 'cluster_id': profile['cluster_id'],
            'kind': profile['kind'], 'regime_id': regime_id, 'u_star': u_star, 'arms': totals,
            'seconds': time.perf_counter() - clock}


def evaluate_learned(model='rev1', workers=1, instance_set='all', artifact=None, regimes=None,
                     profiles=None, progress=False, certificate_path=None):
    """Exact development expected utilities of the learned arms, against bf and the DP."""
    certificate.require(certificate_path or certificate.OUTPUT)
    artifact = Path(artifact or LEARNED)
    chosen = profiles or [item['profile_id'] for item in instances.load()['profiles']]
    if instance_set == 'dev_syn':
        chosen = [item for item in chosen if item.startswith('syn-')]
    regimes = tuple(regimes or costs.REGIME_IDS)
    tasks = [(profile_id, regime_id, model, instance_set, str(artifact))
             for regime_id in regimes for profile_id in sorted(chosen)]
    if workers > 1:
        with multiprocessing.Pool(workers) as pool:
            results = pool.imap(_evaluate_unit, tasks, chunksize=1)
            rows = list(results)
    else:
        rows = [_evaluate_unit(task) for task in tasks]
    per_regime = {}
    for row in rows:  # merged in task order, before any summation
        bucket = per_regime.setdefault(row['regime_id'], {'u_star': 0.0, 'arms': {}, 'clusters': {},
                                                          'profiles': 0, 'seconds': 0.0})
        bucket['u_star'] += row['u_star']
        bucket['profiles'] += 1
        bucket['seconds'] += row['seconds']
        cluster = bucket['clusters'].setdefault(row['cluster_id'], {'u_star': 0.0, 'arms': {}})
        cluster['u_star'] += row['u_star']
        for arm, totals in row['arms'].items():
            into = bucket['arms'].setdefault(arm, {key: 0.0 for key in METRICS})
            every = cluster['arms'].setdefault(arm, {key: 0.0 for key in METRICS})
            for key in METRICS:
                into[key] += totals[key]
                every[key] += totals[key]
        if progress:
            print(compact({'evaluated': row['profile_id'], 'regime': row['regime_id'],
                           'seconds': round(row['seconds'], 1)}), flush=True)
    return per_regime


def _arm_block(bucket, arm):
    """One arm's development expectations, normalized per profile and against the DP."""
    totals, profiles = bucket['arms'][arm], bucket['profiles']
    return {'expected_u': totals['u'] / profiles,
            'regret': (bucket['u_star'] - totals['u']) / bucket['u_star'],
            'expected_safe': totals['safe'] / profiles,
            'expected_cost_units': totals['cost'] / profiles,
            'expected_decisions': totals['decisions'] / profiles,
            'fallback_rule_rate': totals['fallback'] / profiles,
            'dominated_reads': totals['reads'] / profiles,
            'false_completion': totals['false_completion'] / profiles,
            'wrong_publication': totals['forbidden_effect'] / profiles,
            'unsupported_escalation': totals['unsupported_escalation'] / profiles}


def _power_inputs(per_regime, regime_id):
    """Per-cluster delta U of the confirmatory arm against bf, the input of the O2 MDE."""
    bucket = per_regime[regime_id]
    deltas = {}
    for cluster, totals in sorted(bucket['clusters'].items()):
        deltas[cluster] = totals['arms']['q_only']['u'] - totals['arms']['bf']['u']
    values = [deltas[cluster] for cluster in sorted(deltas)]
    mean = fsum_(values) / len(values)
    variance = fsum_([(value - mean) ** 2 for value in values]) / (len(values) - 1)
    return {'regime_id': regime_id, 'arm': 'q_only', 'reference': 'bf',
            'delta_u_by_cluster': deltas, 'n_clusters': len(values), 'mean_delta_u': mean,
            'sd_delta_u': math.sqrt(variance),
            'note': 'cluster totals of E[U], not per-profile means; the MDE amendment multiplies '
                    'sd_delta_u by the pre-registered d_z at n_clusters'}


def evaluation_report(model='rev1', workers=1, instance_set='all', artifact=None, regimes=None,
                      progress=False, certificate_path=None):
    """Assemble learned_eval.json: the exact dev expectations of every learned arm (design 2.6)."""
    certified, certificate_sha = certificate.require(certificate_path or certificate.OUTPUT)
    artifact = Path(artifact or LEARNED)
    per_regime = evaluate_learned(model, workers, instance_set, artifact, regimes,
                                  progress=progress, certificate_path=certificate_path)
    learned = json.loads(artifact.read_text(encoding='utf-8'))
    triggered = load_gate0('rev1')['decision']['trigger']
    data = {'schema': EVALUATION_SCHEMA, 'version': VERSION, 'model': model,
            'split': 'development', 'seen_cluster': True, 'independent_test': False,
            'generalization_claim': 'none', 'instance_set': instance_set,
            'learned_policies_sha256': sha(artifact), 'certificate_sha256': certificate_sha,
            'certificate_status': certified['status'],
            'instances_index_sha256': sha(instances.INDEX),
            'gate0_sha256': {name: sha(path) for name, path in sorted(GATE0.items())
                             if Path(path).exists()},
            'episodes': learned['episodes'], 'seeds': learned['seeds'],
            'numpy_config': learned['numpy_config'], 'regimes': {}, 'per_cluster': {}}
    for regime_id in sorted(per_regime):
        bucket = per_regime[regime_id]
        bf = best_fixed(regime_id, model, instance_set)
        data['regimes'][regime_id] = {
            'expected_u_star': bucket['u_star'] / bucket['profiles'],
            'profiles': bucket['profiles'],
            'q_only': _arm_block(bucket, 'q_only'), 'thompson': _arm_block(bucket, 'thompson'),
            'linucb': _arm_block(bucket, 'linucb'), 'bf_measured': _arm_block(bucket, 'bf'),
            'bf': bf, 'f_hist_members': f_hist_members(regime_id, model, instance_set)}
        data['per_cluster'][regime_id] = {
            cluster: {'expected_u_star': totals['u_star'],
                      'expected_u': {arm: totals['arms'][arm]['u'] for arm in sorted(totals['arms'])}}
            for cluster, totals in sorted(bucket['clusters'].items())}
    data['power_inputs'] = _power_inputs(per_regime, costs.PRIMARY)
    if triggered:
        data['d1_artifacts'] = 'present' if LEARNED_D1.exists() else 'missing'
        data['bf_d1'] = best_fixed(costs.PRIMARY, 'd1', instance_set)
        data['f_hist_members_d1'] = {regime_id: f_hist_members(regime_id, 'd1', instance_set)
                                     for regime_id in sorted(per_regime)}
        data['learned_policies_d1_sha256'] = sha(LEARNED_D1) if LEARNED_D1.exists() else None
    else:
        data['d1_artifacts'] = 'not needed (trigger(rev1, development) false)'
    data['api_calls'] = 0
    data['cny_spent'] = '0.000000'
    return data


def run_training(model='rev1', workers=1, output=None, scale=1.0,
                 learners=('q', 'thompson', 'linucb'), regimes=None, progress=False):
    data = train(model, workers, regimes, learners, scale, progress)
    write_json_once(Path(output or LEARNED), data)
    return data


def run_evaluation(model='rev1', workers=1, output=None, instance_set='all', artifact=None,
                   regimes=None, progress=False):
    data = evaluation_report(model, workers, instance_set, artifact, regimes, progress)
    write_json_once(Path(output or EVALUATION), data)
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--train', action='store_true')
    parser.add_argument('--evaluate', action='store_true')
    parser.add_argument('--model', default='rev1', choices=('rev1', 'd1'))
    parser.add_argument('--split', default='development')
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--instance-set', default='all')
    parser.add_argument('--artifact', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.split != 'development':
        raise SystemExit('this version trains and evaluates on the development split only')
    clock = time.perf_counter()
    if args.train:
        report = run_training(args.model, args.workers, args.output, progress=True)
        print(compact({'learned': str(args.output or LEARNED), 'model': args.model,
                       'sha256': sha_json(report), 'episodes': report['episodes'],
                       'stats': {name: {learner: stats[learner].get('states')
                                        or stats[learner].get('arms_pulled')
                                        or stats[learner].get('rules_selected')
                                        for learner in report['learners']}
                                 for name, stats in report['stats'].items()},
                       'seconds_wall': round(time.perf_counter() - clock, 1)}))
        if args.model == 'rev1' and load_gate0('rev1')['decision']['trigger']:
            # design 1.5: iff trigger(rev1, development), the primary-regime D1 Q gate follows.
            second = run_training('d1', args.workers, LEARNED_D1, learners=('q',),
                                  regimes=(costs.PRIMARY,), progress=True)
            print(compact({'learned': str(LEARNED_D1), 'model': 'd1',
                           'sha256': sha_json(second), 'episodes': second['episodes'],
                           'seconds_wall': round(time.perf_counter() - clock, 1)}))
    if args.evaluate:
        report = run_evaluation(args.model, args.workers, args.output, args.instance_set,
                                args.artifact, progress=True)
        print(compact({'evaluation': str(args.output or EVALUATION), 'sha256': sha_json(report),
                       'regimes': len(report['regimes']),
                       'primary': {arm: report['regimes'][costs.PRIMARY][arm]['regret']
                                   for arm in ('q_only', 'thompson', 'linucb', 'bf_measured')},
                       'bf': report['regimes'][costs.PRIMARY]['bf'],
                       'd1_artifacts': report['d1_artifacts'],
                       'seconds_wall': round(time.perf_counter() - clock, 1)}))
