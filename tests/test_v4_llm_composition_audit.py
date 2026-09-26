import unittest

from research.v4_llm_composition_audit import pair


class PairedAuditTests(unittest.TestCase):
    def test_reports_gains_and_regressions_by_condition(self):
        old, new = {}, {}
        for novelty in ('seen_triple', 'unseen_triple'):
            for fault in (False, True):
                key = (novelty, fault)
                old[key] = {'novelty': novelty, 'fault': fault, 'passed': not fault}
                new[key] = {'novelty': novelty, 'fault': fault,
                            'passed': novelty == 'unseen_triple'}
        scored = pair(old, new)
        self.assertEqual(1, scored['unseen_triple:fault']['gain'])
        self.assertEqual(1, scored['seen_triple:clean']['loss'])
        self.assertEqual(1, scored['all']['gain'])
        self.assertEqual(1, scored['all']['loss'])


if __name__ == '__main__':
    unittest.main()
