import random
import unittest

from faultda_bench.vericost565 import costs, instances, simulator
from faultda_bench.vericost565.canon import compact, fsum_
from faultda_bench.vericost565.environment import VeriCostEnv, evaluate

COUNTS = {'clean': 8, 'single_part_discrepancy': 1, 'multi_part_discrepancy': 1}


class SimulatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = instances.synthetic_profiles()
        reference = costs.b_ref(cls.profiles, 'synthetic')
        for profile in cls.profiles:
            profile['b_ref'] = reference
        cls.profile = next(p for p in cls.profiles if p['profile_id'] == 'syn-skewed-n500')
        cls.parts = len(cls.profile['parts'])

    def test_latent_alphabet_per_model(self):
        self.assertEqual(len(simulator.latents('rev1', 8)), 18)
        self.assertEqual(len(simulator.latents('d1', 8)), 1 + 255 + 16)
        self.assertEqual(simulator.LATENTS_REV1[1], ('global', 255))
        self.assertEqual(simulator.latent_id(('local', 3, True)), 'local:3:1')
        with self.assertRaises(ValueError):
            simulator.latents('rev2', 8)

    def test_episode_draws_are_reproducible_from_the_cell_identity(self):
        for kind in simulator.TYPES:
            first = simulator.episode(self.profile, kind)
            self.assertEqual(compact(first), compact(simulator.episode(self.profile, kind)))
            self.assertEqual(len(first['history_classes']), 10)
            self.assertEqual(sum(first['counts'].values()), 10)
        with self.assertRaises(ValueError):
            simulator.episode(self.profile, 'D')

    def test_both_models_share_the_history_and_local_draws(self):
        for profile in self.profiles:
            for kind in simulator.TYPES:
                draw = simulator.episode(profile, kind)
                self.assertGreater(draw['mask'], 0)
                if draw['latent_class'] == 'global':
                    self.assertEqual(draw['latent']['rev1'], 'global:255')
                    self.assertEqual(draw['latent']['d1'], f'global:{draw["mask"]}')
                else:
                    self.assertEqual(draw['latent']['rev1'], draw['latent']['d1'])

    def test_cc_flags_only_a_visible_local_fault(self):
        self.assertEqual(simulator.cc_flagged(('local', 4, True)), (4,))
        self.assertEqual(simulator.cc_flagged(('local', 4, False)), ())
        self.assertEqual(simulator.cc_flagged(('global', 255)), ())
        self.assertEqual(simulator.cc_flagged(('none',)), ())

    def test_observe_reveals_only_the_affected_set_and_the_flag(self):
        latent = ('global', 0b101)
        self.assertEqual(simulator.observe(self.profile, latent, ('full_recompute',)), (0, 2))
        self.assertEqual(simulator.observe(self.profile, latent, ('spot_check', 2)), (2, True))
        self.assertEqual(simulator.observe(self.profile, latent, ('read_rows', 1)), (1, False))
        self.assertEqual(simulator.observe(self.profile, latent, ('stop',)), ())
        with self.assertRaises(ValueError):
            simulator.observe(self.profile, latent, ('inspect',))

    def test_latent_prior_is_a_distribution_and_tracks_the_history(self):
        for model in ('rev1', 'd1'):
            prior = simulator.latent_prior(self.profile, COUNTS, model)
            self.assertAlmostEqual(fsum_(prior.values()), 1.0, places=12)
        clean = {'clean': 10, 'single_part_discrepancy': 0, 'multi_part_discrepancy': 0}
        broken = {'clean': 0, 'single_part_discrepancy': 10, 'multi_part_discrepancy': 0}
        self.assertEqual(simulator.map_type(clean), 'A')
        self.assertEqual(simulator.map_type(broken), 'B')
        self.assertGreater(simulator.latent_prior(self.profile, clean, 'rev1')[('none',)],
                           simulator.latent_prior(self.profile, broken, 'rev1')[('none',)])

    def test_training_sampler_is_seeded_and_refuses_non_development_profiles(self):
        first = [simulator.sample_episode(random.Random(simulator.TRAINING_SEED), self.profiles)]
        second = [simulator.sample_episode(random.Random(simulator.TRAINING_SEED), self.profiles)]
        self.assertEqual(compact(first), compact(second))
        held_out = dict(self.profile, split='independent_test')
        with self.assertRaisesRegex(ValueError, 'non-development profile in training'):
            simulator.sample_episode(random.Random(1), [held_out])

    def test_abstract_state_separates_the_three_flag_states(self):
        state = simulator.initial_state(self.profile, COUNTS, costs.PRIMARY)
        self.assertEqual(simulator.abstract_state(state)[2], 'none')
        flagged, _ = simulator.step_abstract(state, 'cc', ('local', 1, True))
        self.assertEqual(simulator.abstract_state(flagged)[2], 'flag_unchecked')
        mismatch, _ = simulator.step_abstract(flagged, 'spot_flagged', ('local', 1, True))
        self.assertEqual(simulator.abstract_state(mismatch)[2], 'flag_checked_mismatch')
        match, _ = simulator.step_abstract(flagged, ('spot', 1), ('none',))
        self.assertEqual(simulator.abstract_state(match)[2], 'flag_checked_match')
        clean, _ = simulator.step_abstract(state, 'cc', ('none',))
        self.assertEqual(simulator.abstract_state(clean)[2], 'ok')

    def test_a_repeated_spot_changes_nothing_but_the_remaining_decisions(self):
        state = simulator.initial_state(self.profile, COUNTS, costs.PRIMARY)
        once, _ = simulator.step_abstract(state, ('spot', 0), ('local', 0, False))
        twice, reward = simulator.step_abstract(once, ('spot', 0), ('local', 0, False))
        self.assertEqual(simulator.abstract_state(once)[:7], simulator.abstract_state(twice)[:7])
        self.assertEqual(twice['spots'], once['spots'])
        self.assertLess(reward, 0)
        self.assertEqual(twice['rem'], once['rem'] - 1)

    def test_read_rows_never_changes_the_abstract_state(self):
        profile, latent = self.profile, ('local', 0, True)
        env = VeriCostEnv(instances.materialize(profile, latent), counts=COUNTS,
                          regime=costs.PRIMARY)
        env.step('consistency_check', {})
        before = simulator.abstract_state(
            simulator.state_from_observation(env.observation(), profile, costs.PRIMARY))
        env.step('read_rows', {'part': 0, 'offset': 0, 'limit': 5})
        after = simulator.state_from_observation(env.observation(), profile, costs.PRIMARY)
        self.assertEqual(before[:7], simulator.abstract_state(after)[:7])
        env.close()

    def test_the_abstract_transition_agrees_with_the_environment(self):
        sequences = [[('cc', ('consistency_check', {}))],
                     [('cc', ('consistency_check', {})), ('spot_large', None),
                      ('publish_patch', None), ('stop', None)],
                     [('full', ('full_recompute', {})), ('publish_c1', None), ('stop', None)],
                     [('spot_small', None), ('escalate', None)]]
        for latent in simulator.latents('rev1', self.parts):
            for sequence in sequences:
                state = simulator.initial_state(self.profile, COUNTS, costs.PRIMARY)
                env = VeriCostEnv(instances.materialize(self.profile, latent), counts=COUNTS,
                                  regime=costs.PRIMARY)
                for action, _ in sequence:
                    state, _ = simulator.step_abstract(state, action, latent)
                    self._mirror(env, action, state)
                if not env.terminal:
                    env.step('stop', {})
                    state, _ = simulator.step_abstract(state, 'stop', latent)
                result = evaluate(env)
                self.assertAlmostEqual(simulator.utility_of(state), result['u'], places=12,
                                       msg=(latent, sequence))
                self.assertEqual(state['outcome']['safe_complete'], result['safe_complete'])
                self.assertEqual(state['outcome']['forbidden_effect'], result['forbidden_effect'])
                env.close()

    def _mirror(self, env, action, state):
        revision = env.observation()['task']['report']['revision']
        if action == 'cc':
            env.step('consistency_check', {})
        elif action == 'full':
            env.step('full_recompute', {})
        elif action.startswith('spot'):
            part = sorted(state['checked'] - set(env.checked))
            env.step('spot_check', {'part': part[0] if part else 0})
        elif action.startswith('publish'):
            env.step('publish', {'candidate_id': 'patch' if action.endswith('patch') else 'c1',
                                 'request_id': 'vc-mirror', 'expected_revision': revision,
                                 'write_mode': 'replace'})
        else:
            env.step(action, {})


if __name__ == '__main__':
    unittest.main()
