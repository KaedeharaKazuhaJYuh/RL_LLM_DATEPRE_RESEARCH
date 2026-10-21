"""The frozen offline plan, its write-once preconditions and the development policy comparison."""
import argparse
import json
import multiprocessing
import re
import subprocess
import time
from pathlib import Path

from . import VERSION, certificate, costs, dp, instances, policies, simulator, witness
from .canon import canon, compact, dumps, fsum_, sha_json, write_json_once
from ..multistep.suite import require, same
from ..semantic.tasks import REPO, ROOT, sha

PLAN = ROOT / 'protocols/vericost_v1_plan.json'
REPORTS = ROOT / 'reports/vericost565'
OFFLINE = REPORTS / 'offline_eval.json'
SCHEMA = 'vericost565.plan.v1'
OFFLINE_SCHEMA = 'vericost565.offline_eval.v1'
PREREG_PATH = 'faultda_bench/protocols/vericost_v1_prereg.json'
AMENDMENTS_PATH = 'faultda_bench/protocols/vericost_v1_amendments.json'
PLAN_PATH = 'faultda_bench/protocols/vericost_v1_plan.json'
INDEX_PATH = 'faultda_bench/protocols/vericost_v1_instances.json'
GOLDEN_PATH = 'tests/fixtures/vericost565_semantics_golden.json'
FROZEN_AT_GATE0_PLAN = ('faultda_bench/reports/vericost565/dp_certificate_dev.json',
                        'faultda_bench/reports/vericost565/gate0_rev1_dev.json',
                        'faultda_bench/reports/vericost565/gate0_d1_dev.json',
                        'faultda_bench/reports/vericost565/learned_policies.json',
                        'faultda_bench/reports/vericost565/learned_policies_d1.json',
                        'faultda_bench/reports/vericost565/learned_eval.json',
                        PLAN_PATH)
WRITE_ONCE_OUTPUTS = ('faultda_bench/reports/vericost565/offline_eval.json',
                      'faultda_bench/reports/vericost565/analysis.json',
                      'faultda_bench/reports/vericost565/cross_version.json')
GATE0_ARTIFACTS = tuple(path for path in FROZEN_AT_GATE0_PLAN if path != PLAN_PATH)
FREEZE_PATHS = ('faultda_bench/docs/VERICOST_0565_PREREG.md', PREREG_PATH, INDEX_PATH,
                GOLDEN_PATH, 'tests/fixtures/vericost565_rejection_conditions.txt',
                'faultda_bench/docs/vericost565_exploration')
# The plan pins the modules that produced the frozen evidence. analysis.py and audit.py are
# written after the plan is frozen, so they are pinned by analysis.json and acceptance_v48.
CODE = tuple('faultda_bench/vericost565/%s.py' % name for name in
             ('__init__', 'canon', 'costs', 'instances', 'simulator', 'environment', 'dp',
              'certificate', 'policies', 'witness', 'suite'))
TREE_PATHS = ('faultda_bench/vericost565', 'faultda_bench/protocols', 'faultda_bench/docs',
              'faultda_bench/reports/vericost565', 'tests/fixtures')
ANCHORS = (('C_freeze', PREREG_PATH),
           ('C_gate0a', 'faultda_bench/reports/vericost565/dp_certificate_dev.json'),
           ('C_gate0b', 'faultda_bench/reports/vericost565/gate0_rev1_dev.json'),
           ('C_plan', PLAN_PATH))
STAGES = ('plan', 'offline', 'final')
FAMILY_ARMS = ('bf', 'F', 'F_size', 'F_hist', 'F_hist_plus')
ARMS = FAMILY_ARMS + witness.SINGLE_ARMS + ('q_only', 'thompson', 'linucb')
COUNTED = ('false_completion', 'wrong_publication', 'unsupported_escalation',
           'duplicate_effects', 'fallback_rule', 'dominated_reads')
