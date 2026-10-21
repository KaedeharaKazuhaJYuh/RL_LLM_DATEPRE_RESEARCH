import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from faultda_bench.semantic.tasks import REPO
from faultda_bench.vericost565 import audit, suite
from faultda_bench.vericost565.canon import dumps

PACKAGE = REPO / 'faultda_bench/vericost565'
# Planted in a temporary tree only; built from fragments so this file is not itself a hit.
PLANTED = '-'.join(('sk', '0123456789abcdef0123456789abcdef'))
NETWORK_MODULE = 'import urllib.request\n\n\ndef fetch(url):\n    return urllib.request.urlopen(url)\n'
PROVIDER_MODULE = ("ENDPOINT = 'https://api.deep" + "seek.com/chat/completions'\n")
LIVE_MODULE = ('import urllib.request\n\n\ndef probe():\n'
               "    return urllib.request.urlopen('http" + "://127.0.0.1:9/')\n")


def git(repo, *args):
    done = subprocess.run(('git', '-C', str(repo)) + args, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError('git ' + ' '.join(args) + ': ' + done.stderr.strip())
    return done.stdout.strip()


class NoNetworkTests(unittest.TestCase):
    def copy_package(self, name, text):
        folder = tempfile.mkdtemp(prefix='vericost565_pkg_')
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        target = Path(folder) / 'vericost565'
        shutil.copytree(PACKAGE, target)
        (target / name).write_text(text, encoding='utf-8')
        return target

    def test_the_real_package_has_no_transport_and_no_provider_literal(self):
        result = audit.no_network(runtime=False)
        self.assertGreaterEqual(result['modules_scanned'], 12)
        self.assertEqual(sorted(result['blocked_modules']), sorted(audit.BLOCKED_MODULES))
        self.assertIn('urlopen', result['blocked_attributes'])

    def test_a_transport_import_is_rejected(self):
        target = self.copy_package('client.py', NETWORK_MODULE)
        with self.assertRaises(RuntimeError) as refused:
            audit.no_network(target, runtime=False)
        self.assertIn('network or provider path in client.py', str(refused.exception))
        self.assertIn('import urllib.request', str(refused.exception))

    def test_a_provider_host_literal_is_rejected(self):
        target = self.copy_package('prompts.py', PROVIDER_MODULE)
        with self.assertRaises(RuntimeError) as refused:
            audit.no_network(target, runtime=False)
        self.assertIn('literal host or url', str(refused.exception))

    def test_a_live_urlopen_call_is_rejected(self):
        target = self.copy_package('probe.py', LIVE_MODULE)
        with self.assertRaises(RuntimeError) as refused:
            audit.no_network(target, runtime=False)
        self.assertIn('probe.py', str(refused.exception))
        # The same module is also rejected for the attribute access alone.
        attribute_only = self.copy_package('probe.py', 'def probe(session):\n'
                                                       '    return session.urlopen()\n')
        with self.assertRaises(RuntimeError) as second:
            audit.no_network(attribute_only, runtime=False)
        self.assertIn('attribute urlopen', str(second.exception))

    def test_the_runtime_patch_actually_blocks_a_live_call(self):
        """The runtime proof has teeth: the same patched child refuses a real urlopen."""
        folder = tempfile.mkdtemp(prefix='vericost565_live_')
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        (Path(folder) / 'probe_module.py').write_text(LIVE_MODULE + 'probe()\n', encoding='utf-8')
        import sys
        done = subprocess.run((sys.executable, '-c', audit.PATCH, 'probe_module'),
                              capture_output=True, text=True, cwd=folder)
        self.assertNotEqual(done.returncode, 0)
        self.assertIn('network use attempted', done.stderr)

    def test_every_non_exempt_cli_mode_completes_under_patched_transports(self):
        result = audit.no_network()
        self.assertTrue(result['runtime_modes'])
        for label, state in result['runtime_modes'].items():
            self.assertIn(state, ('completed', 'skipped_missing_input'), label)
        self.assertEqual(result['runtime_modes']['instances --check'], 'completed')
        self.assertIn('policies --evaluate', result['exempt_modes'])


class SecretScanTests(unittest.TestCase):
    def tree(self, planted):
        folder = tempfile.mkdtemp(prefix='vericost565_secret_')
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        root = Path(folder)
        (root / '.env.local').write_text('DEEPSEEK_API_KEY=' + PLANTED + '\n', encoding='utf-8')
        (root / 'docs').mkdir()
        (root / 'docs' / 'notes.md').write_text(
            ('the key is ' + PLANTED + '\n') if planted else 'no key here\n', encoding='utf-8')
        return root

    def test_a_planted_key_is_counted_once_and_never_printed(self):
        root = self.tree(True)
        totals = audit.secret_scan(root, root / '.env.local', branch=None, report=None)
        self.assertEqual(totals['key_matches'], 1)
        self.assertEqual(totals['pattern_matches'], 1)
        self.assertIs(totals['clean'], False)
        rendered = dumps(totals)
        self.assertNotIn(PLANTED, rendered)
        self.assertNotIn(PLANTED[:12], rendered)
        self.assertNotIn('key is', rendered)
        # Every reported value is a count or a flag, so no key byte or context can be printed.
        for key, value in totals.items():
            self.assertIsInstance(value, (int, bool), key)

    def test_a_clean_tree_reports_zero_and_skips_the_key_file_itself(self):
        root = self.tree(False)
        totals = audit.secret_scan(root, root / '.env.local', branch=None, report=None)
        self.assertEqual((totals['key_matches'], totals['sha256_matches'],
                          totals['pattern_matches']), (0, 0, 0))
        self.assertIs(totals['clean'], True)
        self.assertEqual(totals['files_scanned'], 1)

    def test_the_sha256_of_the_key_is_also_a_needle(self):
        root = self.tree(False)
        import hashlib
        digest = hashlib.sha256(PLANTED.encode()).hexdigest()
        (root / 'docs' / 'hash.txt').write_text(digest + '\n', encoding='utf-8')
        totals = audit.secret_scan(root, root / '.env.local', branch=None, report=None)
        self.assertEqual(totals['sha256_matches'], 1)
        self.assertEqual(totals['key_matches'], 0)
        self.assertNotIn(digest, dumps(totals))


class AllowlistTests(unittest.TestCase):
    def test_a_modified_frozen_file_fails_the_diff_allowlist(self):
        folder = tempfile.mkdtemp(prefix='vericost565_allow_')
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        root = Path(folder)
        git(root, 'init', '-q')
        (root / 'pyproject.toml').write_text('[project]\nname = "x"\n', encoding='utf-8')
        git(root, 'add', '--', 'pyproject.toml')
        git(root, '-c', 'user.name=T', '-c', 'user.email=t@e.com', 'commit', '-q', '-m', 'base')
        base = git(root, 'rev-parse', 'HEAD')
        (root / 'pyproject.toml').write_text('[project]\nname = "y"\n', encoding='utf-8')
        git(root, 'add', '--', 'pyproject.toml')
        git(root, '-c', 'user.name=T', '-c', 'user.email=t@e.com', 'commit', '-q', '-m', 'edit')
        with self.assertRaises(RuntimeError) as refused:
            audit.diff_allowlist(root, base)
        self.assertIn('pyproject.toml', str(refused.exception))
        self.assertIn('outside the edit allowlist', str(refused.exception))

    def test_the_real_branch_only_touches_allowlisted_paths(self):
        result = audit.diff_allowlist()
        self.assertEqual(result['base'], audit.BASE)
        for name in result['changed']:
            self.assertIn(name, audit.ALLOWLIST)


class FrozenEvidenceTests(unittest.TestCase):
    def test_the_660_file_freeze_still_hashes(self):
        result = audit.v46_unchanged()
        self.assertEqual(result['files_verified'], 660)

    def test_write_once_reports_a_state_for_every_path(self):
        result = audit.write_once()
        self.assertEqual(result['paths'],
                         len(suite.FROZEN_AT_GATE0_PLAN) + len(suite.WRITE_ONCE_OUTPUTS))
        for path, state in result['status'].items():
            self.assertIn(state, ('committed', 'uncommitted', 'pending'), path)
        for path in suite.FROZEN_AT_GATE0_PLAN:
            self.assertIn(result['status'][path], ('committed', 'uncommitted'), path)


class CrossVersionTests(unittest.TestCase):
    def test_the_recorded_proof_lists_every_artifact_and_the_numpy_exclusion(self):
        if not audit.CROSS.exists():
            self.skipTest('cross_version.json is produced by plan item 20')
        data = json.loads(audit.CROSS.read_text(encoding='utf-8'))
        self.assertEqual(data['schema'], audit.CROSS_SCHEMA)
        self.assertEqual(sorted(data['interpreters']), ['py311', 'py312'])
        self.assertTrue(data['interpreters']['py312'].startswith('3.12'))
        self.assertEqual(len(data['artifacts']), 7)
        for row in data['artifacts']:
            self.assertIs(row['identical'], True, row['path'])
            self.assertEqual(row['sha256_py311'], row['sha256_py312'])
        self.assertEqual([row['path'] for row in data['excluded']],
                         ['faultda_bench/reports/vericost565/learned_policies.json'])
        self.assertIn('numpy', data['excluded'][0]['reason'])
        self.assertIn('mitigation', data['excluded'][0])
        self.assertEqual(data['api_calls'], 0)
        self.assertEqual(data['cny_spent'], '0.000000')


if __name__ == '__main__':
    unittest.main()
