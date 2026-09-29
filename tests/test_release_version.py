import unittest

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
        self.assertEqual(next_display_version("5.0.95"), "5.0.100")
        for value in ("5.0.5", "5.0.40", "5.0.45", "5.4.05", "5.0.06"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_display_version(value)

    def test_package_metadata_uses_normalized_number(self):
        self.assertEqual(package_version("5.0.05"), "5.0.5")
        self.assertEqual(check_repository(), "5.0.0")


if __name__ == "__main__":
    unittest.main()
