"""Check that adaptation selects only explicitly released labels and rows."""
import importlib.util
import unittest
from unittest.mock import patch

HAS_DEPS = all(importlib.util.find_spec(x) is not None for x in ('tables', 'torch'))


@unittest.skipUnless(HAS_DEPS, 'PyTables and PyTorch are optional research dependencies')
class AdaptiveSelectionTests(unittest.TestCase):
    def test_selects_only_released_rows_without_requesting_other_labels(self):
        import numpy as np
        from research.reliability_reset.experiments.communication_telemetry.cesnet_input import FlowBatch
        from research.reliability_reset.experiments.communication_telemetry.cesnet_adaptive_development import selected_examples
        batch = FlowBatch(np.arange(3 * 30 * 4).reshape(3, 30, 4), np.ones((3, 30), dtype=bool),
                          np.zeros((3, 57)), ('2022-04-11',) * 3, np.array([0, 1, 2]), None)
        def read(path, dates, batch_size):
            return iter([batch])
        with patch('research.reliability_reset.experiments.communication_telemetry.cesnet_adaptive_development.iter_batches', read):
            events, masks, labels = selected_examples('unused', ['2022-04-11'], [('2022-04-11', 2, 8), ('2022-04-11', 0, 7)])
            np.testing.assert_array_equal(events, batch.events[[0, 2]])
            np.testing.assert_array_equal(labels, [7, 8])
            self.assertEqual(masks.shape, (2, 30))
            with self.assertRaises(ValueError):
                selected_examples('unused', ['2022-04-11'], [('2022-04-11', 0, 7), ('2022-04-11', 0, 7)])
            with self.assertRaises(ValueError):
                selected_examples('unused', ['2022-04-11'], [('2022-04-11', 4, 7)])
