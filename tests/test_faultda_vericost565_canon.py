import re
import tempfile
import unittest
from pathlib import Path

from faultda_bench.vericost565 import canon

PACKAGE = Path(canon.__file__).resolve().parent
BARE_SUM = re.compile(r'(?<![\w.])sum\(')


class CanonTests(unittest.TestCase):
    def test_floats_are_quantized_at_twelve_significant_digits(self):
        self.assertEqual(canon.canon(0.1 + 0.2), 0.3)
        self.assertEqual(canon.canon(1 / 3), 0.333333333333)
        self.assertEqual(canon.canon({'a': [1e-20, 1.0000000000004]}), {'a': [1e-20, 1.0]})

    def test_negative_zero_becomes_zero_and_scalars_are_untouched(self):
        self.assertEqual(canon.dumps(canon.canon(-0.0)), '0.0\n')
        for value in (0, 7, -7, True, False, None, '', 'latent', '0.1'):
            self.assertIs(canon.canon(value), value)
        self.assertIs(type(canon.canon(True)), bool)

    def test_key_order_is_preserved(self):
        data = {'z': 1, 'a': 2, 'm': {'y': 3, 'b': 4}}
        self.assertEqual(list(canon.canon(data)), ['z', 'a', 'm'])
        self.assertLess(canon.dumps(data).index('"z"'), canon.dumps(data).index('"a"'))

    def test_unsupported_value_is_rejected_rather_than_coerced(self):
        from decimal import Decimal
        with self.assertRaises(TypeError):
            canon.canon({'value': Decimal('1.5')})

    def test_argmax_first_prefers_the_earliest_listed_at_equal_round12(self):
        self.assertEqual(canon.argmax_first([('a', 1.0), ('b', 1.0 + 1e-14)]), 'a')
        self.assertEqual(canon.argmax_first([('b', 1.0 + 1e-14), ('a', 1.0)]), 'b')

    def test_argmax_first_lets_the_twelfth_digit_decide(self):
        self.assertEqual(canon.argmax_first([('a', 1.0), ('b', 1.0 + 5e-13)]), 'b')
        with self.assertRaises(ValueError):
            canon.argmax_first([])

    def test_write_json_once_refuses_a_second_write_and_keeps_the_first_bytes(self):
        with tempfile.TemporaryDirectory(prefix='vericost565_canon_') as folder:
            path = Path(folder) / 'artifact.json'
            digest = canon.write_json_once(path, {'value': 0.1 + 0.2})
            first = path.read_bytes()
            with self.assertRaises(FileExistsError):
                canon.write_json_once(path, {'value': 99.0})
            self.assertEqual(path.read_bytes(), first)
            self.assertEqual(digest, canon.sha_json({'value': 0.3}))
            self.assertEqual(first.decode(), canon.dumps({'value': 0.3}))

    def test_only_canon_serializes_artifacts_and_float_sums_are_compensated(self):
        scanned = 0
        for path in sorted(PACKAGE.glob('*.py')):
            scanned += 1
            for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                where = f'{path.name}:{number}'
                if path.name != 'canon.py':
                    self.assertNotIn('json.dump', line, where)
                if BARE_SUM.search(line):
                    self.assertIn('# int-sum', line, where)
        self.assertGreaterEqual(scanned, 5)


if __name__ == '__main__':
    unittest.main()
