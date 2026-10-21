import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from faultda_bench.termination555 import core
from faultda_bench.termination555.runtime import BatchSnapshot


class SnapshotRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = BatchSnapshot.load()

    @classmethod
    def tearDownClass(cls):
        cls.snapshot.close()

    def test_all_registered_public_inputs_and_grades_equal_reference(self):
        decisions = ({'action':'stop','params':{}}, {'action':'escalate','params':{}},
                     {'action':'stage','params':{}})
        for key in self.snapshot.case_ids:
            actual = self.snapshot.prepare(key)
            reference = core.prepare(key)
            self.assertEqual(actual, reference)
            self.assertEqual(json.dumps(actual), json.dumps(reference))
            for decision in decisions:
                self.assertEqual(self.snapshot.grade(key,actual['payload'],actual['body'],decision),
                                 core.grade(key,reference['payload'],reference['body'],decision))

    def test_registered_payload_and_full_body_mutations_still_rejected(self):
        key = 'terminal-000-shared_numeric'
        p = self.snapshot.prepare(key)
        mutations=[]
        payload=copy.deepcopy(p['payload']);del payload['public']['numeric_helper']
        mutations.append((payload,core.wire_body(payload)))
        payload=copy.deepcopy(p['payload'])
        payload['public']['observation']['history'][0]['response']['extra_help']='stop'
        mutations.append((payload,core.wire_body(payload)))
        body=copy.deepcopy(p['body']);body['messages'].append({'role':'system','content':'help'})
        mutations.append((p['payload'],body))
        body=copy.deepcopy(p['body']);body['max_tokens']+=1
        mutations.append((p['payload'],body))
        mutations.append((p['payload'],self.snapshot.prepare('terminal-000-raw')['body']))
        for payload,body in mutations:
            with self.assertRaises(ValueError):
                self.snapshot.verify_supplied(key,payload,body)

    def test_prepared_inputs_and_returned_grades_are_not_mutable_cache_views(self):
        key='terminal-000-raw';p=self.snapshot.prepare(key)
        g=self.snapshot.grade(key,p['payload'],p['body'],{'action':'stop','params':{}})
        p['payload']['public']['observation']['history'].clear()
        p['body']['messages'].clear();g['grade']['schema_valid']=False
        q=self.snapshot.prepare(key)
        self.assertTrue(q['payload']['public']['observation']['history'])
        self.assertEqual(len(q['body']['messages']),2)
        self.assertTrue(self.snapshot.grade(key,q['payload'],q['body'],{'action':'stop','params':{}})['grade']['schema_valid'])

    def test_warm_operations_do_not_reopen_files(self):
        key='terminal-000-shared_numeric'
        with patch.object(Path,'open',side_effect=AssertionError('unexpected warm file access')):
            p=self.snapshot.prepare(key)
            self.snapshot.verify_supplied(key,p['payload'],p['body'])
            self.snapshot.grade(key,p['payload'],p['body'],{'action':'escalate','params':{}})

    def test_complete_fast_qualification_replays_frozen_output(self):
        path=core.ROOT/'faultda_bench/reports/termination555/qualification.json'
        self.assertEqual(self.snapshot.qualify(),json.loads(path.read_text(encoding='utf-8')))

    def test_new_snapshot_detects_source_change_existing_one_remains_explicit_snapshot(self):
        original=Path.open
        target=(core.ROOT/core.SOURCE_NAME).resolve()
        def changed(path,*args,**kwargs):
            if path.resolve()==target:
                return io.BytesIO(b'changed source')
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',changed):
            self.assertTrue(self.snapshot.prepare('terminal-000-raw'))
            with self.assertRaisesRegex(ValueError,'frozen bytes changed'):
                BatchSnapshot.load()

    def test_close_refuses_reuse_and_releases_cases(self):
        snapshot=BatchSnapshot.load();key=snapshot.case_ids[0];p=snapshot.prepare(key)
        snapshot.close();snapshot.close()
        for call in (lambda:snapshot.prepare(key),lambda:snapshot.case_ids,
                     lambda:snapshot.grade(key,p['payload'],p['body'],{'action':'stop','params':{}})):
            with self.assertRaises(RuntimeError):call()

    def test_no_new_identity_attestation_or_private_truth_argument(self):
        key='terminal-000-raw';p=self.snapshot.prepare(key)
        result=self.snapshot.verify_supplied(key,p['payload'],p['body'])
        self.assertFalse(result['case_identity_authenticated'])
        self.assertFalse(result['provider_or_runtime_input_attested'])
        with self.assertRaises(TypeError):
            self.snapshot.grade(key,p['payload'],p['body'],{'action':'stop','params':{}},actual_safe_stop=False)


if __name__=='__main__':unittest.main()
