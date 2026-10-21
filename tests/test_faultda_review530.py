import copy
import json
import unittest
from faultda_bench.review530 import envelope as e
from faultda_bench.review525 import preflight as old
from faultda_bench.coherent395 import suite


class StrictPublicEnvelopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=json.loads(suite.OUTPUT.read_text(encoding='utf-8'))['rows']

    def cases(self):
        return [{'case_id':'internal-contract-fixture',
                 'public_observation':copy.deepcopy(self.rows[0]['public_observation']),
                 'query_event_id':'history:10'}]

    def arms(self,cases):
        a={'name':'rule','public_observation_sha256':{c['case_id']:old.digest(c['public_observation']) for c in cases},
           'effective_input_sha256':{c['case_id']:old.digest(e.packet(c)) for c in cases},
           'allowed_tools':['stop','escalate','receipt_lookup'],
           'tool_budgets':dict(checks=0,mutations=0,decisions=1,response_bytes=10000,wall_seconds=10),
           'preprocessing':e.helper(),'private_truth_access':False}
        b=copy.deepcopy(a);b['name']='model';return [a,b]

    def test_all_72_packets_are_public_derived_and_source_is_unchanged(self):
        for r in self.rows:
            c={'case_id':'opaque','public_observation':r['public_observation'],'query_event_id':'history:10'}
            before=old.digest(c);p=e.packet(c)
            self.assertNotIn('case_id',p)
            self.assertNotIn('private_truth',p)
            self.assertEqual(p['request_binding']['target_publish_event_id'],r['expected_receipt_facts']['receipt_event_id'])
            self.assertEqual(old.digest(c),before)

    def test_extra_arm_context_previously_ignored_is_now_rejected(self):
        c=self.cases();a=self.arms(c);a[1]['extra_oracle_context']='reference answer'
        self.assertEqual(old.compare_setup(c,a)['status'],'setup_declarations_match_not_authenticated')
        with self.assertRaises(ValueError):e.check(c,a)

    def test_fake_equal_helper_hash_or_schema_previously_accepted_now_rejected(self):
        for field,value in [('code_sha256','f'*64),('view_schema','unimplemented-view')]:
            c=self.cases();a=self.arms(c)
            for arm in a:arm['preprocessing'][field]=value
            self.assertEqual(old.compare_setup(c,a)['status'],'setup_declarations_match_not_authenticated')
            with self.subTest(field=field),self.assertRaises(ValueError):e.check(c,a)

    def test_budget_cannot_be_restored_after_checks_are_consumed(self):
        c=self.cases();a=self.arms(c)
        for arm in a:arm['tool_budgets']['checks']=1
        self.assertEqual(old.compare_setup(c,a)['status'],'setup_declarations_match_not_authenticated')
        with self.assertRaises(ValueError):e.check(c,a)

    def test_one_or_both_arms_cannot_substitute_the_effective_packet(self):
        for count in (1,2):
            c=self.cases();a=self.arms(c)
            for arm in a[:count]:arm['effective_input_sha256'][c[0]['case_id']]='f'*64
            with self.subTest(count=count),self.assertRaises(ValueError):e.check(c,a)

    def test_case_metadata_cannot_carry_reference_labels(self):
        c=self.cases()[0];c['expected_receipt_facts']='answer'
        with self.assertRaises(ValueError):e.packet(c)

    def test_matching_packet_does_not_authenticate_execution_or_admit_trial(self):
        c=self.cases();r=e.check(c,self.arms(c))
        self.assertFalse(r['execution_compliance_verified'])
        self.assertIsNone(r['actual_total_costs_equal'])
        self.assertFalse(r['independent_task_eligibility_verified'])
        self.assertFalse(r['ability_gap_measured'])
        self.assertEqual(r['approved_transport_requests'],0)

    def test_mutating_packet_cannot_modify_source_observation(self):
        c=self.cases()[0];before=old.digest(c);p=e.packet(c)
        p['observation']['history'][0]['action']='changed'
        self.assertEqual(old.digest(c),before)


if __name__=='__main__':unittest.main()
