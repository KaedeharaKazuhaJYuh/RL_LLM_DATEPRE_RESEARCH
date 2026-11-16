"""Check prediction/score/label ordering and reproducible weekly sampling."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HAS_TABLES = importlib.util.find_spec('tables') is not None


@unittest.skipUnless(HAS_TABLES, 'PyTables is an optional research dependency')
class PrequentialTests(unittest.TestCase):
    def test_seal_precedes_labels_and_sampling_is_repeatable(self):
        import numpy as np
        import tables
        from research.reliability_reset.experiments.communication_telemetry.cesnet_input import SUMMARY_FIELDS, iter_batches
        from research.reliability_reset.experiments.communication_telemetry.cesnet_prequential import run_week
        dtype = [('PPI', '<i4', (4, 30)), ('PPI_LEN', '<u2'), ('APP', '<i2')]
        dtype += [(f, '<f8', (8,)) if f.startswith('PHIST_') else (f, '<f8') for f in SUMMARY_FIELDS]
        rows = np.zeros(6, dtype=dtype)
        rows['PPI_LEN'] = 2
        rows['APP'] = [1, 2, 1, 2, 1, 2]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fixture.h5'
            with tables.open_file(path, 'w') as archive:
                group = archive.create_group('/', 'flows')
                archive.create_table(group, 'D20220411', obj=rows)
            pred_path = Path(folder) / 'pred.npz'
            def predict(batch):
                self.assertIsNone(batch.labels)
                self.assertFalse(pred_path.exists())
                return np.ones(len(batch.row_indices), dtype=np.int32)
            def read(*args, **kwargs):
                if kwargs.get('include_labels'):
                    self.assertTrue(pred_path.is_file(), 'labels accessed before predictions were sealed')
                return iter_batches(*args, **kwargs)
            with patch('research.reliability_reset.experiments.communication_telemetry.cesnet_prequential.iter_batches', read):
                score, released = run_week(path, ['2022-04-11'], predict, np.array([1, 2]), 3, 19, pred_path, 2)
            self.assertEqual(score['flows'], 6)
            self.assertEqual(score['accuracy'], 0.5)
            self.assertAlmostEqual(score['macro_f1_fixed_vocabulary'], 1 / 3)
            self.assertEqual(len(released), 3)
            self.assertEqual(len({(d, row) for d, row, _ in released}), 3)
            with np.load(pred_path) as sealed:
                self.assertEqual(set(sealed.files), {'date', 'row', 'prediction'})
            score2, released2 = run_week(path, ['2022-04-11'], lambda b: np.ones(len(b.row_indices), dtype=np.int32),
                                        np.array([1, 2]), 3, 19, Path(folder) / 'pred2.npz', 4)
            self.assertEqual(released, released2)
            self.assertEqual(score['accuracy'], score2['accuracy'])
            with self.assertRaises(ValueError):
                run_week(path, ['2022-04-11'], predict, np.array([1, 2]), 3, 19, pred_path)
            with self.assertRaises(ValueError):
                run_week(path, ['2022-04-11', '2022-04-18'], predict, np.array([1, 2]), 3, 19, Path(folder) / 'invalid.npz')
