import copy
import unittest
from research.termination_case_analysis import analyze, numeric


class TerminationCaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = analyze()['findings']

    def test_public_window_arithmetic_excludes_exact_right_endpoint(self):
        for r in self.results:
            self.assertEqual(r['independent_arithmetic']['selected_ids'], ['1','2','3','4','5'])
            self.assertEqual(r['independent_arithmetic']['total'], '117.89')
            self.assertTrue(r['current_numeric_matches'])

    def test_shifted_boundary_changes_computation_not_a_cached_reference(self):
        obs = copy.deepcopy(self.results[0]['public_observation'])
        obs['contract']['end'] = '2015-02-02T15:25:00+00:00'
        r = numeric(obs)
        self.assertIn('6', r['selected_ids'])
        self.assertNotEqual(r['total'], '117.89')

    def test_missing_timezone_fails_instead_of_silently_comparing(self):
        obs = copy.deepcopy(self.results[0]['public_observation'])
        obs['contract']['start'] = '2015-02-02T14:30:00'
        with self.assertRaises(ValueError):
            numeric(obs)

    def test_historical_single_step_has_no_fabricated_model_motive(self):
        for r in self.results:
            self.assertTrue(r['causal_explanation'].startswith('unknown'))
            if r['source'].startswith('stop'):
                self.assertIsNone(r['experiment_horizon_remaining'])
                self.assertEqual(r['responsibility']['status'],
                                 'no_explicit_responsibility_contract_in_request')


if __name__ == '__main__':
    unittest.main()
