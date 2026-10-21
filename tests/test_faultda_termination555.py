import copy
import unittest
from unittest.mock import patch
from faultda_bench.termination550 import design as old
from faultda_bench.termination555 import core as new


class RegisteredTerminalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = 'terminal-000-shared_numeric'
        cls.p = new.prepare(cls.case)

    def test_removed_helper_cannot_silently_change_condition(self):
        p = copy.deepcopy(self.p['payload'])
        del p['public']['numeric_helper']
        old.validate(p)  # Existing self-consistency behavior is frozen.
        with self.assertRaisesRegex(ValueError, 'registered case/condition'):
            new.verify_supplied(self.case, p, new.wire_body(p))

    def test_nested_context_is_bound_even_when_old_shape_validator_accepts(self):
        p = copy.deepcopy(self.p['payload'])
        p['public']['observation']['history'][0]['response']['extra_help'] = 'stop'
        old.validate(p)
        with self.assertRaises(ValueError):
            new.verify_supplied(self.case, p, new.wire_body(p))

    def test_extra_system_and_changed_token_cap_rejected(self):
        for change in ('system', 'cap'):
            b = copy.deepcopy(self.p['body'])
            if change == 'system':
                b['messages'].append({'role':'system','content':'extra'})
            else:
                b['max_tokens'] += 1
            with self.assertRaises(ValueError):
                new.verify_supplied(self.case, self.p['payload'], b)

    def test_request_from_another_condition_is_not_accepted(self):
        raw = new.prepare('terminal-000-raw')
        with self.assertRaises(ValueError):
            new.verify_supplied(self.case, self.p['payload'], raw['body'])

    def test_caller_cannot_override_actual_grading_truth(self):
        with self.assertRaises(TypeError):
            new.grade(self.case, self.p['payload'], self.p['body'],
                      {'action':'stop','params':{}}, actual_safe_stop=False)

    def test_registry_truth_flip_is_checked_against_original_source(self):
        reg = new.registry()
        reg['entries'][self.case]['private_actual_safe_stop'] = not reg['entries'][self.case]['private_actual_safe_stop']
        with patch.object(new, 'registry', return_value=reg):
            with self.assertRaisesRegex(ValueError, 'grading truth mismatch'):
                new.prepare(self.case)

    def test_supplied_body_is_not_a_claim_of_runtime_attestation(self):
        result = new.verify_supplied(self.case, self.p['payload'], self.p['body'])
        self.assertTrue(result['supplied_artifacts_match_registry'])
        self.assertFalse(result['provider_or_runtime_input_attested'])
        self.assertNotIn('private_actual_safe_stop', self.p)
        self.assertNotIn('private_actual_safe_stop', self.p['body'])

    def test_returned_inputs_are_independent_copies(self):
        p = new.prepare(self.case)
        p['payload']['public']['observation']['history'].clear()
        p['body']['messages'].clear()
        q = new.prepare(self.case)
        self.assertTrue(q['payload']['public']['observation']['history'])
        self.assertEqual(len(q['body']['messages']), 2)

    def test_identical_observations_do_not_authenticate_hidden_world_identity(self):
        groups = {}
        pair = None
        for key, e in new.registry()['entries'].items():
            previous = groups.setdefault(e['public_packet_sha256'], (key, e))
            if previous[1]['private_actual_safe_stop'] != e['private_actual_safe_stop']:
                pair = (previous[0], key)
                break
        self.assertIsNotNone(pair)
        a, b = [new.prepare(k) for k in pair]
        self.assertEqual(a['payload'], b['payload'])
        for p in (a, b):
            result = new.grade(p['case_id'],p['payload'],p['body'],{'action':'stop','params':{}})
            self.assertTrue(result['binding']['supplied_artifacts_match_registry'])
            self.assertFalse(result['binding']['case_identity_authenticated'])
        self.assertNotEqual(new.grade(a['case_id'],a['payload'],a['body'],{'action':'stop','params':{}})['grade']['actual_safe_completion'],
                            new.grade(b['case_id'],b['payload'],b['body'],{'action':'stop','params':{}})['grade']['actual_safe_completion'])


if __name__ == '__main__':
    unittest.main()
