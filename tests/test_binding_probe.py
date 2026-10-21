import copy
import unittest
from research import binding_probe as b


class BindingDesignTests(unittest.TestCase):
    def test_true_certificates_for_different_reports_do_not_compose(self):
        p = b.make_case('cross_report')
        self.assertEqual(b.weak(p), 'stop')
        self.assertFalse(b.numerically_correct_and_acknowledged(p))
        self.assertEqual(b.joint(p), 'escalate')

    def test_healthy_and_benign_change_must_allow_stop(self):
        for name in ('healthy', 'benign_revision'):
            self.assertEqual(b.joint(b.make_case(name)), 'stop')

    def test_wrong_request_data_and_contract_are_not_accepted(self):
        for field in ('request', 'data', 'contract'):
            p = b.make_case('healthy')
            if field == 'request':
                p['receipt']['request'] = 'another-request'
            else:
                p['report'][field] = 'another-object'
                p['validation']['report'] = b.digest(p['report'])
                p['receipt']['report'] = b.digest(p['report'])
            self.assertEqual(b.joint(p), 'escalate')

    def test_legal_recompute_repairs_all_current_results_not_history(self):
        for row in b.run()['rows']:
            self.assertTrue(row['recomputed_numerically_correct_and_acknowledged'])
            self.assertEqual(row['recompute_action'],
                             'escalate' if row['case'] == 'repaired_history' else 'stop')

    def test_insufficient_budget_never_does_free_recompute(self):
        p = b.make_case('cross_report')
        p['budget']['writes'] = 0
        out, action, cost = b.recompute(p)
        self.assertEqual(out, p)
        self.assertEqual(action, 'escalate')
        self.assertEqual(sum(cost.values()), 0)

    def test_copy_and_unknown_boundary(self):
        p = b.make_case('commit_unknown')
        original = copy.deepcopy(p)
        self.assertEqual(b.joint(p), 'escalate')
        b.recompute(p)
        self.assertEqual(p, original)


if __name__ == '__main__':
    unittest.main()
