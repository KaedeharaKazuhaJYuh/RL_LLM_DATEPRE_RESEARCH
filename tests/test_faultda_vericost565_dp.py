import unittest

from faultda_bench.vericost565 import certificate, costs, dp, instances, simulator
from faultda_bench.vericost565.canon import argmax_first, fsum_
from faultda_bench.vericost565.environment import VeriCostEnv

COUNTS = instances.VALIDATION_COUNTS
TYPE_B = {'clean': 0, 'single_part_discrepancy': 5, 'multi_part_discrepancy': 5}
ROOT = (dp.CC_NONE, 0, 0, 'none', simulator.HORIZON)


def expectimax(profile, regime_id, counts, model, horizon):
    """An independent belief-state solver: an explicit posterior, no alive-set representation."""
    parts = len(profile['parts'])
    loss = costs.regime(regime_id)['L']
    price = {'cc': costs.cost(profile, regime_id, 'consistency_check'),
             'full': costs.cost(profile, regime_id, 'full_recompute'),
             'spot': [costs.cost(profile, regime_id, 'spot_check', part) for part in range(parts)]}

    def affected(latent):
        return simulator.affected_parts(latent, parts)

    def ending(belief, checked, published):
        terms = []
        for latent, share in belief:
            if published == 'c1':
                correct = True
            elif published == 'patch':
                correct = affected(latent) <= set(checked)
            else:
                correct = not affected(latent)
            terms.append(share * (costs.V if correct else -loss))
        return fsum_(terms)

    def branch(belief, kind, part, cost, checked, cc_done, full, rem):
        groups = {}
        for latent, share in belief:
            if kind == 'cc':
                key = simulator.cc_flagged(latent)
            elif kind == 'full':
                key = tuple(sorted(affected(latent)))
            else:
                key = part in affected(latent)
            groups.setdefault(key, []).append((latent, share))
        terms = [-cost]
        for key in sorted(groups):
            members = groups[key]
            weight = fsum_([share for _, share in members])
            child = tuple((latent, share / weight) for latent, share in members)
            terms.append(weight * value(child, checked + (part,) if kind == 'spot' else checked,
                                        cc_done or kind == 'cc',
                                        ('mismatch' if key else 'match') if kind == 'full' else full,
                                        rem - 1)[0])
        return fsum_(terms)

    def value(belief, checked, cc_done, full, rem):
        if rem <= 0:
            return 0.0, 'horizon'
        items = [('escalate', 0.0), ('stop', ending(belief, checked, None))]
        if rem >= 2:
            if set(checked) & affected(belief[0][0]):
                items.append(('publish_patch', ending(belief, checked, 'patch')))
            if full != 'none':
                items.append(('publish_c1', ending(belief, checked, 'c1')))
            if not cc_done:
                items.append(('cc', branch(belief, 'cc', None, price['cc'], checked, cc_done,
                                           full, rem)))
            for part in range(parts):
                if part not in checked:
                    items.append((f'spot:{part}',
                                  branch(belief, 'spot', part, price['spot'][part], checked,
                                         cc_done, full, rem)))
            if full == 'none':
                items.append(('full', branch(belief, 'full', None, price['full'], checked, cc_done,
                                             full, rem)))
        chosen = argmax_first(items)
        return next(item for label, item in items if label == chosen), chosen

    prior = simulator.latent_prior(profile, counts, model)
    total = fsum_(prior.values())
    belief = tuple((latent, share / total) for latent, share in prior.items())
    return value(belief, (), False, 'none', horizon)


def permute(profile, order):
    """Relabel the parts of a profile; the DP value must not depend on the labelling."""
    out = dict(profile)
    out['parts'] = [dict(profile['parts'][source], part=target)
                    for target, source in enumerate(order)]
    out['rows'] = tuple(profile['rows'][source] for source in order)
    out['report_part_totals'] = [profile['report_part_totals'][source] for source in order]
    out['fault_rows'] = [dict(profile['fault_rows'][source], part=target)
                         for target, source in enumerate(order)]
    out['costs'] = {regime_id: costs.operation_costs(out, regime_id)
                    for regime_id in costs.REGIME_IDS}
    return out


class DpOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = instances.build_profiles()
        cls.by_id = {profile['profile_id']: profile for profile in cls.profiles}
        cls.fixtures = certificate.fixtures()

    def test_the_compact_solver_equals_the_general_solver_under_both_models(self):
        for profile in self.fixtures[:3]:
            for model in ('rev1', 'd1'):
                for regime_id in ('k0.03_L1', 'k0.30_L3'):
                    for _, counts in certificate.C1_HISTORIES:
                        oracle = dp.Oracle(profile, counts, regime_id, model)
                        self.assertAlmostEqual(oracle.compact_root(), oracle.general_root(),
                                               places=12,
                                               msg=(profile['profile_id'], model, regime_id))

    def test_the_dp_matches_an_independent_belief_state_expectimax(self):
        seen = next(profile for profile in self.profiles
                    if profile['kind'] == 'seen_development' and profile['family'] == 'version')
        chosen = [self.by_id['syn-equal-n500'], self.by_id['syn-skewed-n5000'], seen]
        for profile in chosen:
            self.assertEqual(len(profile['parts']), 8)
            for horizon in (2, 3):
                reference, action = expectimax(profile, costs.PRIMARY, TYPE_B, 'rev1', horizon)
                oracle = dp.Oracle(profile, TYPE_B, costs.PRIMARY, 'rev1', horizon)
                self.assertAlmostEqual(oracle.compact_root(), reference, places=12,
                                       msg=(profile['profile_id'], horizon))
                self.assertEqual(oracle.compact_policy((dp.CC_NONE, 0, 0, 'none', horizon)), action,
                                 msg=(profile['profile_id'], horizon))

    def test_an_independent_expectimax_also_agrees_under_the_d1_latent_model(self):
        profile = self.fixtures[1]
        reference, action = expectimax(profile, costs.PRIMARY, TYPE_B, 'd1', 3)
        oracle = dp.Oracle(profile, TYPE_B, costs.PRIMARY, 'd1', 3)
        self.assertAlmostEqual(oracle.compact_root(), reference, places=12)
        self.assertEqual(oracle.compact_policy((dp.CC_NONE, 0, 0, 'none', 3)), action)

    def test_the_dp_value_is_invariant_under_a_part_permutation(self):
        profile = self.by_id['syn-skewed-n500']
        order = tuple(reversed(range(len(profile['parts']))))
        mirrored = permute(profile, order)
        self.assertNotEqual([part['rows'] for part in mirrored['parts']],
                            [part['rows'] for part in profile['parts']])
        for regime_id in ('k0.30_L3', 'k1.00_L1'):
            straight = dp.Oracle(profile, TYPE_B, regime_id).compact_root()
            flipped = dp.Oracle(mirrored, TYPE_B, regime_id).compact_root()
            self.assertAlmostEqual(straight, flipped, places=12, msg=regime_id)

    def test_value_from_history_uses_the_transcript_filtered_alive_set(self):
        profile = self.by_id['syn-equal-n5000']
        oracle = dp.Oracle(profile, COUNTS, costs.PRIMARY)
        env = VeriCostEnv(instances.materialize(profile, ('local', 2, False)), counts=COUNTS,
                          regime=costs.PRIMARY)
        env.step('consistency_check', {})
        env.step('read_rows', {'part': 2, 'offset': 0, 'limit': 5})
        history = env.observation()['history']
        env.close()
        alive = oracle.alive_from_history(history)
        self.assertEqual([simulator.latent_id(oracle.latents[index]) for index in alive],
                         ['global:255', 'local:2:0'])
        self.assertEqual(sorted(simulator.latent_id(latent) for latent in oracle.belief(history)),
                         ['global:255', 'local:2:0'])
        self.assertAlmostEqual(fsum_(oracle.belief(history).values()), 1.0, places=12)
        self.assertEqual(oracle.state_from_history(history), (0, True, 'none', dp.NO_PUBLISH, 4, None))
        self.assertEqual(oracle.value_from_history(history),
                         oracle.general(alive, 0, True, 'none', dp.NO_PUBLISH, 4))
        self.assertEqual(oracle.policy(history), 'full')
        coarse = (dp.CC_OK, 0, 0, 'none', 4)
        self.assertEqual(len(oracle.alive_of(*coarse[:4])), 10)
        self.assertEqual(oracle.compact_policy(coarse), 'spot:0')
        self.assertLess(oracle.value_from_history(history), oracle.compact(*coarse))

    def test_the_optimum_spots_a_small_part_to_enable_a_patch(self):
        """A pruning of uninformative actions would drop this spot and lose value."""
        profile = self.by_id['syn-skewed-n50000']
        smallest = len(profile['parts']) - 1
        oracle = dp.Oracle(profile, TYPE_B, costs.PRIMARY)
        flagged = (smallest, 0, 0, 'none', 5)
        alive = oracle.alive_of(*flagged[:4])
        self.assertEqual([simulator.latent_id(oracle.latents[index]) for index in alive],
                         [f'local:{smallest}:1'])
        self.assertEqual(oracle.compact_policy(flagged), f'spot:{smallest}')
        self.assertEqual(oracle.compact_policy((smallest, 1 << smallest, 1 << smallest, 'none', 4)),
                         'publish_patch')
        items = dict(oracle.compact_items(*flagged))
        without = max(value for label, value in items.items() if label != f'spot:{smallest}')
        self.assertGreater(items[f'spot:{smallest}'], without + 0.01)
        self.assertEqual(oracle.compact_policy((0, 0, 0, 'none', 5)), 'escalate')

    def test_every_unchecked_part_is_a_spot_candidate(self):
        profile = self.by_id['syn-skewed-n500']
        oracle = dp.Oracle(profile, TYPE_B, costs.PRIMARY)
        for checked in (0, 0b10000001, 0b11111110):
            state = (dp.CC_NONE, checked, 0, 'none', 5)
            labels = [label for label, _ in oracle.compact_items(*state)]
            expected = [f'spot:{part}' for part in range(len(profile['parts']))
                        if not checked >> part & 1]
            self.assertEqual([label for label in labels if label.startswith('spot:')], expected)
            self.assertEqual(labels[:2], ['escalate', 'stop'])
            self.assertEqual(labels[-1], 'full')
            general = oracle.general_items(oracle.alive_of(*state[:4]), checked, False, 'none',
                                           dp.NO_PUBLISH, 5)
            self.assertEqual([label for label, _ in general if label.startswith('spot:')], expected)

    def test_a_read_is_weakly_dominated_by_the_spot_of_the_same_part(self):
        profile = self.by_id['syn-skewed-n5000']
        oracle = dp.Oracle(profile, TYPE_B, costs.PRIMARY)
        alive, state = oracle.root, (0, False, 'none', dp.NO_PUBLISH, 6)
        value = oracle.general(alive, *state)
        for part in range(len(profile['parts'])):
            read = oracle.q_value(alive, *state, ('read', part, 0))
            spot = oracle.q_value(alive, *state, ('spot', part))
            self.assertLessEqual(read, spot + dp.TOL, part)
            self.assertLessEqual(read, value + dp.TOL, part)
            self.assertLessEqual(oracle.q_value(alive, *state, ('publish', 'c1', 'append')),
                                 value + dp.TOL)

    def test_publish_state_folds_a_wrong_patch_and_an_append_into_the_penalty(self):
        profile = self.by_id['syn-equal-n500']
        oracle = dp.Oracle(profile, COUNTS, costs.PRIMARY)
        wrong = dp.publish_state(dp.NO_PUBLISH, 'patch', 'replace', 0b1)
        self.assertEqual(wrong, ('patch', 1, 1, False))
        self.assertTrue(oracle.forbidden(oracle.latents.index(('local', 3, True)), wrong))
        self.assertFalse(oracle.forbidden(oracle.latents.index(('local', 0, True)), wrong))
        covered = dp.publish_state(wrong, 'c1', 'replace', 0b1)
        self.assertEqual(covered[0], 'source')
        self.assertTrue(oracle.correct(oracle.latents.index(('global', 255)), covered))
        self.assertTrue(oracle.forbidden(oracle.latents.index(('global', 255)), covered))
        appended = dp.publish_state(dp.NO_PUBLISH, 'c1', 'append', 0)
        self.assertTrue(appended[3])
        self.assertTrue(all(oracle.forbidden(index, appended) for index in oracle.root))


if __name__ == '__main__':
    unittest.main()