# head_commit records where the evaluation ran; like validation.env_steps_per_second it is
# excluded from replay comparisons, so a replay at a later commit is still byte-comparable.
VOLATILE = ('head_commit',)
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
DUPLICATE_NOTE = ('duplicate_events is 0 by construction: the abstract transition has no '
                  'request_id retry path, so a duplicate public effect cannot be produced; '
                  'the environment-level idempotency guard is certified by C2 instead')


def failure(label, detail):
    return RuntimeError('precondition (%s) failed: %s' % (label, detail))


# ---- git -----------------------------------------------------------------------------------------
def _run(repo, *args):
    return subprocess.run(('git', '-C', str(repo)) + args, capture_output=True, text=True)


def lines(repo, *args):
    done = _run(repo, *args)
    require(done.returncode == 0, 'git ' + ' '.join(args) + ': ' + done.stderr.strip())
    return [line for line in done.stdout.splitlines() if line]


def commits(repo, path, filter_letter):
    return lines(repo, 'log', '--all', '--diff-filter=' + filter_letter, '--format=%H', '--', path)


def is_ancestor(repo, earlier, later):
    return _run(repo, 'merge-base', '--is-ancestor', earlier, later).returncode == 0


def resolves(repo, revision):
    return _run(repo, 'cat-file', '-e', revision + '^{commit}').returncode == 0


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


# ---- (a) the freeze commit ----------------------------------------------------------------------
def c_freeze(repo=REPO):
    """C_freeze is the unique commit that ADDED the pre-registration and never deleted it."""
    added = commits(repo, PREREG_PATH, 'A')
    deleted = commits(repo, PREREG_PATH, 'D')
    if len(added) != 1 or deleted:
        raise failure('a', 'the pre-registration must have exactly one add and no delete: '
                           'adds=%d deletes=%d' % (len(added), len(deleted)))
    return added[0]


def frozen_paths_unchanged(freeze, repo=REPO):
    done = _run(repo, 'diff', '--quiet', freeze, 'HEAD', '--', *FREEZE_PATHS)
    if done.returncode != 0:
        changed = lines(repo, 'diff', '--name-only', freeze, 'HEAD', '--', *FREEZE_PATHS)
        raise failure('a', 'frozen registration paths changed since C_freeze: ' + ','.join(changed))
    return {'c_freeze': freeze, 'paths': len(FREEZE_PATHS)}


# ---- (b) ancestry and artifact identity ---------------------------------------------------------
def anchors(stage, repo=REPO):
    """The commit chain C_freeze subset C_gate0a subset C_gate0b subset C_plan subset HEAD."""
    wanted = ANCHORS if stage != 'plan' else ANCHORS[:3]
    chain = []
    for label, path in wanted:
        added = commits(repo, path, 'A')
        if len(added) != 1:
            raise failure('b', '%s must add %s exactly once, found %d' % (label, path, len(added)))
        chain.append((label, added[0]))
    for (label, earlier), (following, later) in zip(chain, chain[1:]):
        if not is_ancestor(repo, earlier, later):
            raise failure('b', '%s is not an ancestor of %s' % (label, following))
    head = lines(repo, 'rev-parse', 'HEAD')[0]
    if not is_ancestor(repo, chain[-1][1], head):
        raise failure('b', '%s is not an ancestor of HEAD' % chain[-1][0])
    return {label: commit for label, commit in chain}


def artifacts_match_plan(plan, repo=REPO):
    """Every gate 0 artifact still hashes to the sha256 the plan froze."""
    recorded = plan['artifact_sha256'] if plan else {}
    found = {}
    for path in GATE0_ARTIFACTS:
        target = Path(repo) / path
        if plan and path not in recorded:
            if target.exists():
                raise failure('b', 'artifact present but absent from the plan: ' + path)
            continue
        if not target.exists():
            raise failure('b', 'artifact recorded in the plan is missing: ' + path)
        digest = sha(target)
        if plan and recorded[path] != digest:
            raise failure('b', 'artifact sha256 differs from the plan: ' + path)
        found[path] = digest
    return found


