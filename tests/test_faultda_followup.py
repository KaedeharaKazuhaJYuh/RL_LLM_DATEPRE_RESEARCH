import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from faultda_bench.followup import suite
from faultda_bench.formatdiag.core import Client
from faultda_bench.clarity.tasks import write_json


class FollowupTests(unittest.TestCase):
    def test_failed_history_snapshots_are_public_and_nonterminal(self):
        with patch('urllib.request.urlopen', side_effect=AssertionError('network')):
            plan=suite.protocol()
        self.assertEqual(len(plan['snapshots']),6)
        self.assertEqual(len(plan['order']),12)
        for item in plan['snapshots'].values():
            obs=item['observation']
            self.assertIsNone(obs['terminal'])
            self.assertGreater(len(obs['history']),0)
            self.assertNotIn('historical_mode',obs)
            self.assertNotIn('private_records',obs)

    def test_fake_receipts_verify_and_request_forgery_rejected(self):
        from faultda_bench.semantic.tasks import sha
        fake=Client('deepseek-flash',12,config={'DEEPSEEK_API_KEY':'fake'},transport=lambda r:
            {'choices':[{'finish_reason':'stop','message':{'content':'{"action":"escalate","params":{}}'}}]})
        with tempfile.TemporaryDirectory() as folder:
            plan=Path(folder)/'plan.json'; output=Path(folder)/'fake.json'
            write_json(plan,suite.protocol())
            with patch.object(suite,'Client',return_value=fake),redirect_stdout(io.StringIO()): suite.live(plan,output)
            self.assertEqual(suite.verify(output)['status'],'verified')
            trace=output.with_suffix('.jsonl'); rows=[json.loads(x) for x in trace.read_text().splitlines()]
            rows[0]['request_sha256']='0'*64
            trace.write_text('\n'.join(json.dumps(r) for r in rows)+'\n',encoding='utf-8')
            result=json.loads(output.read_text()); result['trace_sha256']=sha(trace)
            output.write_text(json.dumps(result),encoding='utf-8')
            with self.assertRaises(ValueError): suite.verify(output)
