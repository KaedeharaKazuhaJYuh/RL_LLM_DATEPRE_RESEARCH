"""Append the user's explicit reviewer-consent relay; never rewrite the old review."""
import copy
import json
from . import VERSION
from ..review515 import intake
from ..review505.design import digest

REPO = intake.REPO
FOLDER = REPO / 'faultda_bench/reports/review520'
CONSENT = FOLDER / 'consent_relay_2026_10_19.json'
REGISTRATION = FOLDER / 'final_referent_registration.json'
QUESTION = '请转请张雨田确认：是否愿意将 2026-10-18 已给出的 12 对指代意见正式登记为最终裁决？无需重审或重填，原有异议全部保留。'
ANSWER = '审阅者已明确同意正式登记'


def consent_record():
    return {'date': '2026-10-19', 'reviewer': '张雨田',
            'record_kind': 'project_transcription_of_direct_user_consent_relay',
            'question': QUESTION, 'user_answer': ANSWER,
            'question_tool_call_id': 'call_80d578d9b641432989021b18b50a29f0',
            'basis': 'The human user explicitly relayed that the original reviewer consented to formal registration. This is not a newly signed reviewer file or identity authentication.',
            'source_review_sha256': intake.SOURCE_SHA256,
            'original_review_file_rewritten': False,
            'reviewer_identity_authenticated': False,
            'new_design_accepted': False, 'scientific_gate': 'HOLD',
            'approved_transport_requests': 0}


def expected():
    old = intake.expected()
    consent = json.loads(CONSENT.read_text(encoding='utf-8'))
    if consent != consent_record(): raise ValueError('reviewer-consent relay changed')
    return {'version': VERSION, 'reviewer': '张雨田', 'registered_date': '2026-10-19',
            'status': 'registered_final_referent_adjudication_only',
            'source_review_sha256': intake.SOURCE_SHA256,
            'source_intake_sha256': intake.sha(intake.RECEIPT),
            'packet_sha256': old['packet_sha256'], 'consent_relay_sha256': intake.sha(CONSENT),
            'case_opinions': copy.deepcopy(old['referent_opinions']),
            'registered_pairs': 12,
            'retained_objections': [
                'contextual admits both lookup and last-publish readings; explicit specifies lookup',
                'scripted_current actor scope in old prompts is not independently unambiguous',
                'origin scripted is clear but does not imply true model-authored history',
                'wording-collision explanation remains an opinion, not isolated causal evidence'],
            'scope': 'Registration of the existing twelve opinions with objections, after user-relayed reviewer consent; no repeat review, replacement scores or new design acceptance.',
            'final_adjudication_registered': True, 'reviewer_identity_authenticated': False,
            'source_signature_received': False, 'old_scores_replaced': False,
            'old_37_group_scope_expanded': False,
            'design_opinions': copy.deepcopy(old['design_opinions']),
            'new_0520_interface_independently_reviewed': False,
            'scientific_gate': 'HOLD', 'approved_transport_requests': 0}


def verify(record=None):
    actual = json.loads(REGISTRATION.read_text(encoding='utf-8')) if record is None else record
    if actual != expected(): raise ValueError('final referent registration scope/binding changed')
    if digest(actual['case_opinions']) != digest(intake.expected()['referent_opinions']):
        raise ValueError('original opinions or objections changed')
    return {'status': actual['status'], 'registered_pairs': 12,
            'final_adjudication_registered': True, 'reviewer_identity_authenticated': False,
            'source_signature_received': False, 'old_scores_replaced': False,
            'new_interface_independent_review': 'pending',
            'scientific_gate': 'HOLD', 'approved_transport_requests': 0}
