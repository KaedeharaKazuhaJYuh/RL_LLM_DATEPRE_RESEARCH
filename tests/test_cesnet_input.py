"""Contract checks for the optional PyTables CESNET input reader."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

HAS_TABLES = importlib.util.find_spec('tables') is not None


@unittest.skipUnless(HAS_TABLES, 'PyTables is an optional research dependency')
class CesnetInputTests(unittest.TestCase):
    def test_mask_whitelist_and_explicit_label_release(self):
        import numpy as np
        import tables
        from research.reliability_reset.experiments.communication_telemetry.cesnet_input import SUMMARY_FIELDS, iter_batches
        dtype = [('PPI', '<i4', (4, 30)), ('PPI_LEN', '<u2'), ('APP', '<i2'), ('TLS_SNI', 'S16')]
        dtype += [(field, '<f8', (8,)) if field.startswith('PHIST_') else (field, '<f8') for field in SUMMARY_FIELDS]
        rows = np.zeros(2, dtype=dtype)
        rows['PPI'] = 9
        rows['PPI_LEN'] = [2, 3]
        rows['APP'] = [7, 8]
        rows['TLS_SNI'] = b'private'
        rows['BYTES'] = [123, 456]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fixture.h5'
            with tables.open_file(path, 'w') as archive:
                group = archive.create_group('/', 'flows')
                archive.create_table(group, 'D20220411', obj=rows)
            batches = list(iter_batches(path, ['2022-04-11'], batch_size=1))
            self.assertEqual(len(batches), 2)
            self.assertIsNone(batches[0].labels)
            self.assertEqual(batches[0].events.shape, (1, 30, 4))
            self.assertEqual(batches[0].summary.shape, (1, 57))
            self.assertEqual(int(batches[0].mask.sum()), 2)
            self.assertTrue(np.all(batches[0].events[0, 2:] == 0))
            self.assertEqual(batches[0].summary[0, 0], 123)
            self.assertEqual(int(batches[1].row_indices[0]), 1)
            labeled = next(iter_batches(path, ['2022-04-11'], include_labels=True))
            np.testing.assert_array_equal(labeled.labels, [7, 8])
            with self.assertRaises(ValueError):
                next(iter_batches(path, ['2022-04-11', '2022-04-11']))
