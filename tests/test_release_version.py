import unittest
import tempfile
from pathlib import Path

from scripts.release_version import (
    check_repository,
    next_display_version,
    package_version,
    parse_display_version,
)


class ReleaseVersionTests(unittest.TestCase):
    def test_numbering_and_reserved_ranges(self):
        self.assertEqual(next_display_version("5.0.0"), "5.0.05")
        self.assertEqual(next_display_version("5.0.05"), "5.0.10")
        self.assertEqual(next_display_version("5.0.35"), "5.0.50")
        self.assertEqual(next_display_version("5.0.95"), "5.1.0")
        self.assertEqual(next_display_version("5.3.95"), "5.5.0")
        self.assertEqual(next_display_version("5.0.15-beta.1"), "5.0.15")
        self.assertEqual(package_version("5.0.15-beta.1"), "5.0.15b1")
        for value in ("5.0.5", "5.0.40", "5.0.45", "5.4.05", "5.0.06", "5.0.100", "5.0.15-beta.0"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_display_version(value)

    def test_package_metadata_uses_normalized_number(self):
        self.assertEqual(package_version("5.0.05"), "5.0.5")
        self.assertEqual(check_repository(), "5.0.15-beta.2")

    def test_benchmark_heading_requires_exact_inherited_release(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'VERSION').write_text('5.0.15-beta.2', encoding='utf-8')
            (root / 'pyproject.toml').write_text('[project]\nversion="5.0.15b2"\n', encoding='utf-8')
            readme = root / 'README.md'
            for valid in ('# RL + LLM Data Analysis Agent — V5.0.15-beta.2\n',
                          '# FaultDA-Bench\n<!-- inherited-release: V5.0.15-beta.2 -->\n'):
                readme.write_text(valid, encoding='utf-8')
                self.assertEqual(check_repository(root), '5.0.15-beta.2')
            for invalid in ('# FaultDA-Bench\n',
                            '# FaultDA-Bench\n<!-- inherited-release: V5.0.10 -->\n',
                            '# FaultDA-Bench\n' + '<!-- inherited-release: V5.0.15-beta.2 -->\n' * 2,
                            '# Some other project\n<!-- inherited-release: V5.0.15-beta.2 -->\n'):
                readme.write_text(invalid, encoding='utf-8')
                with self.assertRaises(ValueError):
                    check_repository(root)


if __name__ == "__main__":
    unittest.main()
