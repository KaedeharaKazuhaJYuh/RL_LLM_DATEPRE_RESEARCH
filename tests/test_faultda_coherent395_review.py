import copy
import unittest
from faultda_bench.coherent395 import review as r


class ReviewTests(unittest.TestCase):
    def test_cli_verification_uses_pilot_module(self):
        import json
        import subprocess
        import sys
        result = subprocess.run([sys.executable,'-m','faultda_bench.coherent395.review'],capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(result.stdout)['scope_cases'],36)

    def setUp(self):
        self.reg = r.registry(); self.sub = r.template(self.reg)
        self.sub['reviewer'] = {'name':'test fixture, not a reviewer','declares_human':True,'personally_checked':True,'reviewed_git_commit':'a'*40}
        self.sub['overall_verdict'] = 'change'
        self.sub['case_reviews'] = self.sub['case_reviews'][:1]
        self.row = self.sub['case_reviews'][0]
        self.row['checks'] = {k:True for k in r.CHECKS}; self.row['verdict'] = 'change'

    def test_partial_scope_never_authenticates(self):
        v = r.validate(self.sub,self.reg)
        self.assertEqual(v['status'],'scope_validated_identity_unverified')
        self.assertEqual(len(v['remaining_case_ids']),35)
        self.assertFalse(v['human_review_registered'])
        self.assertFalse(v['reviewer_identity_authenticated'])
        self.assertEqual(v['scientific_gate'],'HOLD')

    def test_unsigned_template_rejected(self):
        self.assertEqual(r.validate(r.template(self.reg),self.reg)['status'],'invalid')

    def test_duplicate_and_unknown_case_rejected(self):
        self.sub['case_reviews'].append(copy.deepcopy(self.row))
        self.assertEqual(r.validate(self.sub,self.reg)['status'],'invalid')
        self.row['case_id'] = 'invented'
        self.assertEqual(r.validate(self.sub,self.reg)['status'],'invalid')

    def test_stale_hash_rejected(self):
        self.row['pair_sha256'] = '0'*64
        self.assertEqual(r.validate(self.sub,self.reg)['status'],'invalid')

    def test_incomplete_checks_and_boolean_impostor_rejected(self):
        self.row['checks']['public_source_and_query'] = 1
        self.assertEqual(r.validate(self.sub,self.reg)['status'],'invalid')

    def test_full_commit_and_human_declaration_required(self):
        self.sub['reviewer']['reviewed_git_commit'] = 'abc123'
        self.sub['reviewer']['declares_human'] = False
        self.assertEqual(r.validate(self.sub,self.reg)['status'],'invalid')
