import unittest

from experiments.v4_llm_failure_audit import failure_kind


class TestFailureAudit(unittest.TestCase):
    def test_retry_and_later_tool_are_distinct(self):
        plan = ['deduplicate', 'fill_missing', 'describe_numeric']
        record = {'passed': False, 'fault': True,
                  'steps': [{'action': action} for action in
                            ['deduplicate', 'fill_missing', 'describe_numeric', 'stop']]}
        self.assertEqual('retry_missing', failure_kind(record, plan))
        record['steps'][1]['action'] = 'deduplicate'
        self.assertEqual('wrong_later_tool', failure_kind(record, plan))

    def test_parse_error_and_early_stop(self):
        plan = ['deduplicate', 'fill_missing', 'describe_numeric']
        record = {'passed': False, 'fault': False,
                  'steps': [{'action': 'deduplicate'}, {'action': 'stop'}]}
        self.assertEqual('early_stop', failure_kind(record, plan))
        record['steps'][1] = {'action': None, 'parse_error': 'bad json'}
        self.assertEqual('parse_error', failure_kind(record, plan))


if __name__ == '__main__':
    unittest.main()
