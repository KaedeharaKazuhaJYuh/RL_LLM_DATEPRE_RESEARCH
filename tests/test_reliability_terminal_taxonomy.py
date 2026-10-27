"""Pin every count the terminal-taxonomy record states, and the prose that states them."""

import json
import unittest

from faultda_bench.semantic.tasks import REPO
from research.reliability_reset import terminal_taxonomy as tax

RECORD = REPO / 'research/reliability_reset/TERMINAL_TAXONOMY.md'
PUBLISHED = tax.OUTPUT


class PopulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = tax.population(tax.load())

    def test_the_packet_is_the_one_the_public_record_names(self):
        record = json.loads(tax.RECORD.read_text(encoding='utf-8'))
        self.assertEqual(self.data['source_sha256'], record['sha256'])
        self.assertEqual(self.data['executions'], 60)
        self.assertEqual(self.data['model_executions'], 48)
        self.assertEqual(self.data['rule_executions'], 12)
        self.assertEqual(self.data['api_calls'], 0)

    def test_every_execution_hit_the_same_one_check_cap_and_used_it(self):
        # The cap has no variance, so this packet cannot identify over- or under-checking.
        self.assertEqual(self.data['checks_cap'], {'1': 60})
        self.assertEqual(self.data['checks_used'], {'1': 60})

    def test_all_twenty_seven_failures_are_terminations_not_actions(self):
        self.assertEqual(self.data['terminals'],
                         {'budget_exceeded': 24, 'escalate': 3, 'stop': 33})
        self.assertEqual(self.data['failures'], 27)
        self.assertEqual(self.data['causes'],
                         {'cap_after_publish': 16, 'cap_without_publish': 8,
                          'completed': 33, 'escalation': 3})
        self.assertEqual(self.data['false_completion'], 0)
        self.assertEqual(self.data['agent_wrong_publications'], 0)
        self.assertEqual(self.data['duplicate_events'], 0)
        self.assertEqual(self.data['forbidden_effect'], 0)
        self.assertEqual(self.data['source_intact'], 60)

    def test_twenty_two_of_the_failures_had_already_produced_a_correct_record(self):
        self.assertEqual(self.data['terminal_correct'], 55)
        self.assertEqual(self.data['failures_with_correct_record'], 22)
        self.assertEqual(self.data['failures_with_one_unexecuted_decision'], 24)
        self.assertEqual(self.data['cap_after_publish_by_condition'],
                         {'healthy': 7, 'semantic_error': 9})
        self.assertEqual(self.data['cap_first_action'], {'inspect': 18, 'status': 6})

    def test_the_two_metrics_disagree_on_twenty_two_of_sixty_runs(self):
        self.assertEqual(self.data['model_safe_complete'], 21)
        self.assertEqual(self.data['model_terminal_correct'], 43)
        self.assertEqual(self.data['rule_safe_complete'], 12)
        self.assertEqual(self.data['rule_terminal_correct'], 12)
        gap = self.data['terminal_correct'] - self.data['safe_complete']
        self.assertEqual(gap, 22)

    def test_the_published_artifact_matches_a_fresh_read(self):
        committed = json.loads(PUBLISHED.read_text(encoding='utf-8'))
        self.assertEqual(committed, self.data)

    def test_every_failure_carries_the_reason_it_was_counted(self):
        for row in self.data['rows']:
            self.assertIn(row['cause'],
                          ('completed', 'cap_after_publish', 'cap_without_publish',
                           'escalation'), row['task_id'])
            if row['cause'] == 'completed':
                self.assertTrue(row['safe_complete'])
            else:
                self.assertFalse(row['safe_complete'])
            if row['cause'] == 'cap_after_publish':
                self.assertIn('publish', row['executed'], row['task_id'])


class ProseTests(unittest.TestCase):
    """The record must keep the numbers, and keep the sentence saying what they cannot support."""

    @classmethod
    def setUpClass(cls):
        cls.text = RECORD.read_text(encoding='utf-8')

    def test_the_record_carries_the_headline_counts(self):
        for token in ('27', '24', '22', '16', '43/48', '21/48', '36.7'):
            self.assertIn(token, self.text)

    def test_the_record_refuses_a_rate_estimate_and_a_version_bump(self):
        self.assertIn('存在性陈述，不是率估计', self.text)
        self.assertIn('不占版本号', self.text)
        self.assertIn('至少有两个预算档', self.text)

    def test_the_record_states_the_zero_calls_and_the_reproduction_command(self):
        self.assertIn('0 次 API 调用', self.text)
        self.assertIn('python -m research.reliability_reset.terminal_taxonomy', self.text)
        self.assertIn('python -m unittest tests.test_reliability_terminal_taxonomy', self.text)


if __name__ == '__main__':
    unittest.main()