# ---- (c) clean tree and plan identity -----------------------------------------------------------
def clean_tree(repo=REPO):
    """No tracked file under the frozen paths may be locally modified, deleted or renamed.

    Untracked files are ignored on purpose: they are not committed evidence yet, and the files
    a commit is about to add are untracked by definition. That a committed artifact still has
    its committed bytes is asserted by write_once_state, not here.
    """
    dirty = lines(repo, 'status', '--porcelain', '--untracked-files=no', '--', *TREE_PATHS)
    if dirty:
        raise failure('c', 'uncommitted change under the frozen paths: ' + ';'.join(dirty))
    return {'paths': len(TREE_PATHS)}


def plan_matches_protocol(plan, repo=REPO):
    rebuilt = protocol(repo)
    if not same(canon(plan), canon(rebuilt)):
        raise failure('c', 'the committed plan is not the protocol rebuilt from the tree')
    return {'plan_sha256': sha_json(plan)}


# ---- (d) write-once ------------------------------------------------------------------------------
def write_once_state(path, repo=REPO):
    """Added at most once, never modified, never deleted, never renamed; bytes equal the blob."""
    state = {'path': path, 'adds': len(commits(repo, path, 'A')),
             'modifies': len(commits(repo, path, 'M')), 'deletes': len(commits(repo, path, 'D')),
             'renames': len(commits(repo, path, 'R')),
             'present': (Path(repo) / path).exists()}
    if state['adds'] > 1 or state['modifies'] or state['deletes'] or state['renames']:
        state['status'] = 'violated'
    elif state['adds'] == 1:
        tracked = bool(lines(repo, 'ls-files', '--', path))
        if not tracked or not state['present']:
            state['status'] = 'violated'
        else:
            state['status'] = ('committed' if _run(repo, 'diff', '--quiet', 'HEAD', '--',
                                                   path).returncode == 0 else 'violated')
    else:
        state['status'] = 'uncommitted' if state['present'] else 'pending'
    return state


def write_once(paths=None, strict=False, repo=REPO, label='d'):
    """strict: the output must not exist yet, so a producer cannot overwrite earlier evidence."""
    paths = tuple(paths or (FROZEN_AT_GATE0_PLAN + WRITE_ONCE_OUTPUTS))
    states = {}
    for path in paths:
        state = write_once_state(path, repo)
        states[path] = state
        if state['status'] == 'violated':
            raise failure(label, 'write-once violated for %s: adds=%d modifies=%d deletes=%d '
                                 'renames=%d present=%s' % (path, state['adds'], state['modifies'],
                                                            state['deletes'], state['renames'],
                                                            state['present']))
        if strict and state['status'] != 'pending':
            raise failure(label, 'write-once output already produced: ' + path)
    return states


def first_output_commit(repo=REPO):
    """The commit that first added any final evaluation output, or None before it exists."""
    found = []
    for path in WRITE_ONCE_OUTPUTS:
        for commit in commits(repo, path, 'A'):
            found.append(commit)
    for candidate in found:
        if all(candidate == other or is_ancestor(repo, candidate, other) for other in found):
            return candidate
    return found[0] if found else None


# ---- (e') append-only amendments ----------------------------------------------------------------
def _amendment_revisions(freeze, repo=REPO):
    revisions = lines(repo, 'log', '--all', '--format=%H', '--', AMENDMENTS_PATH)
    if freeze not in revisions and resolves(repo, freeze):
        revisions.append(freeze)
    out = []
    for commit in revisions:
        done = _run(repo, 'show', '%s:%s' % (commit, AMENDMENTS_PATH))
        if done.returncode == 0:
            out.append((commit, json.loads(done.stdout)['amendments']))
    return out


