import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from faultda_bench.semantic.tasks import REPO, sha
from faultda_bench.vericost565 import costs, suite
from faultda_bench.vericost565.canon import dumps

PLAN = REPO / suite.PLAN_PATH
AMENDMENT = {'seq': 4, 'utc': '2026-10-21T06:00:00Z', 'kind': 'gate0_number_change',
             'after_commit': '0' * 40, 'text': 'a number change appended too late',
             'changes': {'gate0.min_fixed_r_primary': [0.0315391087846, 0.03]}}


def git(repo, *args):
    done = subprocess.run(('git', '-C', str(repo)) + args, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError('git ' + ' '.join(args) + ': ' + done.stderr.strip())
    return done.stdout.strip()


def commit(repo, message, paths):
    for path in paths:
        git(repo, 'add', '--', path)
    git(repo, '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-q',
        '-m', message)
    return git(repo, 'rev-parse', 'HEAD')


def copy(relative, root):
    source = REPO / relative
    target = Path(root) / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        shutil.copy2(source, target)


def build_repo(folder):
    """A miniature repository with the real artifacts, the real commit order and local shas."""
    root = Path(folder)
    git(root, 'init', '-q')
    stages = (('C_freeze', suite.FREEZE_PATHS + (suite.AMENDMENTS_PATH,)),
              ('C_gate0a', (suite.GATE0_ARTIFACTS[0],)),
              ('C_gate0b', suite.GATE0_ARTIFACTS[1:] + (suite.AMENDMENTS_PATH,)),
              ('C_plan', (suite.PLAN_PATH,) + suite.CODE))
    history = {}
    for label, paths in stages:
        for relative in paths:
            copy(relative, root)
        if label == 'C_freeze':
            (root / suite.AMENDMENTS_PATH).write_text(dumps({'amendments': []}), encoding='utf-8')
        if label == 'C_gate0b':
            entries = json.loads((REPO / suite.AMENDMENTS_PATH).read_text(encoding='utf-8'))
            for entry in entries['amendments']:
                entry['after_commit'] = history['C_gate0a']
            (root / suite.AMENDMENTS_PATH).write_text(dumps(entries), encoding='utf-8')
        history[label] = commit(root, label, paths)
    return history


def append_amendment(root, entry):
    path = Path(root) / suite.AMENDMENTS_PATH
    entries = json.loads(path.read_text(encoding='utf-8'))
    entries['amendments'].append(entry)
    path.write_text(dumps(entries), encoding='utf-8')


def add_output(root, name='offline_eval.json'):
    path = Path(root) / 'faultda_bench/reports/vericost565' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps({'placeholder': name}), encoding='utf-8')
    return commit(root, 'C_eval', ('faultda_bench/reports/vericost565/' + name,))


class TempRepoCase(unittest.TestCase):
    def repo(self):
        folder = tempfile.mkdtemp(prefix='vericost565_repo_')
        self.addCleanup(shutil.rmtree, folder, ignore_errors=True)
        return Path(folder), build_repo(folder)


