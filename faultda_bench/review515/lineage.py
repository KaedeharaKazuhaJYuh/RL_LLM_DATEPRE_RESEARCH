"""Local historical-source quarantine; no promotion to an unseen test split."""
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

from ..semantic.tasks import REPO

VERSION = '0.5.15-dev'
REGISTRY = 'faultda_bench/protocols/historical_sources.json'
HOLDOUT = 'tasks/v5/beta_holdout_v1/manifest.json'
CSV = 'tasks/v5/beta_holdout_v1/data/occupancy.csv'
SEMANTIC = 'faultda_bench/protocols/semantic_tasks_v1.json'
COHERENT = 'faultda_bench/reports/coherent_v38_offline.json'
PACKET = 'faultda_bench/reports/review510/review_packet.json'
INPUTS = (REGISTRY, HOLDOUT, CSV, SEMANTIC, COHERENT, PACKET,
          'tasks/v5/beta_holdout_v1/tasks.json', 'reports/v5_beta1_paired_audit.json',
          'reports/V5_BETA_1_PREREGISTRATION.md', 'reports/FAULTDA_BENCH_RESEARCH_PROTOCOL_V1.md',
          'faultda_bench/semantic/tasks.py', 'faultda_bench/coherent395/suite.py')


def _read(repo, relative):
    return json.loads((Path(repo) / relative).read_text(encoding='utf-8'))


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _identity(key, value):
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    if key == 'source_id':
        return 'source_id', value.casefold()
    if key in ('sha256', 'source_sha256', 'content_sha256', 'archive_sha256'):
        if re.fullmatch('[0-9a-fA-F]{64}', value):
            # Archive and derivative identities share a namespace deliberately:
            # renaming their metadata field must not wash out an exact match.
            return 'sha256', value.lower()
        return None
    if key == 'doi':
        value = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', value,
                       flags=re.IGNORECASE)
        return 'doi', value.casefold().rstrip('/')
    if key in ('url', 'upstream_url'):
        url = urlsplit(value)
        if url.scheme.lower() in ('http', 'https') and url.hostname:
            return 'url', (url.hostname.casefold() + unquote(url.path).rstrip('/') +
                           ('?' + url.query if url.query else ''))
    return None


def _nodes(candidate):
    """Walk declared ancestry, failing closed on malformed or cyclic metadata."""
    if not isinstance(candidate, dict):
        raise ValueError('candidate must be an identity object')
    stack = [('candidate', candidate, frozenset())]
    while stack:
        location, node, ancestors_seen = stack.pop()
        if not isinstance(node, dict) or id(node) in ancestors_seen:
            raise ValueError('ancestors must be acyclic identity objects')
        yield location, node
        ancestors = node.get('ancestors', [])
        if not isinstance(ancestors, list):
            raise ValueError('ancestors must be a list')
        for i in reversed(range(len(ancestors))):
            stack.append((location + '.ancestors[' + str(i) + ']', ancestors[i],
                          ancestors_seen | {id(node)}))


def seen_sources(repo=REPO):
    """Expose the existing whole V1-V5 registry, not just the eight-row slice."""
    registry = _read(repo, REGISTRY)
    return registry['sources']


def assess_candidate(candidate, *, seen=None):
    """Reject exact known lineage; an unmatched declaration still needs review.

    No filesystem path is treated as evidence of independence. This local exact-
    identity screen cannot detect omitted/false ancestry or all dataset aliases.
    """
    seen = seen_sources() if seen is None else seen
    index = {}
    for source in seen:
        for node in [source] + source.get('datasets', []) + source.get('source_metadata', []):
            for key, value in node.items():
                identity = _identity(key, value)
                if identity:
                    index.setdefault(identity, set()).add(source['source_id'])
    matches = []
    known_fields = 0
    issues = []
    for location, node in _nodes(candidate):
        node_fields = 0
        for key, value in node.items():
            if key in ('ancestors', 'path', 'source_path', 'uri'):
                continue
            identity = _identity(key, value)
            if identity:
                known_fields += 1
                node_fields += 1
                for source_id in sorted(index.get(identity, ())):
                    matches.append({'location': location, 'field': key,
                                    'matched_identity': list(identity), 'seen_source_id': source_id})
            elif key in ('source_id', 'sha256', 'source_sha256', 'content_sha256',
                         'archive_sha256', 'doi', 'url', 'upstream_url'):
                issues.append(location + '.' + key + ': invalid identity')
        if not node_fields:
            issues.append(location + ': no recognized source identity')
    return {'version': VERSION,
            'decision': 'REJECT_SEEN_LINEAGE' if matches else 'PENDING_LINEAGE_REVIEW',
            'eligible_as_unseen_test': False, 'matches': matches, 'issues': issues,
            'recognized_identity_fields': known_fields, 'path_is_independence_evidence': False,
            'reason': 'Known source, content, archive or ancestor already seen.' if matches else
                      'No exact registry match is not proof of independence; provenance and independent review remain required.',
            'scientific_gate': 'HOLD', 'approved_transport_requests': 0}