def amendments_check(freeze, repo=REPO):
    """Append-only, canonically serialized, allowed kinds, no forbidden key, D10 timing."""
    policy = load(Path(repo) / PREREG_PATH)['amendment_policy']
    text = (Path(repo) / AMENDMENTS_PATH).read_text(encoding='utf-8')
    entries = json.loads(text)['amendments']
    if text != dumps({'amendments': entries}):
        raise failure('e', 'the amendment file is not canonically serialized')
    if [entry['seq'] for entry in entries] != list(range(1, len(entries) + 1)):
        raise failure('e', 'amendment seq numbers are not contiguous from 1')
    boundary = first_output_commit(repo)
    for entry in entries:
        if sorted(entry) != sorted(policy['entry_fields']):
            raise failure('e', 'amendment %s has the wrong fields' % entry.get('seq'))
        if entry['kind'] not in policy['allowed_kinds']:
            raise failure('e', 'amendment kind not allowed: ' + str(entry['kind']))
        if not HEX40.match(str(entry['after_commit'])) or not resolves(repo, entry['after_commit']):
            raise failure('e', 'amendment %s has an unresolvable after_commit' % entry['seq'])
        for key in entry['changes']:
            if key.split('.')[-1] in policy['forbidden']:
                raise failure('e', 'amendment %s touches a forbidden key: %s' % (entry['seq'], key))
        if (boundary and entry['kind'] != 'post_eval_erratum'
                and (entry['after_commit'] == boundary
                     or is_ancestor(repo, boundary, entry['after_commit']))):
            raise failure('e', 'amendment %s of kind %s was appended after the first final output'
                          % (entry['seq'], entry['kind']))
    current = [compact(entry) for entry in entries]
    for commit, earlier in _amendment_revisions(freeze, repo):
        if [compact(entry) for entry in earlier] != current[:len(earlier)]:
            raise failure('e', 'amendments are not append-only; %s differs' % commit[:7])
    return {'entries': len(entries), 'kinds': [entry['kind'] for entry in entries],
            'first_output_commit': boundary}


# ---- (h) rebuildable registration ---------------------------------------------------------------
def rebuilds(repo=REPO):
    """instances --check and the golden fixture must both still reproduce byte for byte."""
    try:
        checked = instances.check(Path(repo) / INDEX_PATH)
    except ValueError as error:
        raise failure('h', str(error))
    if (Path(repo) / GOLDEN_PATH).read_text(encoding='utf-8') != dumps(instances.golden()):
        raise failure('h', 'the golden semantics fixture does not match a rebuild')
    return {'instances_check': checked['status'], 'golden': 'ok'}


# ---- the precondition gate ----------------------------------------------------------------------
def preconditions(stage='offline', plan_path=None, repo=REPO):
    """(a) freeze, (b) ancestry and artifacts, (c) clean tree, (d) write-once, (e') amendments,
    (h) rebuilds. Stage `offline` is the pre-production gate, so (d) requires the outputs to be
    absent; stage `final` keeps every other check and asserts the write-once invariants instead."""
    require(stage in STAGES, 'unknown precondition stage: ' + str(stage))
    freeze = c_freeze(repo)
    out = {'stage': stage, 'a': frozen_paths_unchanged(freeze, repo)}
    out['anchors'] = anchors(stage, repo)
    plan = None
    if stage != 'plan':
        plan = load(plan_path or (Path(repo) / PLAN_PATH))
    out['b'] = {'artifacts': artifacts_match_plan(plan, repo)}
    out['c'] = clean_tree(repo)
    if plan is not None:
        out['c'].update(plan_matches_protocol(plan, repo))
    out['d'] = write_once(WRITE_ONCE_OUTPUTS, stage == 'offline', repo)
    if stage == 'final':
        out['d'].update(write_once(FROZEN_AT_GATE0_PLAN, False, repo))
    out['e'] = amendments_check(freeze, repo)
    out['h'] = rebuilds(repo)
    return out


