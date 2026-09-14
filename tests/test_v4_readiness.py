import os
import unittest
from unittest.mock import patch
from research.v4_readiness import check


class V4ReadinessTests(unittest.TestCase):
    def test_missing_key_is_reported_without_secret(self):
        with patch.dict(os.environ, {}, clear=True):
            result = check()
        self.assertFalse(result['live_api_ready'])
        self.assertNotIn('key', ''.join(map(str, result.values())).lower())

    def test_provider_presence_only(self):
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'must-not-leak'}, clear=True):
            result = check()
        self.assertEqual('deepseek', result['api_provider_configured'])
        self.assertNotIn('must-not-leak', str(result))


if __name__ == '__main__':
    unittest.main()
