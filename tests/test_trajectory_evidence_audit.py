import unittest
from research.trajectory_evidence_audit import audit


class HistoricalIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = audit()

    def test_every_indexed_row_links_preserved_response_text(self):
        sources = {s['path']: s for s in self.result['sources']}
        for row in self.result['rows']:
            self.assertTrue(row['request_indices'])
            for i in row['request_indices']:
                self.assertTrue(sources[row['source']]['requests'][i]['response_content_preserved'])

    def test_fact_questions_never_become_model_action_evidence(self):
        for row in self.result['rows']:
            if 'coherent_v38' in row['source'] or 'postreceipt_v36' in row['source']:
                self.assertEqual(row['scope'], 'fact_question_over_scripted_history')
            self.assertEqual(row['causal_attribution'], 'not_identified')
            self.assertFalse(row['independent_new_mechanism_evidence'])

    def test_ready_probe_and_recovery_remain_distinct(self):
        self.assertTrue(self.result['ready_snapshot_actions'])
        for row in self.result['ready_snapshot_actions']:
            self.assertEqual(row['scope'], 'single_action_on_scripted_snapshot')
        for row in self.result['receipt_recovery_outcomes']:
            self.assertEqual(row['scope'], 'actual_model_actions_on_scripted_handoff')


if __name__ == '__main__':
    unittest.main()
