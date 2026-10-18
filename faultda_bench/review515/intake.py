"""Accept the received Markdown as opinions, not a final adjudication."""
import json
from ..review505.intake import REPO, sha
from ..review505.design import digest
from ..review510 import review
from . import VERSION

FOLDER = REPO / 'faultda_bench/reports/review515'
SOURCE = FOLDER / 'HUMAN_REVIEW_2026_10_18_ZHANG.md'
RECEIPT = FOLDER / 'intake.json'
SOURCE_SHA256 = '08f81c87913a9931694f00421ea7408ca3690b46c49b95dc117001fdd5e83703'
REVIEWED = [
    {'commit': '97b8a218babc10be8b2bbd9dbb34080a671431b9',
     'archive': 'FaultDA_0.5.10-dev_Review_2026-10-18_97b8a21.zip',
     'archive_sha256': '355925b5744588c6fc0f434ec3b6a9219e21dfee244e2e3cb8b1b1aef5e63b3c'},
    {'commit': '727fb42ecb50ccf2e92e89fa08c1ae93849c1251',
     'archive': 'FaultDA_Design_Witness_Supplement_2026-10-18_727fb42.zip',
     'archive_sha256': 'a72f244cf9199a539614c1d2c761c38e10a1c07f328dd583a42da334ce51a37e'},
]


def expected():
    if sha(SOURCE) != SOURCE_SHA256:
        raise ValueError('received human Markdown changed')
    packet = json.loads(review.PACKET.read_text(encoding='utf-8'))
    return {
        'version': VERSION, 'reviewer': '张雨田', 'date': '2026-10-18',
        'source_sha256': SOURCE_SHA256, 'source_bytes': 13381,
        'packet_sha256': digest(packet), 'reviewed_artifacts': REVIEWED,
        'basis': 'User supplied this named human-review Markdown; repository intake is a transcription, not a reviewer-filled JSON or authenticated signature.',
        'human_review_opinions_received': True, 'reviewer_identity_authenticated': False,
        'technical_verdict_received': 'pass_with_scientific_revisions',
        'referent_opinions': [
            {'case_id': c['case_id'], 'contextual': 'both_plausible', 'explicit': 'lookup',
             'scripted_origin_clear': True,
             'actor_scope_clear': '|historical|' in c['case_id']}
            for c in packet['prompt_review']],
        'design_opinions': {k: 'revise' for k in review.DESIGN_QUESTIONS},
        'final_referent_adjudication': 'pending_explicitly_not_final',
        'final_adjudication_registered': False,
        'scope_reason': 'The source final paragraph explicitly says this record is not registered as final independent adjudication. Section 3 opinions are retained without overriding that limit.',
        'reviewer_interpretation': 'Wording collision may explain responsibility mismatches; this causal attribution is an opinion, not an experimentally isolated mechanism.',
        'old_scores_replaced': False, 'old_37_group_scope_expanded': False,
        'new_0515_changes_independently_reviewed': False,
        'scientific_gate': 'HOLD', 'approved_transport_requests': 0,
    }


def verify(receipt=None):
    actual = json.loads(RECEIPT.read_text(encoding='utf-8')) if receipt is None else receipt
    if actual != expected():
        raise ValueError('human-review intake scope or source binding changed')
    if SOURCE.stat().st_size != actual['source_bytes']:
        raise ValueError('human-review source length')
    return {'status': 'received_scoped_opinions', 'referent_pair_opinions': 12,
            'design_opinions_received': 4, 'design_verdicts': 'revise',
            'final_referent_adjudication': 'pending_explicitly_not_final',
            'reviewer_identity_authenticated': False, 'scientific_gate': 'HOLD',
            'approved_transport_requests': 0}


def factual_crosscheck():
    """Recount frozen fact fields; do not infer why the model answered this way."""
    path = REPO / 'faultda_bench/reports/coherent_v38_accounting.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    rows = data['pairs']; fields = ('receipt_request_id', 'receipt_committed', 'receipt_revision')
    explicit_facts = sum(all(r['arms']['explicit']['grade']['field_correct'][f] for f in fields) for r in rows)
    current = [r for r in rows if r['represented_role'] == 'scripted_current']
    role_errors = sum(not r['arms']['explicit']['grade']['field_correct']['receipt_responsibility'] for r in current)
    bad_events = [r['row_id'] for r in current
                  if r['arms']['explicit']['reported_facts']['receipt_event_id'] == 'history:5']
    if (len(rows), explicit_facts, len(current), role_errors, len(bad_events)) != (12, 12, 6, 6, 2):
        raise ValueError('review fact-field crosscheck changed')
    return {'source_sha256': sha(path), 'explicit_core_fact_fields_correct': '12/12',
            'scripted_current_role_mismatches': '6/6', 'invalid_stage_event_references': bad_events,
            'scope': 'Retrospective field decomposition only; no new score, causal attribution or model tool execution.'}
