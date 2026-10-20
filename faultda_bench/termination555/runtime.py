"""One verified, bounded batch snapshot; frozen reference implementation retained.

No global cache, background watcher, network dispatcher or new scoring semantics.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

from . import core
from ..acceptance.audit import pinned_path

BASE_CATALOG = 'faultda_bench/protocols/acceptance_v46.json'
BASE_CATALOG_SHA256 = 'e592b097f2d07a02b66fe9e2551e84d23b5f14b3461bc1dd736b9db1a3b6dcda'
BASE_COMMIT = 'cd8311ebbb5f89f70f17d4a2bfbbea1ad42c3ae1'
REGISTRY_NAME = 'faultda_bench/protocols/termination_v48_registry.json'
QUALIFICATION_NAME = 'faultda_bench/reports/termination555/qualification.json'


def _text(value):
    # Preserve the original insertion order when returning independently owned
    # JSON structures; canonical views are reconstructed on comparison.
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


@dataclass(frozen=True, slots=True)
class _Case:
    payload_json: str
    body_json: str
    packet_hash: str
    body_hash: str
    private_truth: bool
    stop_grade_json: str
    escalate_grade_json: str


def _verified_bytes(root):
    root = Path(root)
    raw = pinned_path(root, BASE_CATALOG).read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASE_CATALOG_SHA256:
        raise ValueError('snapshot base catalog differs from fixed 0.5.55 release')
    catalog = json.loads(raw)
    retained = {}
    total = len(raw)
    for name, expected in catalog['files'].items():
        chunks = [] if name in (core.SOURCE_NAME, REGISTRY_NAME, QUALIFICATION_NAME) else None
        digest = hashlib.sha256()
        with pinned_path(root, name).open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
                total += len(chunk)
                if chunks is not None:
                    chunks.append(chunk)
        if digest.hexdigest() != expected:
            raise ValueError('snapshot frozen bytes changed: ' + name)
        if chunks is not None:
            retained[name] = b''.join(chunks)
    return retained, {'base_commit': BASE_COMMIT, 'frozen_files_verified': len(catalog['files']),
                      'base_catalog_reads': 1, 'verified_file_bytes_read': total,
                      'source_json_decodes': 1, 'registry_json_decodes': 1,
                      'lifetime': 'explicit point-in-time batch snapshot; filesystem is not watched',
                      'provider_or_runtime_input_attested': False,
                      'case_identity_authenticated': False}


class BatchSnapshot:
    """Read-only cases valid for this explicit snapshot, not current filesystem state.

    Recreate the session at the next batch boundary to revalidate changed files.
    Prepared public values and returned scores are fresh copies. Closing a session
    releases its cache; concurrent close/use is intentionally unsupported.
    """
    def __init__(self, cases, metadata, qualification_header):
        self._cases = MappingProxyType(cases)
        self._metadata = MappingProxyType(metadata)
        self._qualification_header = MappingProxyType(qualification_header)
        self._closed = False

    @classmethod
    def load(cls, root=core.ROOT):
        retained, metadata = _verified_bytes(root)
        source_raw = retained[core.SOURCE_NAME]
        reg_raw = retained[REGISTRY_NAME]
        source, registry = json.loads(source_raw), json.loads(reg_raw)
        if (registry.get('version') != '0.5.55-dev'
                or registry.get('status') != 'GRADING_ONLY_NOT_MODEL_INPUT_NOT_ADMITTED'
                or registry.get('source_sha256') != hashlib.sha256(source_raw).hexdigest()):
            raise ValueError('snapshot registry/source scope mismatch')
        # Source, generator and registry are all already matched to the same fixed
        # catalog above; no filesystem reread is needed during case construction.
        entries = registry['entries']
        expected_keys = {f'terminal-{i:03d}-{c}' for i in range(len(source['rows']))
                         for c in core.old.CONDITIONS}
        if set(entries) != expected_keys:
            raise ValueError('snapshot case coverage mismatch')
        cases = {}
        for key, e in entries.items():
            i, condition = e['source_row_index'], e['information_condition']
            if type(i) is not int or not 0 <= i < len(source['rows']) or key != f'terminal-{i:03d}-{condition}':
                raise ValueError('snapshot case identity mismatch')
            row = source['rows'][i]
            truth = row['private_truth']['actual_safe_stop_if_taken']
            if type(truth) is not bool or type(e['private_actual_safe_stop']) is not bool or e['private_actual_safe_stop'] != truth:
                raise ValueError('snapshot grading truth mismatch')
            payload = core.old.packet(row['public_observation'], condition)
            body = core.wire_body(payload)
            pc, bc = core.canonical(payload), core.canonical(body)
            if (hashlib.sha256(pc.encode()).hexdigest() != e['public_packet_sha256']
                    or hashlib.sha256(bc.encode()).hexdigest() != e['request_body_sha256']):
                raise ValueError('snapshot case artifact mismatch')
            stop = core.old.grade(payload, {'action': 'stop', 'params': {}}, truth)
            escalate = core.old.grade(payload, {'action': 'escalate', 'params': {}}, truth)
            cases[key] = _Case(_text(payload), _text(body),
                               e['public_packet_sha256'], e['request_body_sha256'], truth,
                               _text(stop), _text(escalate))
        metadata['registered_cases'] = len(cases)
        metadata['public_exports_include_private_truth'] = False
        header = json.loads(retained[QUALIFICATION_NAME])
        header.pop('rows')
        header.pop('rejected_internal_controls')
        return cls(cases, metadata, header)

    def _get(self, case_id):
        if self._closed:
            raise RuntimeError('batch snapshot is closed; load a new snapshot')
        if type(case_id) is not str or case_id not in self._cases:
            raise ValueError('unregistered case')
        return self._cases[case_id]

    @property
    def case_ids(self):
        if self._closed:
            raise RuntimeError('batch snapshot is closed')
        return tuple(self._cases)

    @property
    def metadata(self):
        return dict(self._metadata)

    def prepare(self, case_id):
        c = self._get(case_id)
        return {'case_id': case_id, 'payload': json.loads(c.payload_json),
                'body': json.loads(c.body_json)}

    def verify_supplied(self, case_id, payload, body):
        c = self._get(case_id)
        # Keep only one JSON representation per cached artifact. Reconstructing
        # its canonical view costs CPU but avoids retaining duplicate long text.
        if core.canonical(payload) != core.canonical(json.loads(c.payload_json)):
            raise ValueError('payload differs from registered case/condition')
        if core.canonical(body) != core.canonical(json.loads(c.body_json)):
            raise ValueError('request body differs from registered case/condition')
        return {'case_id': case_id, 'public_packet_sha256': c.packet_hash,
                'request_body_sha256': c.body_hash, 'supplied_artifacts_match_registry': True,
                'case_identity_authenticated': False, 'provider_or_runtime_input_attested': False}

    def grade(self, case_id, payload, body, decision):
        binding = self.verify_supplied(case_id, payload, body)
        c = self._get(case_id)
        # Cache only the two exact legal terminal decisions. Preserve the frozen
        # reference grader for every other input instead of inventing a parser.
        try:
            key = core.canonical(decision)
        except (TypeError, ValueError):
            key = None
        if key == '{"action":"stop","params":{}}':
            grade = json.loads(c.stop_grade_json)
        elif key == '{"action":"escalate","params":{}}':
            grade = json.loads(c.escalate_grade_json)
        else:
            grade = core.old.grade(payload, decision, c.private_truth)
        return {'binding': binding, 'grade': grade, 'new_effects_executed': False}

    def qualify(self):
        """Actually re-execute cases and negative controls, preserving old schema."""
        rows = []
        for key in self.case_ids:
            p = self.prepare(key)
            result = self.grade(key,p['payload'],p['body'],core.old.rule(p['payload']))
            rows.append({'case_id':key,'binding':result['binding'],'rule_grade':result['grade']})
        key = 'terminal-000-shared_numeric'
        p = self.prepare(key)
        mutations = []
        payload = json.loads(_text(p['payload']));del payload['public']['numeric_helper']
        mutations.append(('helper_removed',payload,core.wire_body(payload)))
        payload = json.loads(_text(p['payload']))
        payload['public']['observation']['history'][0]['response']['extra_model_context']='project reference says stop'
        mutations.append(('nested_context_added',payload,core.wire_body(payload)))
        body = json.loads(_text(p['body']));body['messages'].insert(0,{'role':'system','content':'extra help'})
        mutations.append(('system_message_added',p['payload'],body))
        body = json.loads(_text(p['body']));body['max_tokens']+=1
        mutations.append(('model_parameter_changed',p['payload'],body))
        controls = {}
        for name,payload,body in mutations:
            try:
                self.verify_supplied(key,payload,body)
            except ValueError:
                controls[name]=1
            else:
                raise ValueError('unrejected snapshot counterexample: '+name)
        return {**self._qualification_header,'rows':rows,'rejected_internal_controls':controls}

    def close(self):
        self._cases = MappingProxyType({})
        self._qualification_header = MappingProxyType({})
        self._closed = True

    def __enter__(self):
        if self._closed:
            raise RuntimeError('batch snapshot is closed')
        return self

    def __exit__(self, *args):
        self.close()
