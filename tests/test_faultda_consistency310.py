import copy, json, unittest
from faultda_bench.consistency310.core import check
from faultda_bench.consistency310.suite import run, verify

class ConsistencyTests(unittest.TestCase):
    def test_frozen_replay(self): self.assertEqual(verify()['historical_records'],8)
    def test_self_consistent_forgery_is_not_public_proof(self):
        for r in run()['controls'][1:3]:
            self.assertTrue(r['internal']['pass']); self.assertFalse(r['bound']['pass'])
    def test_invalid_flags_and_ids_fail_closed(self):
        for r in run()['controls'][3:]: self.assertFalse(r['internal']['pass'])
    def test_nonfinite_rejected(self):
        r=copy.deepcopy(run()['controls'][0]['record']); r['total']=float('nan')
        self.assertFalse(check(r)['pass'])
    def test_naive_time_rejected(self):
        r=copy.deepcopy(run()['controls'][0]['record']); r['start_utc']='2015-02-02T00:00:00'
        self.assertFalse(check(r)['pass'])
    def test_coverage_and_version_binding(self):
        r=copy.deepcopy(run()['controls'][0]['record']); r['version']='v2'
        p={'version':'v1','start':r['start_utc'],'end':r['end_utc'],'rows':[]}
        verdict=check(r,p); self.assertIn('version_binding',verdict['violations']); self.assertIn('coverage_binding',verdict['violations'])