# ---- the plan -----------------------------------------------------------------------------------
def protocol(repo=REPO):
    """The plan content, rebuilt from the tree; `--freeze-plan` writes it exactly once."""
    root = Path(repo)
    registration = load(root / PREREG_PATH)
    maps = {model: load(root / path) for model, path in
            (('rev1', 'faultda_bench/reports/vericost565/gate0_rev1_dev.json'),
             ('d1', 'faultda_bench/reports/vericost565/gate0_d1_dev.json'))}
    selected = maps['rev1']['decision']['model_used']
    decision = maps[selected]['decision']
    return {'schema': SCHEMA, 'version': VERSION, 'split': 'development', 'seen_cluster': True,
            'independent_test': False, 'generalization_claim': 'none', 'live_authorized': False,
            'model_used': selected, 'scope': decision['scope'],
            'live_round_verdict': decision['live_round_verdict'],
            'gate0_decision': {model: data['decision'] for model, data in sorted(maps.items())},
            'code_sha256': {path: sha(root / path) for path in CODE},
            'artifact_sha256': {path: sha(root / path) for path in GATE0_ARTIFACTS
                                if (root / path).exists()},
            'write_once': {'frozen_at_gate0_plan': list(FROZEN_AT_GATE0_PLAN),
                           'outputs': list(WRITE_ONCE_OUTPUTS)},
            'seeds': registration['seeds'], 'regimes': registration['regimes'],
            'prereg_sha256': sha(root / PREREG_PATH),
            'instances_index_sha256': sha(root / INDEX_PATH),
            'golden_fixture_sha256': sha(root / GOLDEN_PATH),
            'certificate_sha256': sha(root / GATE0_ARTIFACTS[0]),
            'learned_sha256': sha(root / 'faultda_bench/reports/vericost565/learned_policies.json'),
            'arms': list(ARMS), 'live_protocol': registration['live_protocol'],
            'api_calls': 0, 'cny_spent': '0.000000'}


def freeze_plan(path=None, repo=REPO):
    """Assert the pre-plan preconditions, then write the plan through the single boundary."""
    state = preconditions('plan', repo=repo)
    data = protocol(repo)
    write_json_once(Path(path or (Path(repo) / PLAN_PATH)), data)
    return data, state


# ---- the offline evaluation ---------------------------------------------------------------------
def arms_of(regime_id, model, instance_set, artifact):
    """The thirteen evaluated arms of one regime, in the pre-registered order."""
    row = next(item for item in policies.load_gate0(model)['sets'][instance_set]['regimes']
               if item['regime_id'] == regime_id)
    chosen = policies.best_fixed(regime_id, model, instance_set)
    built = [policies.family_arm(chosen['family'], chosen['member'])]
    built[0].name = 'bf'
    for family in FAMILY_ARMS[1:]:
        arm = policies.family_arm(family, row['families'][family]['best_member'])
        arm.name = family
        built.append(arm)
    built.extend(policies.program_arm(name) for name in witness.SINGLE_ARMS)
    data = policies.cached(('learned', str(artifact)), lambda: load(artifact))
    built.extend(policies.learned_arms(data, regime_id,
                                       policies.f_hist_members(regime_id, model, instance_set)))
    require([arm.name for arm in built] == list(ARMS), 'arm order drifted from the plan')
    return built


def _unit(task):
    """One (profile, regime) cell: exact expectations over the 66 histories, then 3 episodes."""
    profile_id, regime_id, model, instance_set, artifact = task
    profile = policies.worker_profiles()[profile_id]
    arms = arms_of(regime_id, model, instance_set, artifact)
    kappa = costs.regime(regime_id)['kappa']
    clock = time.perf_counter()
    totals = {arm.name: {key: 0.0 for key in policies.METRICS} for arm in arms}
    optima, u_star = {}, 0.0
    for history in simulator.history_states():
        counts, weight = history['counts'], history['weight']
        value = dp.Oracle(profile, counts, regime_id, model).compact_root()
        optima[policies.counts_key(counts)] = value
        u_star += weight * value
        for arm in arms:
            row = policies.expected(arm, profile, regime_id, counts, model)
            certificate.c4_assert(arm.name, profile, regime_id, row['u'], value)
            for key in policies.METRICS:
                totals[arm.name][key] += weight * row[key]
    realized = []
    for kind in simulator.TYPES:
        draw = simulator.episode(profile, kind)
        latent = policies.training_latent(draw, profile, model)
        optimum = optima[policies.counts_key(draw['counts'])]
        for arm in arms:
            row = policies.play(arm, profile, regime_id, draw['counts'], latent)
            realized.append({'cell_id': '%s|%s' % (profile_id, kind), 'regime_id': regime_id,
                             'arm': arm.name, 'latent_id': simulator.latent_id(latent),
                             'u': row['u'], 'safe_complete': row['safe'],
                             'false_completion': row['false_completion'],
                             'agent_wrong_publications': row['forbidden_effect'],
                             'duplicate_events': 0.0,
                             'unsupported_escalation': row['unsupported_escalation'],
                             'decisions': row['decisions'],
                             'billed_bytes': int(round(row['cost'] * profile['b_ref'] / kappa)),
                             'cost_units': row['cost'], 'fallback_rule': row['fallback'],
                             'dominated_reads': row['reads'], 'dp_u': optimum,
                             'realized_regret': optimum - row['u']})
    return {'profile_id': profile_id, 'cluster_id': profile['cluster_id'], 'kind': profile['kind'],
            'regime_id': regime_id, 'u_star': u_star, 'arms': totals, 'realized': realized,
            'seconds': time.perf_counter() - clock}


