import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from faultda_bench.current_evidence import VERSION, runner

ROOT = runner.ROOT
WORKFLOW = ROOT / '.github/workflows/faultda-current.yml'
FROZEN_WORKFLOW = ROOT / '.github/workflows/tests.yml'

# Pinned so that adding a module to the registry is a deliberate edit. Phase B
# of 0.5.60 registered tests.test_faultda_release560 and the v47 freeze audit.
# These pins track the living registry, which gains entries every release, so
# acceptance_v47 deliberately does not freeze this module: a hash here would
# make registering the next release's tests fail the freeze audit.
EXPECTED_TEST_MODULES = 78
EXPECTED_EXCLUDED = 22
EXPECTED_AUDITS = 6


class RegistryLoadTests(unittest.TestCase):
    """Pin the registry contract the CI entry point depends on."""

    @classmethod
    def setUpClass(cls):
        cls.registry = runner.load_registry()

    def _reject(self, mutate, message):
        broken = copy.deepcopy(self.registry)
        mutate(broken)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'registry.json'
            path.write_text(json.dumps(broken, ensure_ascii=False), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, message):
                runner.load_registry(path)

    def test_committed_registry_loads(self):
        registry = self.registry
        self.assertEqual('current_evidence', registry['registry'])
        self.assertEqual(1, registry['schema'])
        self.assertEqual(VERSION, registry['version'])
        self.assertEqual('HOLD', registry['scientific_gate'])
        self.assertEqual('3.11', registry['python_version'])
        self.assertEqual(['registry', 'schema', 'version', 'scientific_gate', 'purpose',
                          'python_version', 'discovery', 'test_modules', 'excluded',
                          'excluded_policy', 'excluded_categories', 'audits', 'artifact'],
                         list(registry))

    def test_describe_reports_the_registered_set(self):
        described = runner.describe(self.registry)
        self.assertEqual(EXPECTED_TEST_MODULES, described['test_module_count'])
        self.assertEqual(EXPECTED_TEST_MODULES, len(described['test_modules']))
        self.assertEqual(EXPECTED_EXCLUDED, described['excluded_count'])
        self.assertEqual(EXPECTED_AUDITS, len(described['audits']))
        self.assertEqual('faultda-current-evidence-acceptance', described['artifact_name'])
        self.assertEqual(['work/faultda_current_acceptance.json',
                          'work/faultda_termination555_acceptance.json',
                          'work/stats560.json', 'work/stats560.md',
                          'work/faultda_release560_acceptance.json',
                          'work/faultda_ci565_acceptance.json'],
                         described['artifact_paths'])
        self.assertEqual(['review530_current_acceptance', 'release_version_check',
                          'termination555_performance', 'stats560_uncertainty',
                          'release560_freeze_v47', 'vericost565_ci_v49'],
                         [a['id'] for a in described['audits']])
        self.assertIn('tests.test_faultda_current_evidence', described['test_modules'])
        self.assertEqual('tests.test_release_version', described['test_modules'][-1])

    def test_suite_loads_the_registered_modules(self):
        self.assertGreater(runner.build_suite(self.registry).countTestCases(), 400)

    def test_rejects_a_foreign_registry(self):
        self._reject(lambda r: r.__setitem__('registry', 'something_else'),
                     'not a current_evidence registry')

    def test_rejects_an_unknown_schema(self):
        self._reject(lambda r: r.__setitem__('schema', 2), 'unsupported registry schema')

    def test_rejects_a_released_scientific_gate(self):
        self._reject(lambda r: r.__setitem__('scientific_gate', 'OPEN'),
                     'scientific gate is not HOLD')

    def test_rejects_an_empty_module_list(self):
        self._reject(lambda r: r.__setitem__('test_modules', []), 'test_modules is empty')

    def test_rejects_a_duplicated_module(self):
        self._reject(lambda r: r['test_modules'].append(r['test_modules'][0]),
                     'duplicate test_modules entry')

    def test_rejects_a_module_without_a_file(self):
        self._reject(lambda r: r['test_modules'].append('tests.test_faultda_does_not_exist'),
                     'test module has no file on disk')

    def test_rejects_an_exclusion_without_a_reason(self):
        self._reject(lambda r: r['excluded'][0].pop('reason'),
                     'excluded entry is missing reason')

    def test_rejects_an_undeclared_exclusion_category(self):
        self._reject(lambda r: r['excluded'][0].__setitem__('category', 'because_i_said_so'),
                     'excluded category is not declared')

    def test_rejects_a_module_that_is_both_registered_and_excluded(self):
        self._reject(lambda r: r['test_modules'].append(r['excluded'][0]['module']),
                     'module is both registered and excluded')

    def test_rejects_an_audit_output_outside_work(self):
        self._reject(lambda r: r['audits'][0]['outputs'].__setitem__(0, 'docs/leak.json'),
                     'audit output is not under work/')

    def test_rejects_artifact_paths_that_drift_from_the_audits(self):
        self._reject(lambda r: r['artifact']['paths'].pop(),
                     'artifact.paths differs from the audit outputs')


