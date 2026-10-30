import unittest

from research.reliability_reset.appworld_pilot110 import parse_local_continuation


class TemplateBoundaryTests(unittest.TestCase):
    def test_opening_in_prompt_and_closing_in_continuation(self):
        result = parse_local_continuation('reasoning</think>{"type":"stop"}',
                                          prompt_opens_think=True, finish_reason="stop")
        self.assertEqual(result, {"type": "stop"})

    def test_do_not_remove_untrusted_prefix_without_open_template(self):
        with self.assertRaises(ValueError):
            parse_local_continuation('reasoning</think>{"type":"stop"}',
                                     prompt_opens_think=False, finish_reason="stop")

    def test_missing_close_and_truncated_output_cannot_become_actions(self):
        for content, reason in (('reasoning', 'stop'), ('</think>{"type":"stop"}', 'length')):
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                parse_local_continuation(content, prompt_opens_think=True, finish_reason=reason)

    def test_preclosed_prompt_does_not_autofill_a_json_action(self):
        with self.assertRaises(ValueError):
            parse_local_continuation('{"type":"call","app":"a"}',
                                     prompt_opens_think=False, finish_reason="stop")


if __name__ == "__main__":
    unittest.main()