def _counts_by_arm(realized):
    """Realized per-arm event counts, reported separately for every arm (never pooled)."""
    counts = {name: dict({key: 0 for key in COUNTED}, episodes=0) for name in ARMS}
    for row in realized:
        block = counts[row['arm']]
        block['episodes'] += 1
        block['false_completion'] += int(row['false_completion'])
        block['wrong_publication'] += int(row['agent_wrong_publications'])
        block['unsupported_escalation'] += int(row['unsupported_escalation'])
        block['duplicate_effects'] += int(row['duplicate_events'])
        block['fallback_rule'] += int(row['fallback_rule'])
        block['dominated_reads'] += int(row['dominated_reads'])
    return counts


def evaluation(model='rev1', workers=1, instance_set='all', artifact=None, regimes=None,
               profiles=None, progress=False):
    """Exact expectations and frozen realized episodes for every (profile, regime, arm) cell."""
    artifact = str(artifact or policies.LEARNED)
    regimes = tuple(regimes or costs.REGIME_IDS)
    chosen = sorted(profiles or [item['profile_id'] for item in instances.load()['profiles']])
    tasks = [(profile_id, regime_id, model, instance_set, artifact)
             for regime_id in regimes for profile_id in chosen]
    if workers > 1:
        with multiprocessing.Pool(workers) as pool:
            rows = list(pool.imap(_unit, tasks, chunksize=1))
    else:
        rows = [_unit(task) for task in tasks]
    optimum, expected, realized = [], [], []
    for row in rows:  # merged in task order, before any aggregation
        if progress:
            print(compact({'cell': [row['profile_id'], row['regime_id']],
                           'seconds': round(row['seconds'], 1)}), flush=True)
        optimum.append({'profile_id': row['profile_id'], 'cluster_id': row['cluster_id'],
                        'regime_id': row['regime_id'], 'expected_u_star': row['u_star']})
        for name in ARMS:
            block = row['arms'][name]
            expected.append({'profile_id': row['profile_id'], 'cluster_id': row['cluster_id'],
                             'regime_id': row['regime_id'], 'arm': name,
                             'expected_u': block['u'],
                             'regret': (row['u_star'] - block['u']) / row['u_star'],
                             'expected_safe': block['safe'],
                             'expected_cost_units': block['cost'],
                             'expected_decisions': block['decisions'],
                             'fallback_rule_rate': block['fallback'],
                             'dominated_reads': block['reads']})
        realized.extend(row['realized'])
    return {'optimum': optimum, 'expected': expected, 'realized': realized,
            'counts_by_arm': _counts_by_arm(realized),
            'seconds_cpu': fsum_([row['seconds'] for row in rows])}


