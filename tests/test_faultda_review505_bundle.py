"""Distribution scope must retain runtime and truthful test-count boundaries."""
import unittest
from faultda_bench.review505.bundle import profile


class BundleProfileTests(unittest.TestCase):
    def test_manifest_and_inherited_task_manifests_included(self):
        names = profile({'files': {'research/io.py': 'not-used-here'}})
        self.assertIn('research/io.py', names)
        self.assertIn('tasks/v5/beta_holdout_v1/manifest.json', names)
        self.assertIn('tasks/v5/recovery_beta1/manifest.json', names)
        self.assertIn('faultda_bench/protocols/acceptance_v38.json', names)

    def test_parent_traversal_rejected(self):
        with self.assertRaises(ValueError): profile({'files': {'../outside': ''}})

    def test_absolute_path_rejected(self):
        with self.assertRaises(ValueError): profile({'files': {'/outside': ''}})

    def test_backslash_path_rejected(self):
        with self.assertRaises(ValueError): profile({'files': {'folder\\outside': ''}})


if __name__ == '__main__': unittest.main()
