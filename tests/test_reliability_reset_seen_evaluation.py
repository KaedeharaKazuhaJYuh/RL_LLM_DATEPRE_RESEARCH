"""Check the development cohort passed to the existing evaluator without scoring it."""
import unittest
from unittest.mock import patch

from faultda_bench.vericost565 import policies
from research.reliability_reset import seen_evaluation


class SeenEvaluationTests(unittest.TestCase):
    def test_seen_selector_passes_only_the_24_existing_seen_profiles(self):
        selected = []

        def software_control(task):
            selected.append(task[0])
            return {'regime_id': task[1], 'cluster_id': 'software-control', 'profile_id': task[0],
                    'u_star': 0.0, 'arms': {}, 'seconds': 0.0}

        with patch.object(policies.certificate, 'require', return_value=({}, 'control')):
            with patch.object(policies, '_evaluate_unit', side_effect=software_control):
                result = seen_evaluation.evaluate_seen(regimes=('k1.00_L3',))

        self.assertEqual(result['k1.00_L3']['profiles'], 24)
        self.assertEqual(len(set(selected)), 24)
        self.assertFalse(any(profile.startswith('syn-') for profile in selected))

    def test_empty_seen_cohort_does_not_fall_back_to_all_profiles(self):
        with patch.object(seen_evaluation.instances, 'load', return_value={'profiles': []}):
            with patch.object(policies, 'evaluate_learned') as evaluate:
                with self.assertRaisesRegex(ValueError, 'No seen-development profiles'):
                    seen_evaluation.evaluate_seen()
        evaluate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