def offline_eval(plan_path=None, output_dir=None, workers=1, model='rev1', instance_set='all',
                 artifact=None, replay=False, repo=REPO, progress=False):
    """Assert the preconditions, re-verify the certificate sha256, then write offline_eval.json."""
    state = preconditions('final' if replay else 'offline', plan_path, repo)
    plan = load(plan_path or (Path(repo) / PLAN_PATH))
    certified, certificate_sha = certificate.require()
    if certificate_sha != plan['certificate_sha256']:
        raise failure('b', 'the certificate sha256 differs from the plan')
    body = evaluation(model, workers, instance_set, artifact, progress=progress)
    data = {'schema': OFFLINE_SCHEMA, 'version': VERSION, 'split': 'development',
            'seen_cluster': True, 'independent_test': False, 'generalization_claim': 'none',
            'header': {'head_commit': lines(repo, 'rev-parse', 'HEAD')[0],
                       'prereg_commit': state['anchors']['C_freeze'],
                       'gate0_commit': state['anchors']['C_gate0b'],
                       'plan_commit': state['anchors']['C_plan'],
                       'plan_sha256': sha(plan_path or (Path(repo) / PLAN_PATH)),
                       'learned_sha256': plan['learned_sha256'],
                       'certificate_sha256': certificate_sha,
                       'certificate_status': certified['status'],
                       'instances_check': state['h']['instances_check'], 'golden': state['h']['golden'],
                       'model': model, 'instance_set': instance_set, 'arms': list(ARMS),
                       'replay': bool(replay), 'duplicate_events': DUPLICATE_NOTE},
            'optimum': body['optimum'], 'expected': body['expected'], 'realized': body['realized'],
            'counts_by_arm': body['counts_by_arm'], 'api_calls': 0, 'cny_spent': '0.000000'}
    folder = Path(output_dir or REPORTS)
    write_json_once(folder / 'offline_eval.json', data)
    return data, body['seconds_cpu']


def comparable(data):
    """Canonical text with the volatile header keys dropped, the instances --check convention."""
    data = canon(data)
    data['header'] = {key: value for key, value in data['header'].items() if key not in VOLATILE}
    return compact(data)


def replay(output_dir, workers=1, path=None, **extra):
    """Re-run the offline evaluation into a scratch directory and require byte equality."""
    produced, _ = offline_eval(output_dir=output_dir, workers=workers, replay=True, **extra)
    committed = load(path or OFFLINE)
    return {'path': str(path or OFFLINE), 'identical': comparable(produced) == comparable(committed),
            'volatile': list(VOLATILE), 'sha256_replay': sha_json(produced)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze-plan', type=Path, nargs='?', const=PLAN)
    parser.add_argument('--offline-eval', action='store_true')
    parser.add_argument('--preconditions', choices=STAGES)
    parser.add_argument('--replay', type=Path)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--model', default='rev1', choices=('rev1', 'd1'))
    parser.add_argument('--instance-set', default='all')
    args = parser.parse_args()
    clock = time.perf_counter()
    if args.preconditions:
        print(compact({'preconditions': args.preconditions,
                       'checks': {key: value for key, value in
                                  preconditions(args.preconditions, args.plan).items()
                                  if key in ('stage', 'a', 'e', 'h', 'anchors')},
                       'seconds_wall': round(time.perf_counter() - clock, 1)}))
    if args.freeze_plan:
        frozen, _ = freeze_plan(args.freeze_plan)
        print(compact({'plan': str(args.freeze_plan), 'sha256': sha_json(frozen),
                       'model_used': frozen['model_used'], 'scope': frozen['scope'],
                       'live_round_verdict': frozen['live_round_verdict'],
                       'artifacts': len(frozen['artifact_sha256'])}))
    if args.offline_eval:
        report, spent = offline_eval(args.plan, args.output_dir, args.workers, args.model,
                                     args.instance_set, progress=True)
        print(compact({'offline_eval': str(Path(args.output_dir or REPORTS) / 'offline_eval.json'),
                       'sha256': sha_json(report), 'expected': len(report['expected']),
                       'realized': len(report['realized']), 'arms': len(ARMS),
                       'counts_by_arm': report['counts_by_arm'],
                       'seconds_cpu': round(spent, 1),
                       'seconds_wall': round(time.perf_counter() - clock, 1)}))
    if args.replay:
        print(compact(dict(replay(args.replay, args.workers), plan=str(args.plan or PLAN),
                           seconds_wall=round(time.perf_counter() - clock, 1))))
