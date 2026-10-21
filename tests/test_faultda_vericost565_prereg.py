import json
import re
import unittest
from pathlib import Path

from faultda_bench.semantic.tasks import REPO, ROOT, sha
from faultda_bench.vericost565 import VERSION, canon, costs, instances

PREREG = ROOT / 'protocols/vericost_v1_prereg.json'
PREREG_MD = ROOT / 'docs/VERICOST_0565_PREREG.md'
AMENDMENTS = ROOT / 'protocols/vericost_v1_amendments.json'
AMENDMENTS_MD = ROOT / 'docs/VERICOST_0565_AMENDMENTS.md'
LIVE_MD = ROOT / 'docs/VERICOST_0565_LIVE_PROTOCOL.md'
EXPLORATION = ROOT / 'docs/vericost565_exploration'
SCRATCH = REPO / '.agents/tasks/vericost565/scratch'
REJECTIONS = REPO / 'tests/fixtures/vericost565_rejection_conditions.txt'
# Built from fragments so the detector itself is not a hit for the repo-wide secret scan.
SECRET = re.compile('sk' + r'-[A-Za-z0-9]{20,}')
PACKAGE = Path(canon.__file__).resolve().parent


class PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prereg = json.loads(PREREG.read_text(encoding='utf-8'))

    def test_required_keys_are_present(self):
        for key in ('schema', 'version', 'version_scope', 'tie_break', 'framing', 'instance_set',
                    'latent_model', 'fault_mode_mapping', 'regimes', 'primary_regime', 'anchor',
                    'arms', 'metrics', 'dp_certificate', 'hypotheses_offline',
                    'hypotheses_live_pending', 'verdict_rules', 'gate0', 'no_go_table',
                    'rejection_conditions_verbatim', 'design_exploration', 'seeds', 'write_once',
                    'amendment_policy', 'commit_order', 'live_protocol', 'instances_index_sha256',
                    'golden_fixture_sha256'):
            self.assertIn(key, self.prereg)
        self.assertEqual(self.prereg['schema'], 'vericost565.prereg.v1')
        self.assertEqual(self.prereg['version'], VERSION)
        self.assertEqual(self.prereg['tie_break'], 'earliest_listed_wins_at_round12')
        self.assertEqual(self.prereg['framing'], 'measurement')
        self.assertEqual(self.prereg['generalization_claim'], 'none')

    def test_version_scope_records_zero_live_calls_and_the_decision(self):
        scope = self.prereg['version_scope']
        self.assertEqual(scope['live_calls'], 0)
        self.assertEqual(scope['cny_spent'], '0.000000')
        self.assertEqual(scope['decision_record'][0]['text_verbatim'],
                         '先不考虑实跑吧，其他的可以继续迭代')
        for entry in scope['decision_record']:
            self.assertEqual(set(entry), {'source', 'location', 'date', 'text_verbatim'})
        self.assertIn('[key redacted]', canon.compact(scope['superseded']))
        self.assertIn('¥30', scope['carried_forward'])
        for key in ('new_sources', 'heldout_split', 'live_blocks', 'provider_path'):
            self.assertIn(key, scope['rescope'])

    def test_no_provider_key_appears_in_any_committed_record(self):
        for path in (PREREG, PREREG_MD, AMENDMENTS, AMENDMENTS_MD, REJECTIONS):
            self.assertIsNone(SECRET.search(path.read_text(encoding='utf-8')), path.name)

    def test_regimes_and_primary_match_the_cost_model(self):
        self.assertEqual([item['regime_id'] for item in self.prereg['regimes']],
                         list(costs.REGIME_IDS))
        self.assertEqual(self.prereg['primary_regime'], costs.PRIMARY)
        self.assertEqual([item['regime_id'] for item in self.prereg['regimes'] if item['primary']],
                         [costs.PRIMARY])

    def test_the_under_power_declaration_is_pre_registered(self):
        declaration = self.prereg['hypotheses_offline']['under_power_declaration']
        self.assertEqual(declaration['n_clusters'], 4)
        self.assertEqual(declaration['min_attainable_signflip_p'], 0.0625)
        self.assertEqual(declaration['alpha_O2'], 0.05)
        self.assertIn('INCONCLUSIVE', declaration['statement_en'])
        power = self.prereg['verdict_rules']['power']
        self.assertEqual(power['n_clusters'], 4)
        self.assertEqual(power['min_attainable_signflip_p'], 0.0625)

    def test_verdict_thresholds_live_only_in_the_prereg(self):
        rules = self.prereg['verdict_rules']
        self.assertEqual(rules['ci_test'], 'signflip_inversion_0.025')
        self.assertIn('H1-H3', rules['ci_test_scope'])
        self.assertEqual(rules['alpha_O2'], 0.05)
        self.assertEqual(rules['admissibility'], 0.10)
        self.assertEqual(rules['epsilon'], 0.05)
        self.assertEqual(rules['gap_floor'], 0.01)
        self.assertEqual(self.prereg['gate0']['epsilon'], rules['epsilon'])
        forbidden = ('EPSILON', 'ALPHA', 'ADMISSIBILITY', 'GAP_FLOOR', 'CI_TEST')
        for path in sorted(PACKAGE.glob('*.py')):
            for name in forbidden:
                self.assertNotIn(name + ' =', path.read_text(encoding='utf-8'),
                                 f'{path.name} must read {name} from the prereg')

    def test_admissibility_follows_the_prereg_and_not_a_module_constant(self):
        self.assertTrue(costs.admissible(0.10, self.prereg))
        self.assertFalse(costs.admissible(0.09, self.prereg))

    def test_the_certificate_contract_is_pre_registered_and_never_weakened(self):
        certificate = self.prereg['dp_certificate']
        self.assertEqual(certificate['parts'], ['C1', 'C2', 'C3', 'C4', 'C5'])
        self.assertEqual(certificate['tol'], 1e-09)
        self.assertEqual(certificate['mi_threshold_bits'], 1e-12)
        self.assertIn('never reduced', certificate['c3_scope_rule'])
        self.assertIn('no output file is written', certificate['failure_contract'])

    def test_rejection_conditions_diff_byte_for_byte_against_the_fixture(self):
        fixture = REJECTIONS.read_text(encoding='utf-8')
        self.assertEqual('\n'.join(self.prereg['rejection_conditions_verbatim']) + '\n', fixture)
        self.assertIn('R_COMPARISON_0520.md', fixture)
        self.assertIn('RESEARCH_RESTART_2026_10_19.md', fixture)
        self.assertIn('RESEARCH_CONTRIBUTION_DESIGN_2026_10_19.md', fixture)
        self.assertIn('FAULTDA_BENCH_RESEARCH_PROTOCOL_V2.md', fixture)
        self.assertIn('historical_sources.json', fixture)
        self.assertIn('Sources already seen', fixture)
        self.assertGreaterEqual(len(self.prereg['no_go_table']), 9)

    def test_the_exploration_package_is_an_unmodified_copy(self):
        for name in ('gate0.py', 'gate0_v2.py', 'gate0_v3.py', 'gate0_v4.py'):
            self.assertEqual(self.prereg['design_exploration']['scripts_sha256'][name],
                             sha(EXPLORATION / name))
        self.assertEqual(self.prereg['design_exploration']['log_sha256'],
                         sha(EXPLORATION / 'exploration_log.txt'))
        self.assertEqual(self.prereg['design_exploration']['order'][0], 'E1')
        self.assertEqual(self.prereg['design_exploration']['order'][-1], 'E9')
        self.assertTrue(any('R1/R2' in item
                            for item in self.prereg['design_exploration']['not_reproducible']))

    def test_the_exploration_log_labels_every_result_line(self):
        lines = (EXPLORATION / 'exploration_log.txt').read_text(encoding='utf-8').splitlines()
        results = [line for line in lines if line and not line.startswith('#')]
        self.assertGreater(len(results), 100)
        for line in results:
            self.assertRegex(line, r'^E[0-9A-Za-z-]+ label=(explored|D1 candidate|final-check) '
                                   r'config=\{.*\} \| ')
        self.assertNotIn('chosen', '\n'.join(results))

    def test_artifact_hashes_point_at_the_committed_files(self):
        self.assertEqual(self.prereg['instances_index_sha256'], sha(instances.INDEX))
        self.assertEqual(self.prereg['golden_fixture_sha256'], sha(instances.GOLDEN))

    def test_live_protocol_is_deferred_with_the_corrected_prices_and_window(self):
        live = self.prereg['live_protocol']
        self.assertEqual(live['status'], 'deferred_not_run')
        self.assertIs(live['live_authorized'], False)
        self.assertEqual(live['api_calls'], 0)
        self.assertEqual(live['cny_spent'], '0.000000')
        self.assertIs(live['re_verify_before_live'], True)
        self.assertEqual(live['prices']['deepseek-flash'],
                         {'cache_hit': '0.04', 'cache_miss': '2', 'output': '8'})
        self.assertEqual(live['prices']['deepseek-v4-pro'],
                         {'cache_hit': '0.30', 'cache_miss': '9', 'output': '27'})
        self.assertEqual(live['peak_windows_beijing'],
                         [['Mon-Fri', '09:00', '12:00'], ['Mon-Fri', '14:00', '18:00']])
        self.assertEqual(live['off_peak'], 'half price')
        self.assertEqual(live['tz'], 'Asia/Shanghai')
        self.assertEqual(live['access_date'], '2026-10-20')

    def test_the_live_protocol_document_records_the_same_values(self):
        live = self.prereg['live_protocol']
        text = LIVE_MD.read_text(encoding='utf-8')
        for value in (live['status'], live['cny_spent'], live['tz'], live['access_date'],
                      live['source_url'], live['peak_excludes'], 're_verify_before_live',
                      live['floor_cny'], live['cap_cny']):
            self.assertIn(str(value), text)
        for model, prices in live['prices'].items():
            self.assertIn(model, text)
            for price in prices.values():
                self.assertIn(price, text)
        for _, start, end in live['peak_windows_beijing']:
            self.assertIn(start, text)
            self.assertIn(end, text)
        self.assertIn(live['recorded_by'], text)
        self.assertIn('ceil((2/3) · planned_pairs)', text)
        self.assertIn('signflip_p([ε − regret_raw_c]) < 0.025', text)
        self.assertIn('temperature', text)

    def test_the_withdrawn_utc_window_appears_nowhere_in_the_package_or_protocols(self):
        withdrawn = ('16:30', '00:30', 'preferred_utc_window')
        scanned = sorted(PACKAGE.glob('*.py')) + sorted((ROOT / 'protocols').glob('*.json'))
        self.assertGreater(len(scanned), 20)
        for path in scanned:
            text = path.read_text(encoding='utf-8')
            for needle in withdrawn:
                self.assertNotIn(needle, text, '%s in %s' % (needle, path.name))
        # The withdrawal itself is recorded, once, in the deferred live protocol document.
        document = LIVE_MD.read_text(encoding='utf-8')
        self.assertIn('preferred_utc_window', document)
        self.assertIn('撤回', document)

    def test_amendment_policy_and_the_append_only_pair(self):
        policy = self.prereg['amendment_policy']
        self.assertEqual(policy['allowed_kinds'],
                         ['mde_regret_units', 'k_power_table', 'gate0_number_change',
                          'certificate_scope', 'post_eval_erratum'])
        self.assertIn('epsilon', policy['forbidden'])
        self.assertIn('after_commit', policy['entry_fields'])
        text = AMENDMENTS.read_text(encoding='utf-8')
        entries = json.loads(text)['amendments']
        self.assertEqual(text, canon.dumps({'amendments': entries}))
        self.assertEqual([entry['seq'] for entry in entries],
                         list(range(1, len(entries) + 1)))
        markdown = AMENDMENTS_MD.read_text(encoding='utf-8')
        self.assertIn('只允许追加', markdown)
        for entry in entries:
            self.assertEqual(sorted(entry), sorted(policy['entry_fields']))
            self.assertIn(entry['kind'], policy['allowed_kinds'])
            self.assertEqual(len(entry['after_commit']), 40)
            self.assertIn(f"seq {entry['seq']} — `{entry['kind']}`", markdown)
            for key in entry['changes']:
                for forbidden in policy['forbidden']:
                    self.assertNotEqual(key.split('.')[-1], forbidden, key)
        # Appended by the Gate 0 commit: the O2 MDE and the realized cluster power table.
        self.assertEqual([entry['kind'] for entry in entries][:2],
                         ['mde_regret_units', 'k_power_table'])

    def test_write_once_and_commit_order_are_declared(self):
        write_once = self.prereg['write_once']
        self.assertIn('faultda_bench/protocols/vericost_v1_plan.json',
                      write_once['frozen_at_gate0_plan'])
        self.assertEqual(write_once['outputs'],
                         ['faultda_bench/reports/vericost565/offline_eval.json',
                          'faultda_bench/reports/vericost565/analysis.json',
                          'faultda_bench/reports/vericost565/cross_version.json'])
        self.assertEqual(self.prereg['commit_order'],
                         ['C_freeze', 'C_gate0a', 'C_gate0b', 'C_plan', 'C_eval', 'release'])
        with self.assertRaises(FileExistsError):
            canon.write_json_once(AMENDMENTS, {'amendments': []})

    def test_the_markdown_renders_the_same_scope_and_hypotheses(self):
        text = PREREG_MD.read_text(encoding='utf-8')
        self.assertIn('先不考虑实跑吧，其他的可以继续迭代', text)
        self.assertIn('API 调用 0 次、花费 ¥0', text)
        self.assertIn('2^-4 = 0.0625', text)
        for name in ('O1', 'O2', 'O3', 'H1', 'H2', 'H3'):
            self.assertIn(name, text)
        self.assertIn('pending_live', text)
        self.assertIn('k ≥ 6', text)


if __name__ == '__main__':
    unittest.main()
