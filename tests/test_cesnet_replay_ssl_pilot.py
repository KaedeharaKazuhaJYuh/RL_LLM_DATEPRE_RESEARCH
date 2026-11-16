"""Check that unlabeled sampling does not request labels and uses global row positions."""
import importlib.util
import unittest
from unittest.mock import patch

HAS_DEPS = all(importlib.util.find_spec(x) is not None for x in ('tables', 'torch'))


@unittest.skipUnless(HAS_DEPS, 'PyTables and PyTorch are optional research dependencies')
class ReplaySelectionTests(unittest.TestCase):
    def test_unlabeled_selection_across_batches(self):
        import numpy as np
        from research.reliability_reset.experiments.communication_telemetry.cesnet_input import FlowBatch
        from research.reliability_reset.experiments.communication_telemetry.cesnet_replay_ssl_pilot import select_positions
        def batch(day, values):
            n = len(values)
            return FlowBatch(np.asarray(values).reshape(n, 1, 1), np.ones((n, 1), dtype=bool),
                             np.zeros((n, 57)), (day,) * n, np.arange(n), None)
        def read(path, dates, *, include_labels):
            self.assertFalse(include_labels)
            return iter([batch('2022-04-11', [10, 11]), batch('2022-04-12', [20, 21])])
        with patch('research.reliability_reset.experiments.communication_telemetry.cesnet_replay_ssl_pilot.iter_batches', read):
            events, mask, labels, refs = select_positions('unused', ['2022-04-11', '2022-04-12'], [3, 0], labels=False)
            np.testing.assert_array_equal(events[:, 0, 0], [10, 21])
            self.assertIsNone(labels)
            self.assertEqual(refs, [('2022-04-11', 0), ('2022-04-12', 1)])
            self.assertEqual(mask.shape, (2, 1))
            with self.assertRaises(ValueError):
                select_positions('unused', [], [0, 0], labels=False)
            with self.assertRaises(ValueError):
                select_positions('unused', [], [4], labels=False)
