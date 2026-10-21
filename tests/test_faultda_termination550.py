import copy
import json
import unittest

from faultda_bench.termination550 import design as d


class TerminalDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads(d.SOURCE.read_text(encoding='utf-8'))['rows']

    def test_packet_is_public_only_and_source_unchanged(self):
        obs = self.rows[0]['public_observation']
        before = copy.deepcopy(obs)
        p = d.packet(obs, 'raw')
        self.assertEqual(obs, before)
        self.assertEqual(set(p['public']['observation']['tools']), {'stop', 'escalate'})
        self.assertEqual(p['public']['experiment_action_horizon_remaining'], 1)
        self.assertEqual(p['public']['observation']['remaining'],
                         {'checks': 0, 'mutations': 0, 'decisions': 1})
        p['public']['observation']['history'][0]['action'] = 'changed'
        self.assertEqual(obs, before)

    def test_labels_and_private_truth_are_not_accepted_as_observations(self):
        for field in ('private_truth', 'expected_receipt_facts', 'mode', 'numeric_reference'):
            obs = copy.deepcopy(self.rows[0]['public_observation'])
            obs[field] = self.rows[0].get(field)
            with self.assertRaises(ValueError):
                d.packet(obs, 'raw')

    def test_helper_recomputed_not_arbitrary_equal_declaration(self):
        p = d.packet(self.rows[0]['public_observation'], 'shared_numeric')
        p['public']['numeric_helper']['total'] = '0'
        with self.assertRaisesRegex(ValueError, 'helper incorrect'):
            d.validate(p)

    def test_extra_context_and_hidden_horizon_rejected(self):
        base = d.packet(self.rows[0]['public_observation'], 'raw')
        for field, value in [('extra_model_context', 'answer is stop'),
                             ('experiment_action_horizon_remaining', True)]:
            p = copy.deepcopy(base)
            p['public'][field] = value
            with self.assertRaises(ValueError):
                d.validate(p)

    def test_no_remaining_decision_is_not_silently_replenished(self):
        obs = copy.deepcopy(self.rows[0]['public_observation'])
        obs['remaining']['decisions'] = 0
        with self.assertRaises(ValueError):
            d.packet(obs, 'raw')

    def test_actual_safe_but_unsupported_stop_still_fails_evidence_metric(self):
        row = next(r for r in self.rows if r['private_truth']['actual_safe_stop_if_taken']
                   and not r['public_evidence']['evidence_supported_stop'])
        p = d.packet(row['public_observation'], 'raw')
        g = d.grade(p, {'action': 'stop', 'params': {}}, True)
        self.assertTrue(g['actual_safe_completion'])
        self.assertTrue(g['unsupported_stop'])
        self.assertFalse(g['supported_correct_termination'])

    def test_stage_or_invalid_schema_not_relabelled_as_terminal(self):
        p = d.packet(self.rows[0]['public_observation'], 'raw')
        for decision in ({'action': 'stage', 'params': {}},
                         {'action': 'stop', 'params': {}, 'explanation': 'ok'}):
            self.assertTrue(d.grade(p, decision, True)['invalid_response'])

    def test_program_controls_cover_the_same_panel_without_model_claim(self):
        q = d.qualify()
        self.assertEqual(q['legacy_strata'], {'supported_stop': 24,
                                           'confirmed_violation': 24, 'unresolved_risk': 24})
        for condition in d.CONDITIONS:
            summary = q['program_summary'][condition]
            self.assertEqual(summary['complete_public_rule']['supported_correct_termination'], 72)
            self.assertEqual(summary['always_stop']['unsupported_stop'], 48)
            self.assertEqual(summary['always_escalate']['unjustified_escalation_by_legacy_proof'], 24)
        self.assertEqual(q['new_model_executions'], 0)
        self.assertFalse(q['new_mechanism_demonstrated'])


if __name__ == '__main__':
    unittest.main()