def _instant(text):
    instant = datetime.fromisoformat(text)
    if instant.tzinfo is None:
        raise ValueError('derived timestamps must retain a timezone')
    return instant.astimezone(timezone.utc).isoformat()


def audit(repo=REPO):
    """Bind observed development reuse without rewriting historical split labels."""
    repo = Path(repo)
    manifest = _read(repo, HOLDOUT)
    registry = _read(repo, REGISTRY)
    semantic = _read(repo, SEMANTIC)
    coherent = _read(repo, COHERENT)
    packet = _read(repo, PACKET)
    source = manifest['sources']['occupancy']
    if _hash(repo / CSV) != source['sha256']:
        raise ValueError('occupancy bytes do not match the historical manifest')
    with (repo / CSV).open(encoding='utf-8', newline='') as stream:
        raw = list(csv.DictReader(stream))
    task = next(t for t in semantic['tasks'] if t['id'] == 'window-01')
    if (task['source_path'], task['source_sha256'], task['selection'], task['split']) != (
            CSV, source['sha256'], [0, 8], 'historical_development'):
        raise ValueError('semantic development source binding changed')
    expected = {str(i): (row['Temperature'], _instant(row['date'] + '+00:00'))
                for i, row in enumerate(raw[:8])}

    def check_rows(rows):
        actual = {r['id']: (r['value'], _instant(r['time'])) for r in rows}
        if len(rows) != 8 or actual != expected:
            raise ValueError('derived eight-row values/timestamps differ from source')

    check_rows(task['versions']['v1'])
    for derived in coherent['tasks'].values():
        if (derived['source_id'], derived['source_sha256'], derived['selection']) != (
                source['source_id'], source['sha256'], [0, 8]):
            raise ValueError('coherent task source binding changed')
        check_rows(derived['versions']['v1'])
    prompt_pairs = packet['prompt_review']
    for pair in prompt_pairs:
        for variant in pair['variants']:
            message = next(m['content'] for m in variant['messages'] if m['role'] == 'user')
            obs = json.loads(message)['observation']
            inputs = next(h['response'] for h in obs['history'] if h['action'] == 'inputs')
            check_rows(inputs['versions']['v1'])
    historical = next(s for s in registry['sources'] if s['source_id'] == source['source_id'])
    if historical['faultda_split'] != 'seen_development':
        raise ValueError('historical registry no longer quarantines this source')
    evaluation = _read(repo, 'reports/v5_beta1_paired_audit.json')
    beta_tasks = _read(repo, 'tasks/v5/beta_holdout_v1/tasks.json')
    traced = [{'source_row_index': i, 'original_source_id': row['id'],
               'task_row_id': str(i), 'original_date': row['date'],
               'utc_time': expected[str(i)][1], 'Temperature': row['Temperature']}
              for i, row in enumerate(raw[:8])]
    return {'version': VERSION, 'status': 'verified_local_lineage',
            'input_sha256': {name: _hash(repo / name) for name in INPUTS},
            'source_lineage': {'source_id': source['source_id'], 'source_sha256': source['sha256'],
                               'original_manifest_external_test': manifest['external_test'],
                               'original_manifest_one_time_evaluation': manifest['one_time_evaluation'],
                               'frozen_manifest_rewritten': False,
                               'existing_registry_split': historical['faultda_split'],
                               'current_qualification': 'seen_development_only',
                               'future_unseen_external_test_eligible': False,
                               'final_test_sources': registry['final_test_sources']},
            'eight_row_trace': traced,
            'observed_reuse': {'semantic_task': task['id'], 'source_slice': [0, 8],
                              'coherent_task_views': len(coherent['tasks']),
                              'prompt_pairs': len(prompt_pairs),
                              'distinct_source_slices': 1, 'independent_task_clusters': 1,
                              'time_renderings_or_window_endpoints_add_independence': False},
            'historical_usage': {'consumed_evaluation_record_present': bool(evaluation['seeds']),
                                 'paired_audit_seeds': len(evaluation['seeds']),
                                 'historical_beta_tasks': len(beta_tasks),
                                 'historical_beta_sources': sorted({t['source_id'] for t in beta_tasks}),
                                 'later_development_reuse_confirmed': True,
                                 'earlier_training_leakage_proved': False,
                                 'chronology_independently_attested': False},
            'limits': ['Local files establish current traceability, not independent historical attestation.',
                       'Later development reuse does not prove leakage during the original evaluation.',
                       'The inherited external_test label describes the historical protocol, not future eligibility.',
                       'Exact identity screening cannot prove absence of omitted ancestry or aliases.'],
            'new_provider_requests': 0, 'scientific_gate': 'HOLD'}
