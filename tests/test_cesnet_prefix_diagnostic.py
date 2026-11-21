"""A shortened observation must preserve the original packet prefix."""
import importlib.util
import unittest

HAS_DEPS = all(importlib.util.find_spec(x) is not None for x in ('tables', 'torch'))


@unittest.skipUnless(HAS_DEPS, 'PyTables and PyTorch are optional research dependencies')
class PrefixObservationTests(unittest.TestCase):
    def test_shortening_preserves_order_and_does_not_modify_source(self):
        import numpy as np
        from research.reliability_reset.experiments.communication_telemetry.cesnet_prefix_diagnostic import shorten_prefix
        events = np.arange(3 * 4 * 2).reshape(3, 4, 2)
        mask = np.array([[1, 1, 1, 1], [1, 0, 0, 0], [0, 0, 0, 0]], dtype=bool)
        original = events.copy()
        out, valid = shorten_prefix(events, mask)
        np.testing.assert_array_equal(valid, [[1, 1, 1, 0], [1, 0, 0, 0], [0, 0, 0, 0]])
        np.testing.assert_array_equal(out[valid], original[valid])
        self.assertTrue(np.all(out[~valid] == 0))
        np.testing.assert_array_equal(events, original)
