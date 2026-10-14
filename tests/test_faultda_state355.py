import copy
import json
import unittest
from faultda_bench.state355.index import revision_index
from faultda_bench.state355.suite import protocol, execute, action_request
from tests.test_faultda_live350 import mock_send

class StateIndexTests(unittest.TestCase):
    def test_timeout_does_not_acknowledge_revision(self):
        obs={'history':[{'action':'inspect','response':{'ok':True,'revision':1}}, {'action':'publish','response':{'ok':False,'revision':2}}]}
        r=revision_index(obs)
        self.assertEqual(r['highest_acknowledged_revision'],1)
        self.assertFalse(r['snapshot_older_than_acknowledged_revision'])
        self.assertEqual(r['publish_attempt_indices_after_snapshot'],[1])
    def test_acknowledged_revision_marks_snapshot_old(self):
        obs={'history':[{'action':'inspect','response':{'ok':True,'revision':1}}, {'action':'publish','response':{'ok':True,'revision':2}}, {'action':'status','response':{'ok':True,'revision':2}}]}
        self.assertTrue(revision_index(obs)['snapshot_older_than_acknowledged_revision'])
        obs['history'].append({'action':'inspect','response':{'ok':True,'revision':2}})
        self.assertFalse(revision_index(obs)['snapshot_older_than_acknowledged_revision'])
    def test_complete_public_history_and_shared_record(self):
        r=execute(protocol(),mock_send)
        for i in range(8):
            pair=[x for x in r['rows'] if x['state']==i]
            self.assertEqual(pair[0]['action_record'],pair[1]['action_record'])
        q=next(q for q in r['requests'] if q['probe']=='action')
        obs=json.loads(q['body']['messages'][1]['content'])
        obs.pop('public_revision_index',None)
        old=copy.deepcopy(obs)
        a=action_request(obs,{'test':'same'},'history');b=action_request(obs,{'test':'same'},'revision_index')
        x=json.loads(a['messages'][1]['content']);y=json.loads(b['messages'][1]['content'])
        self.assertIn('public_revision_index',y);y.pop('public_revision_index')
        self.assertEqual(x,y);self.assertEqual(obs,old)
        for q in r['requests']:
            text=json.dumps(q['body'])
            for hidden in ('before_twice','_before_failures_remaining','stop_permitted_by_checker'):
                self.assertNotIn(hidden,text)
