"""Development instance index: six synthetic profiles and the seen cross-source profiles."""
import argparse
import hashlib
import json
import math
import random
import sys
import time
from decimal import Decimal
from pathlib import Path

from . import VERSION, costs, simulator
from .canon import canon, compact, fsum_, sha_json, write_json_once
from .environment import VeriCostEnv, transcript
from ..clarity.tasks import load as load_cross_source
from ..semantic.tasks import REPO, ROOT, sha

INDEX = ROOT / 'protocols/vericost_v1_instances.json'
GOLDEN = REPO / 'tests/fixtures/vericost565_semantics_golden.json'
SCHEMA = 'vericost565.instances.v1'
GOLDEN_SCHEMA = 'vericost565.golden.v1'
SYNTHETIC_SHARES = (('equal', (1, 1, 1, 1, 1, 1, 1, 1)), ('skewed', (35, 20, 12, 10, 8, 6, 5, 4)))
SYNTHETIC_SIZES = (500, 5000, 50000)
VALIDATION_COUNTS = {'clean': 8, 'single_part_discrepancy': 1, 'multi_part_discrepancy': 1}
MIN_PARTS = 2
GOLDEN_DRAWS = 30
# VeriCost-owned contract text, never the seen task's own text, so the private-label guard holds.
CONTRACTS = {
    'group': ('Sum value per business group over the audited slice; identical duplicate key/group '
              'mappings count once. Keep exactly one active report and correct it with a '
              'compare-and-set replace.'),
    'version': ('Sum value over the partition set selected by version_policy and publish the per '
                'partition totals. Keep exactly one active report and correct it with a '
                'compare-and-set replace.'),
}
SEEDS = {'synthetic_rows': 'closed form, no RNG', 'training_sampler': simulator.TRAINING_SEED,
         'episode': 'sha256("vericost565|" + profile_id + "|" + type)'}


def value_string(value):
    """Serialized field of one row value; a missing value is the empty string (design 1.1)."""
    return '' if value is None else str(Decimal(value).normalize())


def _size_bucket(rows):
    return f'n{rows}' if rows in SYNTHETIC_SIZES else f'seen{rows}'