class PreconditionTests(TempRepoCase):
    def test_every_precondition_passes_in_the_mirror_repository(self):
        root, history = self.repo()
        state = suite.preconditions('offline', repo=root)
        self.assertEqual(state['anchors']['C_freeze'], history['C_freeze'])
        self.assertEqual(state['anchors']['C_plan'], history['C_plan'])
        self.assertEqual(state['h'], {'instances_check': 'ok', 'golden': 'ok'})
        self.assertEqual(state['e']['entries'], 3)
        self.assertIsNone(state['e']['first_output_commit'])
        for path in suite.WRITE_ONCE_OUTPUTS:
            self.assertEqual(state['d'][path]['status'], 'pending')

    def test_a_delete_and_re_add_of_the_pre_registration_fails(self):
        root, _ = self.repo()
        git(root, 'rm', '-q', '--', suite.PREREG_PATH)
        commit(root, 'drop the pre-registration', ())
        copy(suite.PREREG_PATH, root)
        commit(root, 'put it back', (suite.PREREG_PATH,))
        with self.assertRaises(RuntimeError) as refused:
            suite.preconditions('offline', repo=root)
        self.assertIn('precondition (a)', str(refused.exception))
        self.assertIn('exactly one add and no delete', str(refused.exception))

    def test_a_change_to_a_frozen_registration_path_fails(self):
        root, _ = self.repo()
        path = root / 'faultda_bench/docs/VERICOST_0565_PREREG.md'
        path.write_text(path.read_text(encoding='utf-8') + '\n<!-- late edit -->\n',
                        encoding='utf-8')
        commit(root, 'edit the frozen pre-registration', (str(path.relative_to(root)),))
        with self.assertRaises(RuntimeError) as refused:
            suite.preconditions('offline', repo=root)
        self.assertIn('frozen registration paths changed', str(refused.exception))

    def test_modifying_a_gate0_artifact_after_the_plan_fails(self):
        root, _ = self.repo()
        path = root / suite.GATE0_ARTIFACTS[3]
        data = json.loads(path.read_text(encoding='utf-8'))
        data['episodes']['linucb'] = 1
        path.write_text(dumps(data), encoding='utf-8')
        commit(root, 'retrain quietly', (suite.GATE0_ARTIFACTS[3],))
        with self.assertRaises(RuntimeError) as refused:
            suite.preconditions('offline', repo=root)
        self.assertIn('precondition (b)', str(refused.exception))
        self.assertIn('differs from the plan', str(refused.exception))
        with self.assertRaises(RuntimeError) as audited:
            suite.write_once(repo=root, label='write_once')
        self.assertIn('write-once violated', str(audited.exception))

    def test_a_locally_modified_plan_fails_the_clean_tree_check(self):
        root, _ = self.repo()
        path = root / suite.PLAN_PATH
        data = json.loads(path.read_text(encoding='utf-8'))
        data['live_authorized'] = True
        path.write_text(dumps(data), encoding='utf-8')
        with self.assertRaises(RuntimeError) as refused:
            suite.preconditions('offline', repo=root)
        self.assertIn('precondition (c)', str(refused.exception))

    def test_a_perturbed_index_or_golden_fixture_fails_the_rebuild_check(self):
        root, _ = self.repo()
        path = root / suite.INDEX_PATH
        data = json.loads(path.read_text(encoding='utf-8'))
        data['b_ref']['synthetic'] = data['b_ref']['synthetic'] + 1.0
        path.write_text(dumps(data), encoding='utf-8')
        with self.assertRaises(RuntimeError) as refused:
            suite.rebuilds(repo=root)
        self.assertIn('precondition (h)', str(refused.exception))
        copy(suite.INDEX_PATH, root)
        golden = root / suite.GOLDEN_PATH
        golden.write_text(golden.read_text(encoding='utf-8').replace('"b_ref"', '"B_ref"', 1),
                          encoding='utf-8')
        with self.assertRaises(RuntimeError) as second:
            suite.rebuilds(repo=root)
        self.assertIn('golden semantics fixture', str(second.exception))


