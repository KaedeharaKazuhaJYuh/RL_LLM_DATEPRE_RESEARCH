"""Register the supplied human Markdown, without fabricating JSON signatures."""
import hashlib
import json
from pathlib import Path
from ..validity500.review import REGISTRY

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO/'faultda_bench/reports/review505/HUMAN_REVIEW_2026_10_16_ZHANG.md'
RECEIPT = SOURCE.with_name('intake.json')
REVIEWED_COMMIT = 'e29d39c1dc9ea26de3c3c3428b4eee0a318d98ec'
REVIEWED_ZIP_SHA256 = '08336b3097964ae434d32835fb3b28641db905fbe2c1bf5ef3980498faf3c6d8'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(receipt=None):
    r = json.loads(RECEIPT.read_text(encoding='utf-8')) if receipt is None else receipt
    registry = json.loads(REGISTRY.read_text(encoding='utf-8'))
    expected = {
        'reviewer': '张雨田', 'reviewed_commit': REVIEWED_COMMIT,
        'reviewed_bundle_sha256': REVIEWED_ZIP_SHA256,
        'source_sha256': sha(SOURCE), 'registry_sha256': sha(REGISTRY),
        'case_bindings': registry['cases'], 'technical_groups_passed': 37,
        'basis': 'Supplied Markdown global 37/37 verdict plus direct user human-review assertion; not a reviewer-filled per-case JSON submission.',
        'human_review_registered': True, 'reviewer_identity_authenticated': False,
        'reviewed_commit_resolved_at_intake': True,
        'reviewer_json_attachments_received': False,
        'independent_final_referent_adjudication': 'not_performed',
        'scientific_gate': 'HOLD', 'new_design_independently_reviewed': False,
        'approved_transport_requests': 0,
        'excluded_scopes': ['provider_authenticity', 'inherited_v5', 'older_reports_full_rereview',
                            '0.3.80_live_independent_replay', 'final_referent_adjudication', '0.5.05_new_work'],
        'nonblocking_changes': ['bundle_runtime_dependencies_and_entrypoint', 'test_count_scope'],
    }
    if r != expected:
        raise ValueError('Review receipt differs from source-bound, scoped human intake')
    if len(r['case_bindings']) != 37:
        raise ValueError('Review scope must contain exactly 37 registry groups')
    return {'status': 'accepted_technical_37_groups', 'groups': 37,
            'human_review_registered': True, 'reviewer_identity_authenticated': False,
            'final_referent_adjudication': 'not_performed', 'scientific_gate': 'HOLD',
            'new_design_independently_reviewed': False}