def _apportion(shares, total):
    """Largest-remainder apportionment of `total` rows over the share vector, at least one each."""
    weight = sum(shares)  # int-sum
    base = [max(1, total * share // weight) for share in shares]
    while sum(base) > total:  # int-sum
        base[base.index(max(base))] -= 1
    remainders = sorted(range(len(shares)), key=lambda j: (-((total * shares[j]) % weight), j))
    step = 0
    while sum(base) < total:  # int-sum
        base[remainders[step % len(shares)]] += 1
        step += 1
    return base


def _synthetic_value(part, index):
    """Deterministic mixed-sign Decimal; every value ends in a non-zero digit at scale -3."""
    if index % 50 == 49:
        return None
    return Decimal(((index * 37 + part * 11) % 199 - 99) * 1000 + 1) / 1000


def _part_rows(part, count, first_id):
    return tuple((str(first_id + index), str(part), _synthetic_value(part, index))
                 for index in range(count))


def _decimal_total(rows):
    total = Decimal(0)
    for row in rows:
        if row[2] is not None:
            total += row[2]
    return total


def _profile(profile_id, kind, cluster_id, family, version_policy, source, part_rows):
    parts, totals, faults, digest = [], [], [], hashlib.sha256()
    for index, rows in enumerate(part_rows):
        body = ''.join(f'{row[0]},{row[1]},{value_string(row[2])}\n' for row in rows)
        digest.update(body.encode())
        parts.append({'part': index, 'rows': len(rows), 'bytes': len(body.encode()), 'share': 0.0})
        totals.append(_decimal_total(rows))
        first = next((row for row in rows if row[2] is not None and row[2] != 0), None)
        if first is not None:
            value = Decimal(first[2])
            faults.append({'part': index, 'row_id': first[0], 'v': str(value),
                           'w': str(value / 10), 'discrepancy': str(9 * (value / 10))})
    total_rows = sum(part['rows'] for part in parts)  # int-sum
    for part in parts:
        part['share'] = part['rows'] / total_rows
    return {'profile_id': profile_id, 'kind': kind, 'cluster_id': cluster_id, 'family': family,
            'split': 'development', 'n': total_rows, 'size_bucket': _size_bucket(total_rows),
            'contract': CONTRACTS[family], 'parts': parts, 'version_policy': version_policy,
            'report_part_totals': [str(total) for total in totals], 'fault_rows': faults,
            'rows_sha256': digest.hexdigest(), 'source': source, 'costs': {}, 'b_ref': 0.0,
            'rows': tuple(part_rows)}


def synthetic_profiles():
    """Six profiles: equal and skewed eight-part shares at N in {500, 5 000, 50 000}."""
    out = []
    for shape, shares in SYNTHETIC_SHARES:
        for size in SYNTHETIC_SIZES:
            counts, rows, first = _apportion(shares, size), [], 0
            for part, count in enumerate(counts):
                rows.append(_part_rows(part, count, first))
                first += count
            profile = _profile(f'syn-{shape}-n{size}', 'synthetic', 'synthetic', 'version',
                               'snapshot', {'source_id': 'synthetic', 'path': 'generated'}, rows)
            profile['source']['sha256'] = profile['rows_sha256']
            out.append(profile)
    return out


def _decimal(text):
    return None if text in (None, '') else Decimal(text)


def _seen_parts(task, rows):
    """Plan D2: group parts are the distinct dimension.group labels, version parts the partitions."""
    if task['contract']['family'] == 'group':
        mapping = {item['key']: item['group'] for item in task['dimension']}
        labels = sorted(set(mapping.values()))
        buckets = {label: [] for label in labels}
        for row in rows:
            buckets[mapping[row['key']]].append((row['id'], row['key'], _decimal(row['value'])))
        return [tuple(buckets[label]) for label in labels]
    width = math.ceil(len(rows) / 8)
    buckets = {}
    for index, row in enumerate(rows):
        buckets.setdefault(index // width, []).append(
            (row['id'], str(index // width), _decimal(row['value'])))
    return [tuple(buckets[key]) for key in sorted(buckets)]


def seen_profiles():
    """The 24 seen cross-source tasks; source bytes are re-verified from the repo CSV, no network."""
    kept, excluded = [], []
    for task in load_cross_source():
        path = REPO / task['source_path']
        if sha(path) != task['source_sha256']:
            raise ValueError('seen source bytes changed: ' + task['source_path'])
        rows = task['versions'][task['catalog'][task['contract']['version_policy']]]
        source = {'source_id': task['source_id'], 'path': task['source_path'],
                  'sha256': task['source_sha256']}
        profile = _profile(task['id'], 'seen_development', task['source_id'],
                           task['contract']['family'], task['contract']['version_policy'],
                           source, _seen_parts(task, rows))
        if len(profile['parts']) < MIN_PARTS:
            excluded.append({'profile_id': task['id'], 'reason': 'too_few_parts'})
        elif len(profile['fault_rows']) != len(profile['parts']):
            excluded.append({'profile_id': task['id'], 'reason': 'fault_unrealizable'})
        else:
            kept.append(profile)
    return kept, excluded


class Materialized:
    """One shared immutable copy of B's rows plus an override map of at most G entries (plan D6)."""

    __slots__ = ('profile', 'latent', 'latent_id', 'parts', 'affected', 'override', 'rows',
                 'report_totals', 'report_strings', 'source_totals', 'source_strings',
                 'engine_row_counts')

    def __init__(self, profile, latent):
        self.profile = profile
        self.latent = latent
        self.latent_id = simulator.latent_id(latent)
        self.rows = profile['rows']
        self.parts = len(profile['parts'])
        faults = {item['part']: item for item in profile['fault_rows']}
        affected = simulator.affected_parts(latent, self.parts)
        self.override = {(part, faults[part]['row_id']): Decimal(faults[part]['w'])
                         for part in sorted(affected)}
        self.affected = frozenset(part for part, _ in self.override)
        self.report_strings = tuple(profile['report_part_totals'])
        self.report_totals = tuple(Decimal(text) for text in self.report_strings)
        totals = []
        for part in range(self.parts):
            total = self.report_totals[part]
            if part in self.affected:
                total = total - Decimal(faults[part]['v']) + Decimal(faults[part]['w'])
            totals.append(total)
        self.source_totals = tuple(totals)
        self.source_strings = tuple(str(total) for total in totals)
        visible = latent[0] == 'local' and latent[2]
        self.engine_row_counts = tuple(
            part['rows'] + (1 if visible and part['part'] == latent[1] else 0)
            for part in profile['parts'])

    def page(self, part, offset, limit):
        """Raw rows of one part with the override applied; derived in O(limit), never copied."""
        return [[row[0], row[1], value_string(self.override.get((part, row[0]), row[2]))]
                for row in self.rows[part][offset:offset + limit]]


def materialize(profile, latent):
    return Materialized(profile, latent)


def _single_actions(parts):
    out = [('consistency_check', {}), ('full_recompute', {})]
    out.extend(('spot_check', {'part': part}) for part in range(parts))
    out.extend(('read_rows', {'part': part, 'offset': 0, 'limit': 10}) for part in range(parts))
    out.extend([('stop', {}), ('escalate', {})])
    return out


def _action_key(action, params):
    return action if 'part' not in params else f'{action}:{params["part"]}'


def _static_signature(observation):
    return compact({key: observation[key] for key in
                    ('task', 'pricing', 'reliability', 'public_reliability_model')})


def validate(profile, model='rev1'):
    """Freeze-time validation: realizability, env/simulator agreement, patch rule, static invariance."""
    parts = len(profile['parts'])
    if parts < MIN_PARTS or len(profile['fault_rows']) != parts:
        raise ValueError('unrealizable profile: ' + profile['profile_id'])
    actions, steps, static, checked = _single_actions(parts), 0, None, 0
    started = time.perf_counter()
    for latent in simulator.latents(model, parts):
        mat = materialize(profile, latent)
        if len(mat.override) > parts:
            raise ValueError('override map larger than the part count')
        if mat.rows is not profile['rows']:
            raise ValueError('materialization copied the shared rows')
        for action, params in actions:
            env = VeriCostEnv(mat, counts=VALIDATION_COUNTS, regime=costs.PRIMARY)
            signature = _static_signature(env.observation())
            if static is None:
                static = signature
            elif signature != static:
                raise ValueError('static observation depends on the latent: ' + profile['profile_id'])
            env.step(action, params)
            steps += 1
            env.close()
        _check_patch_rule(profile, mat, parts)
        checked += 1
    seconds = time.perf_counter() - started
    return {'profile_id': profile['profile_id'], 'latents_checked': checked, 'env_steps': steps,
            'static_observation_sha256': hashlib.sha256(static.encode()).hexdigest(),
            'seconds': seconds}


def _check_patch_rule(profile, mat, parts):
    """A published patch is correct exactly when it covers the affected set."""
    covers = {frozenset({0}), frozenset(range(min(parts, 4))), frozenset(sorted(mat.affected)[:4])}
    for cover in sorted(covers, key=lambda item: (len(item), sorted(item))):
        env = VeriCostEnv(mat, counts=VALIDATION_COUNTS, regime=costs.PRIMARY)
        for part in sorted(cover):
            env.step('spot_check', {'part': part})
        if env.mismatch:
            env.step('publish', {'candidate_id': 'patch', 'request_id': 'vc-validate',
                                 'expected_revision': 1, 'write_mode': 'replace'})
            if env.effects[-1]['correct'] is not simulator.patch_covers(mat.latent, cover, parts):
                raise ValueError('patch rule disagrees with the simulator: ' + profile['profile_id'])
        env.close()


def _profiles():
    """Every development profile with its reference size and per-regime costs, not yet validated."""
    synthetic = synthetic_profiles()
    seen, excluded = seen_profiles()
    profiles = synthetic + seen
    references = {'synthetic': costs.b_ref(synthetic, 'synthetic'),
                  'seen': costs.b_ref(seen, 'seen_development')}
    for profile in profiles:
        profile['b_ref'] = (references['synthetic'] if profile['kind'] == 'synthetic'
                            else references['seen'])
        profile['costs'] = {item['regime_id']: costs.operation_costs(profile, item['regime_id'])
                            for item in costs.REGIMES}
    return profiles, references, excluded


def _build():
    """The validated development profiles and the index that describes them."""
    profiles, references, excluded = _profiles()
    validations = [validate(profile) for profile in profiles]
    steps = sum(item['env_steps'] for item in validations)  # int-sum
    seconds = fsum_(item['seconds'] for item in validations)
    clusters = {}
    for profile in profiles:
        clusters.setdefault(profile['cluster_id'], []).append(profile['profile_id'])
    index_data = {
        'schema': SCHEMA, 'version': VERSION, 'split': 'development', 'seen_cluster': True,
        'independent_test': False, 'generalization_claim': 'none', 'b_ref': references,
        'b_ref_rule': {'synthetic': '5000 x median bytes per row (design 1.1)',
                       'seen': 'median bytes(profile) over kept seen profiles (documented deviation '
                               'R8: every seen slice has exactly eight rows)'},
        'clusters': [{'cluster_id': cluster,
                      'kind': 'synthetic' if cluster == 'synthetic' else 'seen_development',
                      'profile_ids': sorted(ids)} for cluster, ids in sorted(clusters.items())],
        'profiles': [{key: value for key, value in profile.items() if key != 'rows'}
                     for profile in profiles],
        'excluded': excluded,
        'validation': {'latents_checked': sum(item['latents_checked'] for item in validations),  # int-sum
                       'env_steps': steps, 'c2_status': 'pass',
                       'c2_scope': 'freeze_time_information_equivalence',
                       # Measured throughput is informational and is excluded from --check.
                       'env_steps_per_second': steps / seconds if seconds else 0.0},
        'seeds': SEEDS,
    }
    return profiles, index_data


def build():
    return _build()[1]


def load():
    """The committed index; its profiles carry no rows, so callers rebuild them with build_profiles."""
    return json.loads(INDEX.read_text(encoding='utf-8'))


def build_profiles(data=None):
    """Rebuild the live profile objects (with rows) that match a committed index."""
    data = data or load()
    profiles, _, _ = _profiles()
    keep = {item['profile_id'] for item in data['profiles']}
    return [profile for profile in profiles if profile['profile_id'] in keep]


def index(path=INDEX):
    data = build()
    write_json_once(path, data)
    return data


def _comparable(data):
    data = canon(data)
    data['validation'] = {key: value for key, value in data['validation'].items()
                          if key != 'env_steps_per_second'}
    return compact(data)


def check(path=INDEX):
    """Rebuild every derived table and compare with the committed index (timing excluded)."""
    stored = json.loads(Path(path).read_text(encoding='utf-8'))
    if _comparable(stored) != _comparable(build()):
        raise ValueError('instance index does not match a rebuild from source')
    return {'status': 'ok', 'profiles': len(stored['profiles']), 'excluded': len(stored['excluded'])}


def _utility_table(regime_id):
    outcomes = {'safe_complete': {'safe_complete': True},
                'false_completion': {'false_completion': True},
                'forbidden_effect': {'forbidden_effect': True},
                'escalate': {}, 'response_failure': {}}
    return {name: costs.utility(flags, 0.0, regime_id) for name, flags in outcomes.items()}


def _semantics(profile):
    """observe() and the single-action transcript hashes for every rev-1 latent."""
    parts = len(profile['parts'])
    observed, hashes = {}, {}
    for latent in simulator.latents('rev1', parts):
        mat = materialize(profile, latent)
        key = simulator.latent_id(latent)
        observed[key], hashes[key] = {}, {}
        for action, params in _single_actions(parts):
            name = _action_key(action, params)
            probe = (action,) if 'part' not in params else (action, params['part'])
            observed[key][name] = list(simulator.observe(profile, latent, probe))
            env = VeriCostEnv(mat, counts=VALIDATION_COUNTS, regime=costs.PRIMARY)
            env.step(action, params)
            hashes[key][name] = hashlib.sha256(transcript(env).encode()).hexdigest()
            env.close()
    return observed, hashes


def golden():
    """The golden semantics fixture: costs, utilities, episode draws, observations, transcripts."""
    profiles, data = _build()
    fixture = {'schema': GOLDEN_SCHEMA, 'version': VERSION, 'b_ref': data['b_ref'],
               'costs': {profile['profile_id']: profile['costs'] for profile in profiles},
               'utility': {item['regime_id']: _utility_table(item['regime_id'])
                           for item in costs.REGIMES},
               'episodes': {}, 'training_draws': [], 'observe': {}, 'transcript_sha256': {}}
    for profile in profiles:
        pid = profile['profile_id']
        for kind in simulator.TYPES:
            draw = simulator.episode(profile, kind)
            fixture['episodes'][f'{pid}|{kind}'] = {'model': {
                'rev1': {'history_classes': draw['history_classes'], 'counts': draw['counts'],
                         'latent_class': draw['latent_class'], 'part': draw['part'],
                         'cc_visible': draw['cc_visible'], 'latent_id': draw['latent']['rev1']},
                'd1': {'mask': draw['mask'], 'latent_id': draw['latent']['d1']}}}
        fixture['observe'][pid], fixture['transcript_sha256'][pid] = _semantics(profile)
    rng = random.Random(simulator.TRAINING_SEED)
    ordered = sorted(profiles, key=lambda profile: profile['profile_id'])
    for _ in range(GOLDEN_DRAWS):
        fixture['training_draws'].append(simulator.sample_episode(rng, ordered))
    return fixture


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--index', action='store_true')
    parser.add_argument('--golden', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--path', type=Path)
    args = parser.parse_args()
    if args.index:
        written = index(args.path or INDEX)
        print(compact({'profiles': len(written['profiles']), 'excluded': len(written['excluded']),
                       'clusters': len(written['clusters']), 'b_ref': written['b_ref'],
                       'env_steps': written['validation']['env_steps'],
                       'env_steps_per_second': round(written['validation']['env_steps_per_second'], 1)}))
    if args.golden:
        produced = golden()
        write_json_once(args.path or GOLDEN, produced)
        print(compact({'golden_fixture_sha256': sha_json(produced),
                       'profiles': len(produced['observe'])}))
    if args.check:
        try:
            print(compact(check(args.path or INDEX)))
        except ValueError as error:
            print(str(error), file=sys.stderr)
            raise SystemExit(1)