class RegistryCompletenessTests(unittest.TestCase):
    """The drift guard: no test_faultda_*.py may be silently absent from CI."""

    @classmethod
    def setUpClass(cls):
        cls.registry = runner.load_registry()
        discovery = cls.registry['discovery']
        cls.discovered = {
            'tests.' + path.stem
            for path in (ROOT / discovery['root']).glob(discovery['glob'])}
        cls.registered = set(cls.registry['test_modules'])
        cls.excluded = {entry['module'] for entry in cls.registry['excluded']}

    def test_every_discovered_module_is_registered_or_excluded(self):
        unaccounted = sorted(self.discovered - self.registered - self.excluded)
        self.assertEqual(
            [], unaccounted,
            'these tests/%s files are in neither test_modules nor excluded of %s: %s. '
            'Add each one to test_modules, or add it to excluded with a category and a '
            'reason naming the frozen CI job that already verifies it every run.'
            % (self.registry['discovery']['glob'],
               'faultda_bench/protocols/current_evidence_v1.json',
               ', '.join(name.split('.')[-1] + '.py' for name in unaccounted)))

    def test_no_module_is_both_registered_and_excluded(self):
        self.assertEqual([], sorted(self.registered & self.excluded))

    def test_no_stale_entries(self):
        for name in sorted(self.registered | self.excluded):
            with self.subTest(module=name):
                self.assertTrue((ROOT / 'tests' / (name.split('.')[-1] + '.py')).is_file(),
                                'registry names a module with no file on disk: ' + name)

    def test_every_exclusion_states_a_reason(self):
        for entry in self.registry['excluded']:
            with self.subTest(module=entry['module']):
                self.assertGreaterEqual(len(entry['reason']), 20)

    def test_the_partition_is_exact(self):
        prefix = 'tests.' + self.registry['discovery']['glob'].split('*')[0]
        registered_faultda = {name for name in self.registered if name.startswith(prefix)}
        self.assertEqual(len(self.discovered), len(registered_faultda) + len(self.excluded))
        self.assertEqual(self.discovered, registered_faultda | self.excluded)


class WorkflowGuardTests(unittest.TestCase):
    """Fail if the workflow regains an inline module list or stops using the runner."""

    @classmethod
    def setUpClass(cls):
        cls.registry = runner.load_registry()
        cls.text = WORKFLOW.read_text(encoding='utf-8')

    def test_workflow_encodes_no_module_list(self):
        self.assertIsNone(
            re.search(r'tests\.test_', self.text),
            'faultda-current.yml must not inline test module names; register them in '
            'faultda_bench/protocols/current_evidence_v1.json instead.')
        self.assertNotIn('python -m unittest', self.text)

    def test_workflow_calls_the_runner_once_per_action(self):
        for flag in ('--list', '--run-tests', '--run-audits'):
            with self.subTest(flag=flag):
                self.assertEqual(1, len(re.findall(
                    r'python -m faultda_bench\.current_evidence ' + re.escape(flag) + r'\b',
                    self.text)))
        self.assertIn("python-version: '3.11'", self.text)
        self.assertEqual(self.registry['python_version'], '3.11')

    def test_workflow_uploads_exactly_the_registered_artifact(self):
        self.assertIn('name: ' + self.registry['artifact']['name'], self.text)
        lines = self.text.splitlines()
        starts = [index for index, line in enumerate(lines) if line.strip() == 'path: |']
        self.assertEqual(1, len(starts),
                         'faultda-current.yml must declare exactly one `path: |` upload block; '
                         'found %d' % len(starts))
        indent = len(lines[starts[0]]) - len(lines[starts[0]].lstrip())
        paths = []
        for line in lines[starts[0] + 1:]:
            stripped = line.strip()
            if not stripped or len(line) - len(stripped) <= indent:
                break
            paths.append(stripped)
        self.assertEqual(self.registry['artifact']['paths'], paths)

    def test_workflow_defines_only_the_offline_evidence_job(self):
        lines = self.text.splitlines()
        start = lines.index('jobs:')
        jobs = [match.group(1) for match in
                (re.fullmatch(r'  (\S+):', line) for line in lines[start + 1:]) if match]
        self.assertEqual(['offline-evidence'], jobs)

    def test_frozen_historical_workflow_is_untouched(self):
        frozen = FROZEN_WORKFLOW.read_text(encoding='utf-8')
        self.assertIn('python -m unittest discover -s tests', frozen)
        self.assertIn('faultda_bench.release030.audit', frozen)


if __name__ == '__main__':
    unittest.main()
