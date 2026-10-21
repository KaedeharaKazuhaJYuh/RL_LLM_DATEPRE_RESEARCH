import itertools
import json
import unittest
from pathlib import Path

import numpy

from faultda_bench.vericost565 import certificate, costs, dp, instances, policies, simulator
from faultda_bench.vericost565.canon import argmax_first, dumps, fsum_
from faultda_bench.vericost565.environment import VeriCostEnv, evaluate
from faultda_bench.semantic.tasks import REPO, sha

COUNTS = instances.VALIDATION_COUNTS
TYPE_C = {'clean': 1, 'single_part_discrepancy': 1, 'multi_part_discrepancy': 8}
AGENT_SHA = {'agent/bandit.py': 'f4419f2dd0f5ac2d70fde0ba457aab8131d1f3c38496bc3b58f2260e9107dcc3',
             'agent/llm.py': '0d6611fe8ae03364c4e14c6018dbd0984f24841921185eb01fa446080ff7dcc2'}
CALLS = {'cc': ('consistency_check', {}), 'full': ('full_recompute', {}),
         'stop': ('stop', {}), 'escalate': ('escalate', {})}


def drive(arm, profile, latent, regime_id, counts=COUNTS):
    """Execute an arm against the real environment, re-deriving its state from the observation."""
    env = VeriCostEnv(instances.materialize(profile, latent), counts=counts, regime=regime_id)
    actions, observation = [], env.observation()
    while not env.terminal:
        state = simulator.state_from_observation(observation, profile, regime_id)
        for entry in observation['history']:
            if entry['action'] == 'full_recompute' and entry['response'].get('ok'):
                state['full_parts'] = tuple(entry['response']['mismatched_parts'])
        state['reads'] = len([entry for entry in observation['history']
                              if entry['action'] == 'read_rows' and entry['response'].get('ok')])
        action = arm.action(state)
        actions.append(action)
        revision = observation['task']['report']['revision']
        if isinstance(action, tuple) and action[0] == 'spot':
            observation = env.step('spot_check', {'part': action[1]})
        elif isinstance(action, tuple) and action[0] == 'read':
            observation = env.step('read_rows', {'part': action[1], 'offset': 0, 'limit': 100})
        elif action in ('publish_patch', 'publish_c1'):
            observation = env.step('publish', {
                'candidate_id': 'patch' if action == 'publish_patch' else 'c1',
                'request_id': f'vc-{len(actions)}', 'expected_revision': revision,
                'write_mode': 'replace'})
        else:
            observation = env.step(*CALLS[action])
    scored = evaluate(env)
    env.close()
    return actions, scored


class RuleFamilyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = {profile['profile_id']: profile for profile in instances.build_profiles()}
        cls.fixtures = certificate.fixtures()

    def test_f_rules_are_the_246_names_of_the_design_in_order(self):
        self.assertEqual(len(policies.F_RULES), 246)
        self.assertEqual(policies.F_RULES[:3], policies.SPECIAL_RULES)
        self.assertEqual([name for name in policies.F_RULES
                          if policies.RULE_SPECS[name] is None], list(policies.SPECIAL_RULES))
        groups = {'cc0': [], 'cc1_k0': [], 'cc1_k': []}
        for name, spec in policies.RULE_SPECS.items():
            if spec is None:
                continue
            check, spots = spec[0], spec[1]
            groups['cc0' if not check else ('cc1_k0' if spots == 0 else 'cc1_k')].append(name)
        self.assertEqual([len(groups[key]) for key in ('cc0', 'cc1_k0', 'cc1_k')], [60, 3, 180])
        self.assertEqual(len(set(policies.F_RULES)), 246)
        self.assertEqual(policies.PROGRAM_ARMS[246:], policies.ADAPTED_ARMS)

    def test_every_rule_state_function_equals_its_execution_in_the_environment(self):
        profile = self.profiles['syn-skewed-n500']
        for latent in (('none',), ('local', 7, True), ('global', 255)):
            for name in policies.PROGRAM_ARMS:
                actions, scored = drive(policies.program_arm(name), profile, latent,
                                        costs.PRIMARY)
                abstract = policies.play(policies.program_arm(name), profile, costs.PRIMARY,
                                         COUNTS, latent)
                where = (name, simulator.latent_id(latent), tuple(map(str, actions)))
                self.assertAlmostEqual(scored['u'], abstract['u'], places=12, msg=where)
                self.assertEqual(scored['safe_complete'], bool(abstract['safe']), where)
                self.assertEqual(scored['cost']['decisions'], abstract['decisions'], where)

    def test_an_f_rule_never_reads_the_public_history(self):
        """The factorization of design 1.5 is only valid if U_f depends on the latent alone."""
        profile = self.fixtures[1]
        for name in policies.PROGRAM_ARMS:
            for latent in simulator.latents('rev1', len(profile['parts'])):
                first = policies.play(policies.program_arm(name), profile, costs.PRIMARY,
                                      COUNTS, latent)
                second = policies.play(policies.program_arm(name), profile, costs.PRIMARY,
                                       TYPE_C, latent)
                self.assertEqual(first['u'], second['u'], (name, simulator.latent_id(latent)))

    def test_the_f_hist_cell_argmax_equals_brute_force_over_every_nine_cell_map(self):
        chosen = [self.fixtures[index] for index in (0, 1, 3)]
        rules = ('never_verify', 'always_full_recompute', 'cc1_k1_asc_rows_mis-full_flag-patch')
        values = {}
        for rule in rules:
            arm = policies.program_arm(rule)
            for profile in chosen:
                for history in simulator.history_states():
                    cell = f"{history['map_type']}|{profile['size_bucket']}"
                    row = policies.expected(arm, profile, 'k1.00_L3', history['counts'], 'rev1')
                    values[(rule, cell)] = (values.get((rule, cell), 0.0)
                                            + history['weight'] * row['u'])
        cells = sorted({cell for _, cell in values})
        self.assertEqual(len(cells), 9)
        per_cell = {cell: argmax_first([(rule, values[(rule, cell)]) for rule in rules])
                    for cell in cells}
        brute = max(itertools.product(rules, repeat=len(cells)),
                    key=lambda combo: fsum_(values[(rule, cell)]
                                            for rule, cell in zip(combo, cells)))
        self.assertEqual([per_cell[cell] for cell in cells], list(brute))
        self.assertGreater(len(set(per_cell.values())), 1)  # the map is not a constant rule
        arm = policies.f_hist(per_cell)
        self.assertEqual(arm.family, 'F_hist')
        state = simulator.initial_state(chosen[0], TYPE_C, 'k1.00_L3')
        self.assertEqual(arm.member(state), per_cell[f'C|{chosen[0]["size_bucket"]}'])

    def test_always_full_recompute_is_priced_rather_than_banned(self):
        """E[U] = V - cost(full) under every latent, and the committed regret is far above
        epsilon: 1.264 on DEV-SYN at the primary (0.867 under the design's 0.25/0.5/0.25 size
        weights; DEV-SYN weights the three size buckets equally)."""
        arm = policies.program_arm('always_full_recompute')
        for name in ('syn-equal-n500', 'syn-equal-n5000', 'syn-equal-n50000'):
            profile = self.profiles[name]
            price = costs.cost(profile, costs.PRIMARY, 'full_recompute')
            for latent in simulator.latents('rev1', len(profile['parts'])):
                row = policies.play(arm, profile, costs.PRIMARY, COUNTS, latent)
                self.assertAlmostEqual(row['u'], costs.V - price, places=12, msg=name)
                self.assertEqual(row['safe'], 1.0)
        committed = json.loads(Path(f'{certificate.ROOT}/reports/vericost565/gate0_rev1_dev.json')
                               .read_text(encoding='utf-8'))
        primary = next(row for row in committed['sets']['dev_syn']['regimes'] if row['primary'])
        self.assertGreater(primary['families']['always_full_recompute']['regret'], 0.5)
        self.assertIn('always_full_recompute', policies.F_RULES)

    def test_static_semantic_coincides_with_always_full_recompute_and_is_labelled(self):
        profile = self.profiles['syn-equal-n5000']
        alias, origin = policies.program_arm('static_semantic'), policies.program_arm(
            'always_full_recompute')
        self.assertEqual(alias.family, 'static_semantic')
        for latent in simulator.latents('rev1', len(profile['parts'])):
            self.assertEqual(policies.play(alias, profile, costs.PRIMARY, COUNTS, latent),
                             policies.play(origin, profile, costs.PRIMARY, COUNTS, latent))

    def test_guarded_read_pays_a_dominated_read_and_is_counted(self):
        profile = self.profiles['syn-equal-n5000']
        arm = policies.program_arm('guarded_read')
        clean = policies.play(arm, profile, costs.PRIMARY, COUNTS, ('none',))
        self.assertEqual(clean['reads'], 0.0)  # a matching recompute stops without a read
        faulty = policies.play(arm, profile, costs.PRIMARY, COUNTS, ('local', 3, False))
        self.assertEqual(faulty['reads'], 1.0)
        self.assertEqual(faulty['safe'], 1.0)
        price = costs.cost(profile, costs.PRIMARY, 'read_rows', 3)
        full = policies.play(policies.program_arm('always_full_recompute'), profile,
                             costs.PRIMARY, COUNTS, ('local', 3, False))
        self.assertAlmostEqual(faulty['u'], full['u'] - price, places=12)

    def test_c4_assert_guards_every_expected_utility_before_aggregation(self):
        profile = self.fixtures[0]
        value = policies.expected_u('always_full_recompute', profile, costs.PRIMARY, COUNTS)
        self.assertTrue(policies.expected_u('always_full_recompute', profile, costs.PRIMARY,
                                            COUNTS, eu_star=value + 1e-12))
        with self.assertRaises(RuntimeError) as refused:
            policies.expected_u('always_full_recompute', profile, costs.PRIMARY, COUNTS,
                                eu_star=value - 0.01)
        self.assertIn('INV-DP violated: C4/always_full_recompute', str(refused.exception))


class LearnedArmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.unit = certificate.unit_profile()

    def test_training_refuses_any_profile_outside_the_development_split(self):
        held_out = dict(self.unit, split='held_out')
        for trainer in (policies.train_q, policies.train_thompson, policies.train_linucb):
            with self.assertRaises(ValueError) as refused:
                trainer([held_out], costs.PRIMARY, 10)
            self.assertEqual(str(refused.exception), 'non-development profile in training')

    def test_the_nig_posterior_matches_hand_computed_values_after_two_rewards(self):
        prior = (policies.NIG_PRIOR['mu0'], policies.NIG_PRIOR['kappa0'],
                 policies.NIG_PRIOR['a0'], policies.NIG_PRIOR['b0'], 0)
        first, second = 0.4, -0.2
        posterior = policies.nig_update(policies.nig_update(prior, first), second)
        mean = (first + second) / 2
        scatter = (first - mean) ** 2 + (second - mean) ** 2
        expected = ((first + second) / 3, 3.0, 2.0,
                    1 + scatter / 2 + 1 * 2 * mean ** 2 / (2 * 3), 2)
        for index, value in enumerate(expected):
            self.assertAlmostEqual(posterior[index], value, places=12, msg=index)
        self.assertEqual(policies.nig_posterior(2), (3.0, 2.0))

    def test_the_gate_action_set_covers_every_decision_an_f_rule_can_make(self):
        """Design 2.6: the gate's actions cover every F decision apart from part order, so the
        learned-versus-rule comparison is not biased."""
        profile = next(item for item in instances.build_profiles()
                       if item['profile_id'] == 'syn-skewed-n500')
        mapped = {'desc_rows': set(), 'asc_rows': set(), 'smallest_then_desc': set(),
                  'flag_patch': set()}
        for name in policies.F_RULES:
            spec = policies.RULE_SPECS[name]
            arm = policies.program_arm(name)
            for latent in simulator.latents('rev1', len(profile['parts'])):
                state = simulator.initial_state(profile, COUNTS, costs.PRIMARY)
                while not state['terminal']:
                    action = arm.action(state)
                    equivalents = policies.gate_equivalents(action, state)
                    self.assertTrue(equivalents, (name, action, state['cc'], state['rem']))
                    self.assertTrue(set(equivalents) <= set(simulator.GATE_ACTIONS))
                    if spec is not None and isinstance(action, tuple):
                        if state['flag'] is not None and spec[4] == 'patch':
                            mapped['flag_patch'].update(equivalents)
                        else:
                            mapped[spec[2]].update(equivalents)
                    state, _ = simulator.step_abstract(state, action, latent)
                    if state['full'] != 'none' and 'full_parts' not in state:
                        state['full_parts'] = tuple(sorted(
                            simulator.affected_parts(latent, len(profile['parts']))))
        self.assertIn('spot_large', mapped['desc_rows'])
        self.assertIn('spot_small', mapped['asc_rows'])
        self.assertNotIn('spot_large', mapped['asc_rows'])
        self.assertEqual({'spot_small', 'spot_large'} & mapped['smallest_then_desc'],
                         {'spot_small', 'spot_large'})
        self.assertIn('spot_flagged', mapped['flag_patch'])
        for state in (simulator.initial_state(profile, COUNTS, costs.PRIMARY),):
            self.assertEqual(policies.legal_actions(state),
                             ('escalate', 'stop', 'cc', 'spot_small', 'spot_large', 'full'))

    def test_the_gate_action_set_expresses_the_dp_action_at_the_post_flag_state(self):
        """The representation is adequate: scored by the DP's own action values, the greedy gate
        action at the post-flag state is `spot_flagged`, i.e. the DP's spot(j)."""
        oracle = dp.Oracle(self.unit, COUNTS, costs.PRIMARY)
        state = simulator.initial_state(self.unit, COUNTS, costs.PRIMARY)
        flagged, _ = simulator.step_abstract(state, 'cc', ('local', 1, True))
        compact_state = (1, 0, 0, 'none', flagged['rem'])
        self.assertEqual(oracle.compact_policy(compact_state), 'spot:1')
        items = dict(oracle.compact_items(*compact_state))
        row = {}
        for name in policies.legal_actions(flagged):
            part = simulator._resolve_part(flagged, name) if name.startswith('spot') else None
            label = f'spot:{part}' if part is not None else name
            if label in items:
                row[name] = items[label]
        self.assertEqual(argmax_first([(name, row.get(name, 0.0))
                                       for name in policies.legal_actions(flagged)]),
                         'spot_flagged')

    def test_the_reduced_q_run_does_not_recover_the_dp_action_at_the_post_flag_state(self):
        """Plan item 12 predicted that the reduced run's greedy action at the post-flag state
        would equal the DP's. It does not, and this records the measured outcome (amendment
        seq 3). Read with the capability assertion above: the gate action set DOES cover the
        DP's decision, so the gap is slow credit assignment at the pre-registered configuration
        and episode budget, not a missing action. Whether another configuration would recover it
        is untested here.
        """
        trained = policies.train_q([self.unit], costs.PRIMARY, 20000)
        self.assertEqual(trained['stats']['episodes'], 20000)
        self.assertEqual(trained['stats']['states'], 696)
        table = trained['q']
        seen, unseen = {}, []
        for kind, counts in certificate.C1_HISTORIES:
            state = simulator.initial_state(self.unit, counts, costs.PRIMARY)
            flagged, _ = simulator.step_abstract(state, 'cc', ('local', 1, True))
            oracle = dp.Oracle(self.unit, counts, costs.PRIMARY)
            self.assertEqual(oracle.compact_policy((1, 0, 0, 'none', flagged['rem'])), 'spot:1')
            row = table.get(simulator.state_key(flagged))
            if row is None:
                unseen.append(kind)  # q_only falls back to the F_hist member, not to spot(j)
                continue
            greedy = argmax_first([(name, row.get(name, 0.0))
                                   for name in policies.legal_actions(flagged)])
            seen[kind] = greedy
            self.assertEqual(greedy, 'escalate', kind)
            self.assertNotEqual(greedy, 'spot_flagged', kind)
            # Every action the reduced run explored is still valued below the zero-valued
            # terminal, which is why escalate wins the greedy argmax.
            self.assertLess(max(row.values()), 0.0, row)
        self.assertEqual(sorted(seen), ['A'])
        self.assertEqual(sorted(unseen), ['B', 'C'])

    def test_linucb_returns_the_first_listed_action_on_a_twelve_digit_tie(self):
        bandit = policies.linucb_class()(policies.LINUCB_DIM, ['a', 'b', 'c'], 1.0)
        self.assertIs(policies.VeriCostLinUCB, policies.linucb_class())
        x = numpy.asarray([1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        self.assertEqual(bandit.select(x), 'a')
        bandit.b['c'] = bandit.b['c'] + 1e-14
        self.assertEqual(bandit.select(x), 'a')
        bandit.b['c'] = bandit.b['c'] + 1e-6
        self.assertEqual(bandit.select(x), 'c')

    def test_the_stdlib_linucb_score_equals_a_numpy_reference(self):
        generator = numpy.random.default_rng(565003)
        worst = 0.0
        for _ in range(50):
            matrix = numpy.eye(policies.LINUCB_DIM)
            for _ in range(3):
                draw = generator.normal(size=policies.LINUCB_DIM)
                matrix = matrix + numpy.outer(draw, draw)
            vector = generator.normal(size=policies.LINUCB_DIM)
            x = numpy.concatenate(([1.0], generator.normal(size=policies.LINUCB_DIM - 1)))
            inverse = numpy.linalg.inv(matrix)
            reference = float(inverse @ vector @ x + 1.0 * numpy.sqrt(x @ inverse @ x))
            stdlib = policies.linucb_score([list(row) for row in matrix], list(vector),
                                           list(x), 1.0)
            worst = max(worst, abs(reference - stdlib))
        self.assertLess(worst, 1e-9)

    def test_the_context_and_the_matrix_round_trip(self):
        profile = certificate.unit_profile()
        x = policies.context(profile, COUNTS)
        self.assertEqual(len(x), policies.LINUCB_DIM)
        self.assertEqual(x[0], 1.0)
        self.assertAlmostEqual(fsum_(x[1:4]), 1.0, places=12)
        upper = [float(value) for value in range(21)]
        matrix = policies.expand_matrix(upper)
        self.assertEqual(matrix[0][5], matrix[5][0])
        self.assertEqual(len(matrix), policies.LINUCB_DIM)

    def test_a_reduced_training_run_reproduces_byte_identically(self):
        first = policies.train('rev1', 1, (costs.PRIMARY,), ('q', 'thompson', 'linucb'), 0.001)
        second = policies.train('rev1', 1, (costs.PRIMARY,), ('q', 'thompson', 'linucb'), 0.001)
        self.assertEqual(dumps(first['regimes']), dumps(second['regimes']))
        self.assertEqual(dumps({key: value for key, value in first.items() if key != 'stats'}),
                         dumps({key: value for key, value in second.items() if key != 'stats'}))
        stats = first['stats'][costs.PRIMARY]
        self.assertEqual(stats['q']['episodes'], 400)
        self.assertEqual(stats['thompson']['episodes'], 500)
        self.assertEqual(stats['linucb']['episodes'], 50)

    def test_the_unchanged_agent_modules_are_asserted_by_hash(self):
        for name, digest in AGENT_SHA.items():
            self.assertEqual(sha(REPO / name), digest, name)


class CommittedLearnedArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.learned = json.loads(policies.LEARNED.read_text(encoding='utf-8'))
        cls.evaluation = json.loads(policies.EVALUATION.read_text(encoding='utf-8'))
        cls.gate0 = {model: json.loads(Path(path).read_text(encoding='utf-8'))
                     for model, path in policies.GATE0.items()}

    def test_the_artifacts_carry_the_pre_registered_episode_counts_and_seeds(self):
        self.assertEqual(self.learned['episodes']['q'][costs.PRIMARY], 400000)
        self.assertEqual(sorted(self.learned['episodes']['q'].values())[0], 100000)
        self.assertEqual(len(self.learned['episodes']['q']), 8)
        self.assertEqual(self.learned['episodes']['thompson'], 500000)
        self.assertEqual(self.learned['episodes']['linucb'], 50000)
        self.assertEqual(self.learned['seeds'], {'q': 565001, 'thompson': 565002,
                                                 'linucb': 565003})
        self.assertEqual(self.learned['thompson_prior'], policies.NIG_PRIOR)
        self.assertEqual(self.learned['gate_actions'], list(simulator.GATE_ACTIONS))
        for regime_id, regime in self.learned['regimes'].items():
            self.assertEqual(len(regime['thompson']), 12, regime_id)  # 3 MAP types x 4 buckets
            for cell, row in regime['thompson'].items():
                self.assertTrue(set(row) <= set(policies.F_RULES), cell)
            self.assertTrue(regime['q'])
            self.assertEqual(len(regime['linucb']['a_upper']), len(policies.F_RULES))

    def test_the_evaluation_records_bf_and_the_f_hist_fallback_for_every_regime(self):
        self.assertEqual(self.evaluation['instance_set'], 'all')
        self.assertEqual(self.evaluation['learned_policies_sha256'], sha(policies.LEARNED))
        self.assertEqual(len(self.evaluation['regimes']), 8)
        for regime_id, row in self.evaluation['regimes'].items():
            self.assertIn(row['bf']['family'], ('F', 'F_size', 'F_hist'))
            self.assertEqual(len(row['f_hist_members']), 12)
            for cell, rule in row['f_hist_members'].items():
                self.assertIn(rule, policies.F_RULES, cell)
            for arm in ('q_only', 'thompson', 'linucb'):
                self.assertGreaterEqual(row[arm]['regret'], 0.0, (regime_id, arm))
                self.assertIn('fallback_rule_rate', row[arm])

    def test_the_learned_evaluation_reproduces_the_gate0_aggregate_for_bf(self):
        """bf is Gate 0's argmin, so the independent evaluation path must return min_fixed_r."""
        for regime_id, row in self.evaluation['regimes'].items():
            gate = next(item for item in self.gate0['rev1']['sets']['all']['regimes']
                        if item['regime_id'] == regime_id)
            self.assertAlmostEqual(row['bf_measured']['regret'], gate['min_fixed_r'], places=9,
                                   msg=regime_id)
            self.assertAlmostEqual(row['expected_u_star'], gate['expected_u_star'], places=9,
                                   msg=regime_id)

    def test_the_d1_artifacts_exist_because_rev1_triggered(self):
        self.assertTrue(self.gate0['rev1']['decision']['trigger'])
        self.assertEqual(self.gate0['rev1']['decision']['model_used'], 'd1')
        self.assertEqual(self.evaluation['d1_artifacts'], 'present')
        self.assertTrue(policies.LEARNED_D1.exists())
        d1 = json.loads(policies.LEARNED_D1.read_text(encoding='utf-8'))
        self.assertEqual(d1['model'], 'd1')
        self.assertEqual(list(d1['regimes']), [costs.PRIMARY])
        self.assertEqual(d1['episodes']['q'][costs.PRIMARY], 400000)
        self.assertEqual(self.evaluation['bf_d1']['family'], 'F_hist')

    def test_no_cpu_learned_arm_beats_the_best_fixed_rule_at_any_regime(self):
        """The recorded negative result: the pre-registered learners stay above bf's regret
        everywhere, which the prereg's null_results clause names as a finding."""
        for regime_id, row in self.evaluation['regimes'].items():
            for arm in ('q_only', 'thompson', 'linucb'):
                self.assertGreater(row[arm]['regret'], row['bf_measured']['regret'],
                                   (regime_id, arm))
        primary = self.evaluation['regimes'][costs.PRIMARY]
        self.assertLess(primary['thompson']['regret'], primary['q_only']['regret'])
        self.assertLess(self.evaluation['power_inputs']['mean_delta_u'], 0.0)
        self.assertEqual(len(self.evaluation['power_inputs']['delta_u_by_cluster']), 4)

    def test_the_artifacts_record_no_api_call_and_no_spend(self):
        self.assertEqual(self.evaluation['api_calls'], 0)
        self.assertEqual(self.evaluation['cny_spent'], '0.000000')
        for data in self.gate0.values():
            self.assertEqual(data['api_calls'], 0)
            self.assertEqual(data['cny_spent'], '0.000000')


if __name__ == '__main__':
    unittest.main()