class WriteOnceTests(TempRepoCase):
    def test_an_already_produced_output_blocks_a_second_offline_evaluation(self):
        root, _ = self.repo()
        add_output(root)
        state = suite.write_once(suite.WRITE_ONCE_OUTPUTS, False, root)
        self.assertEqual(state[suite.WRITE_ONCE_OUTPUTS[0]]['status'], 'committed')
        with self.assertRaises(RuntimeError) as refused:
            suite.preconditions('offline', repo=root)
        self.assertIn('already produced', str(refused.exception))
        self.assertEqual(suite.preconditions('final', repo=root)['stage'], 'final')

    def test_re_adding_a_deleted_output_fails_write_once(self):
        root, _ = self.repo()
        add_output(root)
        git(root, 'rm', '-q', '--', suite.WRITE_ONCE_OUTPUTS[0])
        commit(root, 'drop the evaluation output', ())
        add_output(root)
        for stage in ('offline', 'final'):
            with self.assertRaises(RuntimeError) as refused:
                suite.preconditions(stage, repo=root)
            self.assertIn('write-once', str(refused.exception))
        with self.assertRaises(RuntimeError) as audited:
            suite.write_once(repo=root, label='write_once')
        self.assertIn('deletes=1', str(audited.exception))

    def test_an_amendment_appended_after_the_output_fails_the_timing_rule(self):
        root, _ = self.repo()
        head = add_output(root)
        append_amendment(root, dict(AMENDMENT, after_commit=head))
        commit(root, 'append a late number change', (suite.AMENDMENTS_PATH,))
        with self.assertRaises(RuntimeError) as refused:
            suite.amendments_check(suite.c_freeze(root), repo=root)
        self.assertIn('after the first final output', str(refused.exception))
        self.assertEqual(suite.first_output_commit(root), head)

    def test_a_post_eval_erratum_is_the_only_kind_allowed_after_the_output(self):
        root, _ = self.repo()
        head = add_output(root)
        append_amendment(root, dict(AMENDMENT, seq=4, kind='post_eval_erratum',
                                    after_commit=head,
                                    changes={'hypotheses_offline.O2.measured': [None, 1]}))
        commit(root, 'append an erratum', (suite.AMENDMENTS_PATH,))
        state = suite.amendments_check(suite.c_freeze(root), repo=root)
        self.assertEqual(state['kinds'][-1], 'post_eval_erratum')

    def test_editing_an_earlier_amendment_fails_the_append_only_check(self):
        root, _ = self.repo()
        path = root / suite.AMENDMENTS_PATH
        entries = json.loads(path.read_text(encoding='utf-8'))
        entries['amendments'][0]['text'] = 'rewritten after the fact'
        path.write_text(dumps(entries), encoding='utf-8')
        with self.assertRaises(RuntimeError) as refused:
            suite.amendments_check(suite.c_freeze(root), repo=root)
        self.assertIn('append-only', str(refused.exception))

    def test_a_forbidden_key_or_a_broken_sequence_fails(self):
        root, _ = self.repo()
        append_amendment(root, dict(AMENDMENT, seq=4, kind='post_eval_erratum',
                                    after_commit=suite.c_freeze(root),
                                    changes={'verdict_rules.epsilon': [0.05, 0.1]}))
        with self.assertRaises(RuntimeError) as refused:
            suite.amendments_check(suite.c_freeze(root), repo=root)
        self.assertIn('forbidden key', str(refused.exception))
        path = root / suite.AMENDMENTS_PATH
        entries = json.loads(path.read_text(encoding='utf-8'))
        entries['amendments'][-1]['seq'] = 9
        path.write_text(dumps(entries), encoding='utf-8')
        with self.assertRaises(RuntimeError) as second:
            suite.amendments_check(suite.c_freeze(root), repo=root)
        self.assertIn('not contiguous', str(second.exception))


class PlanTests(unittest.TestCase):
    def test_the_committed_plan_is_the_protocol_rebuilt_from_the_tree(self):
        plan = json.loads(PLAN.read_text(encoding='utf-8'))
        self.assertEqual(dumps(plan), dumps(suite.protocol()))
        self.assertEqual(plan['schema'], suite.SCHEMA)
        self.assertIs(plan['live_authorized'], False)
        self.assertEqual(plan['api_calls'], 0)
        self.assertEqual(plan['cny_spent'], '0.000000')
        self.assertEqual(plan['write_once']['outputs'], list(suite.WRITE_ONCE_OUTPUTS))
        self.assertEqual(plan['write_once']['frozen_at_gate0_plan'],
                         list(suite.FROZEN_AT_GATE0_PLAN))
        self.assertEqual(sorted(plan['code_sha256']), sorted(suite.CODE))
        self.assertEqual(sorted(plan['artifact_sha256']), sorted(suite.GATE0_ARTIFACTS))
        self.assertIs(plan['live_protocol']['re_verify_before_live'], True)
        self.assertEqual(plan['live_protocol']['status'], 'deferred_not_run')

    def test_freeze_plan_refuses_to_overwrite_an_existing_plan(self):
        before = PLAN.read_bytes()
        with self.assertRaises(FileExistsError):
            suite.freeze_plan(PLAN)
        self.assertEqual(PLAN.read_bytes(), before)

    def test_the_plan_pins_the_producing_modules_and_not_the_later_ones(self):
        """analysis.py and audit.py are written after the freeze, so the plan cannot pin them."""
        package = sorted(path.name for path in (REPO / 'faultda_bench/vericost565').glob('*.py'))
        pinned = sorted(Path(name).name for name in suite.CODE)
        self.assertEqual(sorted(set(package) - set(pinned)), ['analysis.py', 'audit.py'])


class OfflineEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = suite.evaluation(regimes=(costs.PRIMARY,), profiles=['syn-equal-n500'])

    def test_every_arm_is_evaluated_and_no_arm_beats_the_dp(self):
        self.assertEqual([row['arm'] for row in self.body['expected']], list(suite.ARMS))
        self.assertEqual(len(suite.ARMS), 13)
        for row in self.body['expected']:
            self.assertGreaterEqual(row['regret'], 0.0, row['arm'])
            # The history weights sum to 1 only up to float noise, which is kept, never clamped.
            self.assertLessEqual(row['expected_safe'], 1.0 + 1e-9, row['arm'])
        self.assertEqual(len(self.body['optimum']), 1)

    def test_three_frozen_episodes_per_cell_carry_the_dp_value_and_billed_bytes(self):
        self.assertEqual(len(self.body['realized']), 3 * len(suite.ARMS))
        for row in self.body['realized']:
            self.assertEqual(row['duplicate_events'], 0.0)
            self.assertGreaterEqual(row['billed_bytes'], 0)
            self.assertAlmostEqual(row['realized_regret'], row['dp_u'] - row['u'], places=12)
            self.assertLessEqual(row['decisions'], 6.0)

    def test_the_per_arm_counts_are_reported_separately_and_recomputable(self):
        counts = self.body['counts_by_arm']
        self.assertEqual(sorted(counts), sorted(suite.ARMS))
        for name, block in counts.items():
            self.assertEqual(block['episodes'], 3)
            self.assertEqual(sorted(block), sorted(suite.COUNTED + ('episodes',)))
            rows = [row for row in self.body['realized'] if row['arm'] == name]
            self.assertEqual(block['dominated_reads'],
                             sum(int(row['dominated_reads']) for row in rows))
        self.assertGreater(counts['guarded_read']['dominated_reads'], 0)

    def test_the_committed_evaluation_matches_the_plan_and_the_schema(self):
        if not suite.OFFLINE.exists():
            self.skipTest('offline_eval.json is produced by plan item 17')
        data = json.loads(suite.OFFLINE.read_text(encoding='utf-8'))
        plan = json.loads(PLAN.read_text(encoding='utf-8'))
        self.assertEqual(data['schema'], suite.OFFLINE_SCHEMA)
        self.assertEqual(data['split'], 'development')
        self.assertIs(data['seen_cluster'], True)
        self.assertIs(data['independent_test'], False)
        self.assertEqual(data['generalization_claim'], 'none')
        self.assertEqual(data['api_calls'], 0)
        self.assertEqual(data['cny_spent'], '0.000000')
        self.assertEqual(data['header']['plan_sha256'], sha(PLAN))
        self.assertEqual(data['header']['learned_sha256'], plan['learned_sha256'])
        self.assertEqual(data['header']['certificate_sha256'], plan['certificate_sha256'])
        self.assertEqual(data['header']['arms'], list(suite.ARMS))
        self.assertEqual(len(data['expected']), 30 * 8 * len(suite.ARMS))
        self.assertEqual(len(data['realized']), 30 * 3 * 8 * len(suite.ARMS))
        self.assertEqual(len(data['optimum']), 30 * 8)
        self.assertNotIn('head_commit', suite.comparable(data))


if __name__ == '__main__':
    unittest.main()
