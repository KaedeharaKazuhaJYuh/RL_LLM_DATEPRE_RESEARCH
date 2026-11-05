import json
import unittest

from faultda_bench.semantic.tasks import REPO, ROOT, sha
from faultda_bench.vericost565 import VERSION

V46 = ROOT / 'protocols/acceptance_v46.json'
V48 = ROOT / 'protocols/acceptance_v48.json'
AUDIT = ROOT / 'reports/vericost565/audit_0565.json'
ANALYSIS = ROOT / 'reports/vericost565/analysis.json'
RELEASE = ROOT / 'reports/RELEASE_0565.md'
CLAIM = ROOT / 'docs/CLAIM_DECISION_INPUT_0565.md'
LIVE = ROOT / 'docs/VERICOST_0565_LIVE_PROTOCOL.md'
WORKFLOW = REPO / '.github/workflows/faultda-current.yml'
CHANGELOG = REPO / 'CHANGELOG.md'
README = REPO / 'README.md'
PACKAGE_README = ROOT / 'README.md'
CI_STEP = ("      - run: python -m unittest discover -s tests "
           "-p 'test_faultda_vericost565*.py' -v")


class AcceptanceV48Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v46 = json.loads(V46.read_text(encoding='utf-8'))
        cls.v48 = json.loads(V48.read_text(encoding='utf-8'))

    def test_the_catalog_keeps_the_v46_shape_and_scope(self):
        self.assertEqual(sorted(self.v48), sorted(self.v46))
        self.assertEqual(self.v48['version'], VERSION)
        self.assertEqual(self.v48['scientific_gate'], 'HOLD')
        self.assertIs(self.v48['new_experiments_human_reviewed'], False)
        self.assertIn('vericost565_offline_verification_cost', self.v48['new_experiments'])

    def test_every_v46_entry_is_carried_unchanged(self):
        for name, digest in self.v46['files'].items():
            self.assertEqual(self.v48['files'].get(name), digest, name)
        self.assertGreater(len(self.v48['files']), len(self.v46['files']))

    def test_every_listed_file_still_hashes_to_its_recorded_value(self):
        for name, digest in self.v48['files'].items():
            from faultda_bench.ci565 import effective_v48_digest
            self.assertEqual(sha(REPO / name), effective_v48_digest(name, digest), name)

    def test_the_new_evidence_is_registered_and_the_catalog_excludes_itself(self):
        files = self.v48['files']
        for name in ('faultda_bench/protocols/vericost_v1_prereg.json',
                     'faultda_bench/protocols/vericost_v1_instances.json',
                     'faultda_bench/protocols/vericost_v1_plan.json',
                     'faultda_bench/protocols/vericost_v1_amendments.json',
                     'faultda_bench/reports/vericost565/dp_certificate_dev.json',
                     'faultda_bench/reports/vericost565/gate0_rev1_dev.json',
                     'faultda_bench/reports/vericost565/gate0_d1_dev.json',
                     'faultda_bench/reports/vericost565/learned_policies.json',
                     'faultda_bench/reports/vericost565/learned_eval.json',
                     'faultda_bench/reports/vericost565/offline_eval.json',
                     'faultda_bench/reports/vericost565/analysis.json',
                     'faultda_bench/reports/vericost565/cross_version.json',
                     'faultda_bench/reports/vericost565/audit_0565.json',
                     'faultda_bench/reports/RELEASE_0565.md',
                     'faultda_bench/docs/VERICOST_0565_PREREG.md',
                     'faultda_bench/docs/VERICOST_0565_LIVE_PROTOCOL.md',
                     'faultda_bench/docs/CLAIM_DECISION_INPUT_0565.md',
                     'faultda_bench/vericost565/dp.py',
                     'faultda_bench/vericost565/certificate.py',
                     'tests/test_faultda_vericost565_release.py'):
            self.assertIn(name, files, name)
        self.assertNotIn('faultda_bench/protocols/acceptance_v48.json', files)
        self.assertNotIn('.env.local', files)


class AuditRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = json.loads(AUDIT.read_text(encoding='utf-8'))

    def test_the_recorded_audit_covers_every_part_with_zero_spend(self):
        self.assertEqual(self.audit['schema'], 'vericost565.audit.v1')
        self.assertEqual(self.audit['version'], VERSION)
        self.assertEqual(self.audit['parts'], ['v46', 'allowlist', 'write_once', 'no_network',
                                               'replay', 'secret_scan'])
        self.assertEqual(self.audit['v46_unchanged']['files_verified'], 660)
        self.assertEqual(self.audit['api_calls'], 0)
        self.assertEqual(self.audit['cny_spent'], '0.000000')

    def test_the_secret_scan_is_clean_and_reports_counts_only(self):
        scan = self.audit['secret_scan']
        self.assertIs(scan['clean'], True)
        self.assertEqual(scan['key_matches'], 0)
        self.assertEqual(scan['sha256_matches'], 0)
        self.assertEqual(scan['pattern_matches'], 0)
        for key, value in scan.items():
            self.assertIsInstance(value, (int, bool), key)

    def test_the_replay_and_the_diff_allowlist_are_recorded(self):
        self.assertIs(self.audit['replay_outputs']['offline_eval']['identical'], True)
        self.assertIs(self.audit['replay_outputs']['analysis']['identical'], True)
        self.assertEqual(self.audit['diff_allowlist']['base'], '540f7fb')
        for name in self.audit['diff_allowlist']['changed']:
            self.assertIn(name, ('README.md', 'faultda_bench/README.md', 'CHANGELOG.md',
                                 '.github/workflows/faultda-current.yml',
                                 'tests/test_v4_llm_composition.py', 'tests/test_v4_llm_hard.py',
                                 'tests/test_v4_real_csv.py'), name)


class DocumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analysis = json.loads(ANALYSIS.read_text(encoding='utf-8'))
        cls.release = RELEASE.read_text(encoding='utf-8')
        cls.claim = CLAIM.read_text(encoding='utf-8')

    def test_the_release_report_copies_the_committed_numbers(self):
        rev1 = self.analysis['O1']['models']['rev1']['sets']['dev_syn']
        d1 = self.analysis['O1']['models']['d1']['sets']['dev_syn']
        o3 = self.analysis['O3']['regret_by_arm']['k0.30_L3']
        for value in (rev1['decision']['min_fixed_r_primary'], d1['decision']['min_fixed_r_primary'],
                      o3['bf'], o3['q_only'], o3['thompson'], o3['linucb'],
                      self.analysis['O2']['delta_u'], self.analysis['O2']['signflip_p'],
                      self.analysis['min_attainable_signflip_p'],
                      self.analysis['power']['mde']):
            self.assertIn(str(value), self.release, str(value))
        self.assertIn(self.analysis['certificate']['sha256'], self.release)

    def test_the_release_report_keeps_every_boundary_and_the_english_summary(self):
        for needle in ('split: development', 'seen_cluster: true', 'independent_test: false',
                       'generalization_claim', 'API 调用 0 次', '¥0', 'English summary',
                       'agent/llm.py', 'faultda_bench/semantic/deepseek.py', 'pending_live',
                       'F_hist', 'hard_stop'):
            self.assertIn(needle, self.release, needle)
        for key in self.analysis['not_run']:
            self.assertIn(key, self.release, key)
        # The headline is stated as measured bypassability; no unbypassability claim is made.
        self.assertIn('不作任何“不可绕过”声明', self.release)
        self.assertIn('no unbypassability claim', self.release)

    def test_the_claim_decision_input_supplies_evidence_without_deciding(self):
        for needle in ('R_COMPARISON_0520.md', 'vericost565_rejection_conditions.txt',
                       'RL does not beat a rule or SFT with the same representation',
                       'only the old dev cluster shows it', 'FALSIFIED',
                       '0.0315391087846', '0.014189449731', '0.307923762624',
                       'independent_test: false'):
            self.assertIn(needle, self.claim, needle)
        self.assertIn('不作出', self.claim)
        self.assertIn('不选择 A 或 B', self.claim)

    def test_the_live_protocol_is_linked_from_the_two_other_documents(self):
        self.assertIn('VERICOST_0565_LIVE_PROTOCOL.md', self.release)
        self.assertIn('VERICOST_0565_LIVE_PROTOCOL.md', self.claim)
        self.assertTrue(LIVE.exists())


class SharedEditTests(unittest.TestCase):
    def test_ci_uses_registry_and_requires_complete_history(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        self.assertIn('fetch-depth: 0', text)
        self.assertIn('Require complete audit history', text)
        self.assertIn('VERICOST_PY312:', text)
        self.assertIn('python -m faultda_bench.current_evidence --run-tests --verbose', text)
        self.assertNotIn('python -m unittest', text)
        registry = json.loads((ROOT / 'protocols/current_evidence_v1.json').read_text(encoding='utf-8'))
        expected = {'tests.' + p.stem for p in (REPO / 'tests').glob('test_faultda_vericost565*.py')}
        self.assertTrue(expected.issubset(registry['test_modules']))

    def test_the_0_5_65_changelog_entry_keeps_its_bullets_and_the_zero_spend(self):
        lines = CHANGELOG.read_text(encoding='utf-8').splitlines()
        starts = [index for index, line in enumerate(lines)
                  if line.startswith('# FaultDA-Bench %s — ' % VERSION)]
        self.assertEqual(len(starts), 1, starts)
        head = starts[0]
        bullets = [line for line in lines[head:head + 8] if line.startswith('- ')]
        self.assertEqual(len(bullets), 3)
        self.assertTrue(any('0 API calls, ¥0' in line for line in bullets))

    def test_the_readme_keeps_the_inherited_release_line_and_points_at_the_report(self):
        lines = README.read_text(encoding='utf-8').splitlines()
        self.assertEqual(lines[0], '# FaultDA-Bench')
        self.assertEqual(lines[7], '<!-- inherited-release: V5.0.15-beta.2 -->')
        self.assertIn('faultda_bench/reports/RELEASE_0565.md', README.read_text(encoding='utf-8'))
        package = PACKAGE_README.read_text(encoding='utf-8')
        self.assertIn('reports/RELEASE_0565.md', package)
        self.assertIn('vericost565/', package)


if __name__ == '__main__':
    unittest.main()
