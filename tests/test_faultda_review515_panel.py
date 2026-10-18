"""Prospective-panel guardrails; fixtures are not human eligibility judgments."""
from copy import deepcopy
import unittest

from faultda_bench.review515 import panel


def reviewed_case(case_id='task-a', verdict='include'):
    return {
        'case_id': case_id,
        'cluster_id': 'synthetic-lineage',
        'design_verdict': verdict,
        'eligibility_evidence': {
            'basis': 'independent_task_review',
            'frozen_before_any_policy_outcome': True,
            'independent_of_compared_solver': True,
            'reference': 'SYNTHETIC TEST FIXTURE; not a human review',
        },
        'interface_unambiguous': True,
        'terminal_target': 'safe_completion',
        'design_defect': 'Synthetic prompt ambiguity fixed before all arms run',
    }


def completed_rows(case_ids=('task-a',), arms=('rule', 'model')):
    return [
        {'arm': arm, 'case_id': case_id,
         'execution_kind': 'model_tool_execution', 'terminal_action': 'stop'}
        for arm in arms for case_id in case_ids
    ]


class ProspectiveCommonPanelTests(unittest.TestCase):
    def test_solver_derived_or_post_outcome_eligibility_is_rejected(self):
        for field, value in (
            ('basis', 'reference_policy_prediction'),
            ('frozen_before_any_policy_outcome', False),
            ('independent_of_compared_solver', False),
            ('reference', ''),
        ):
            with self.subTest(field=field):
                case = reviewed_case()
                case['eligibility_evidence'][field] = value
                with self.assertRaises(ValueError):
                    panel.qualify([case])

    def test_exclusion_requires_the_same_prospective_evidence_as_inclusion(self):
        case = reviewed_case(verdict='exclude')
        case['eligibility_evidence']['frozen_before_any_policy_outcome'] = False
        with self.assertRaises(ValueError):
            panel.qualify([case])
        case = reviewed_case(verdict='exclude')
        case.pop('design_defect')
        with self.assertRaises(ValueError):
            panel.qualify([case])

    def test_ambiguous_or_unknown_target_cannot_be_admitted(self):
        for field, value in (('interface_unambiguous', False),
                             ('terminal_target', 'unknown')):
            with self.subTest(field=field):
                case = reviewed_case()
                case[field] = value
                with self.assertRaises(ValueError):
                    panel.qualify([case])

    def test_pending_eligibility_does_not_silently_disappear(self):
        unresolved = reviewed_case('task-b', 'pending')
        result = panel.qualify([reviewed_case(), unresolved])
        self.assertEqual(result['pending_case_ids'], ['task-b'])
        with self.assertRaises(ValueError):
            panel.check_outcome_coverage(result, ['rule', 'model'], completed_rows())

    def test_design_exclusion_applies_to_every_arm(self):
        result = panel.qualify([reviewed_case(), reviewed_case('task-b', 'exclude')])
        self.assertEqual(result['common_excluded_case_ids'], ['task-b'])
        coverage = panel.check_outcome_coverage(result, ['rule', 'model'], completed_rows())
        self.assertEqual(coverage['scheduled_per_arm'], {'rule': 1, 'model': 1})
        with self.assertRaises(ValueError):
            panel.check_outcome_coverage(
                result, ['rule', 'model'], completed_rows(('task-a', 'task-b')))

    def test_failure_censoring_role_and_referent_errors_stay_in_common_panel(self):
        cases = [reviewed_case('task-a'), reviewed_case('task-b')]
        result = panel.qualify(cases)
        rows = completed_rows(('task-a', 'task-b'))
        rows[0].update(terminal_action='invalid', invalid_output=True)
        rows[1].update(terminal_action=None, censored=True)
        rows[2].update(role_error=True, referent_error=True)
        rows[3].update(terminal_action='unknown', facts_correct=False)
        coverage = panel.check_outcome_coverage(result, ['rule', 'model'], rows)
        self.assertEqual(coverage['scheduled_per_arm'], {'rule': 2, 'model': 2})
        self.assertNotIn('accuracy', coverage)
        self.assertNotIn('correct_resolutions', coverage)
        # Removing one failure must fail coverage rather than improve a score.
        with self.assertRaises(ValueError):
            panel.check_outcome_coverage(result, ['rule', 'model'], rows[1:])

    def test_duplicate_outcome_cannot_replace_missing_case(self):
        result = panel.qualify([reviewed_case(), reviewed_case('task-b')])
        rows = completed_rows(('task-a', 'task-b'))
        rows[-1] = deepcopy(rows[-2])
        with self.assertRaises(ValueError):
            panel.check_outcome_coverage(result, ['rule', 'model'], rows)

    def test_no_eligible_case_produces_no_zero_denominator_score(self):
        result = panel.qualify([reviewed_case(verdict='exclude')])
        with self.assertRaisesRegex(ValueError, 'no eligible cases'):
            panel.check_outcome_coverage(result, ['rule', 'model'], [])

    def test_fact_answers_cannot_be_counted_as_executed_terminal_actions(self):
        result = panel.qualify([reviewed_case()])
        rows = completed_rows()
        for row in rows:
            row['execution_kind'] = 'fact_answer'
        with self.assertRaises(ValueError):
            panel.check_outcome_coverage(result, ['rule', 'model'], rows)

    def test_program_and_model_cohorts_are_not_pooled(self):
        result = panel.qualify([reviewed_case()])
        rows = completed_rows()
        rows[0]['execution_kind'] = 'scripted_program_not_model'
        with self.assertRaises(ValueError):
            panel.check_outcome_coverage(result, ['rule', 'model'], rows)

    def test_structural_success_does_not_authenticate_or_admit_experiments(self):
        result = panel.qualify([reviewed_case()])
        coverage = panel.check_outcome_coverage(result, ['rule', 'model'], completed_rows())
        self.assertEqual(result['status'], 'declarations_complete_not_authenticated')
        self.assertEqual(result['scientific_gate'], 'HOLD')
        for returned in (result, coverage):
            self.assertFalse(returned['scientific_admission_granted'])
            self.assertEqual(returned['approved_transport_requests'], 0)
        self.assertIsNone(coverage['confidence_interval'])
        self.assertEqual(coverage['declared_lineage_cluster_count'], 1)
        self.assertFalse(coverage['cluster_independence_authenticated'])
        self.assertNotIn('independent_clusters', coverage)

    def test_later_caller_mutation_does_not_rewrite_admitted_case(self):
        case = reviewed_case()
        result = panel.qualify([case])
        case['terminal_target'] = 'unknown'
        case['eligibility_evidence']['basis'] = 'post_outcome_prediction'
        admitted = result['common_included_cases'][0]
        self.assertEqual(admitted['terminal_target'], 'safe_completion')
        self.assertEqual(admitted['eligibility_evidence']['basis'], 'independent_task_review')


if __name__ == '__main__':
    unittest.main()
