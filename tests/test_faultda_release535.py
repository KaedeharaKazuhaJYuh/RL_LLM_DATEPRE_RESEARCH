import copy
import json
import unittest
from unittest.mock import patch
from faultda_bench.release535 import audit as release


class Release535Tests(unittest.TestCase):
    def test_bounded_replay_does_not_claim_new_model_or_science(self):
        result = release.audit()
        self.assertEqual(result['version'], '0.5.35-dev')
        self.assertEqual(result['new_provider_requests'], 0)
        self.assertFalse(result['mechanism_go'])
        self.assertFalse(result['draft_admitted'])
        self.assertEqual(result['human_review'], 'not_arranged')

    def test_changed_derived_output_is_rejected(self):
        old = release.OUTPUTS
        changed = dict(old)
        name = next(iter(changed))
        changed[name] = lambda: {'invented': 'result'}
        with patch.object(release, 'OUTPUTS', changed):
            with self.assertRaisesRegex(ValueError, 'analysis replay mismatch'):
                release.audit()

    def test_draft_cannot_self_approve_transport(self):
        original = release.json.loads
        def changed(text, *args, **kwargs):
            value = original(text, *args, **kwargs)
            if isinstance(value, dict) and value.get('status') == 'DRAFT_NOT_ADMITTED':
                value = copy.deepcopy(value)
                value['approved_transport_requests'] = 1
            return value
        with patch.object(release, 'inventory', return_value=0):
            with patch.object(release.json, 'loads', side_effect=changed):
                with self.assertRaisesRegex(ValueError, 'draft must not'):
                    release.audit()


if __name__ == '__main__':
    unittest.main()
