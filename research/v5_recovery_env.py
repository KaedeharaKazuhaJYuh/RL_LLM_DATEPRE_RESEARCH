"""Conditional recovery after a known first operation, with real CSV artifacts.

The task's prefix and continuation are supplied by the benchmark, not learned.
Only inspect/retry/continue/abort decisions belong to the policy. Fault timing
is simulated at a transaction boundary; this is not a distributed crash test.
"""
import copy
import hashlib
import json
import shutil
from pathlib import Path

from agent.tools import execute_tool
from research.io import ROOT, digest, read_table, write_json, write_table
from research.oracle import expected
from research.v3_runtime import params_for
from verifier.score import _same, verify

ACTIONS = ('inspect_commit', 'retry', 'continue', 'abort')
MODES = ('none', 'before_commit', 'after_commit', 'partial_write')


class RecoveryEnv:
    def __init__(self, task, plan, folder, mode):
        if mode not in MODES or len(plan) != 2:
            raise ValueError('invalid recovery protocol')
        self.task, self.plan, self.mode = copy.deepcopy(task), list(plan), mode
        self.folder = Path(folder).resolve()
        self.folder.mkdir(parents=True, exist_ok=False)
        self.source = (ROOT / task['dataset']['uri']).resolve()
        if digest(self.source) != task['dataset']['sha256']:
            raise ValueError('source hash mismatch')
        self.current = self.source
        self.calls = self.decisions = self.commits = self.inspections = 0
        self.done = self.passed = False
        self.history = []
        self.known = 'unknown'
        self.answer = None
        if mode in ('none', 'after_commit'):
            self._commit()
        elif mode == 'partial_write':
            (self.folder / 'private_partial.csv').write_bytes(b'incomplete,header\n1,')
        if mode == 'none':
            self.known = 'committed'
        # Failure feedback deliberately identical across three fault modes.
        self.initial_feedback = ('operation acknowledged' if mode == 'none'
                                 else task.get('timeout_message', 'Timeout: outcome unknown'))

    def _execute(self, action):
        self.calls += 1
        params = params_for(action, self.task)
        before = digest(self.current)
        result = execute_tool(action, {'uri': str(self.current), 'params': params,
                                       'artifact_dir': self.folder / f'call_{self.calls}'})
        checked = verify(result, expected(self.current, action, params),
                         [{'tool': action, 'ok': True}],
                         {'allowed_tools': [action], 'input_sha256': before,
                          'max_tool_calls': 1, 'max_steps': 1})
        if not checked['passed']:
            raise ValueError('tool result verification failed')
        if 'artifact' in result:
            self.current = Path(result['artifact']['path']).resolve()
        return result

    def _commit(self):
        self._execute(self.plan[0])
        self.commits += 1
        write_json(self.folder / 'receipt.json', {
            'action': self.plan[0], 'input_sha256': self.task['dataset']['sha256'],
            'output': self.current.relative_to(self.folder).as_posix(),
            'output_sha256': digest(self.current), 'commits': self.commits})

    def observation(self):
        # No current-file metadata, fault label, count or privileged gold leaks.
        return {'request': self.task['prompt'], 'pending_operation': self.plan[0],
                'feedback': self.initial_feedback, 'commit_status': self.known,
                'history': list(self.history), 'remaining_decisions': 3 - self.decisions}

    def step(self, action):
        if self.done:
            raise RuntimeError('episode ended')
        if action not in ACTIONS:
            raise ValueError('invalid recovery action')
        self.decisions += 1
        if action == 'inspect_commit':
            self.inspections += 1
            path = self.folder / 'receipt.json'
            if path.exists():
                receipt = json.loads(path.read_text(encoding='utf-8'))
                output = (self.folder / receipt['output']).resolve()
                if (not output.is_relative_to(self.folder) or
                        receipt['input_sha256'] != self.task['dataset']['sha256'] or
                        receipt['action'] != self.plan[0] or
                        digest(output) != receipt['output_sha256'] or
                        receipt['commits'] != self.commits or output != self.current):
                    raise ValueError('invalid commit receipt')
                self.known = 'committed'
            elif self.commits:
                raise ValueError('missing commit receipt')
            else:
                self.known = 'absent'
        elif action == 'retry':
            self._commit()
            self.known = 'committed'
        elif action == 'continue':
            # Fixed suffix makes this a recovery test, not end-to-end planning.
            self.answer = self._execute(self.plan[1])['answer']
            first = expected(self.source, self.plan[0], params_for(self.plan[0], self.task))
            reference = self.folder / 'gold.csv'
            write_table(reference, first['artifact_columns'], first['artifact_rows'])
            final = expected(reference, self.plan[1], params_for(self.plan[1], self.task))
            cols, rows = read_table(self.current)
            self.passed = bool(self.commits == 1 and
                               digest(self.source) == self.task['dataset']['sha256'] and
                               cols == first['artifact_columns'] and
                               _same(rows, first['artifact_rows']) and
                               _same(self.answer, final['expected']))
            self.done = True
        else:
            self.done = True
        self.history.append({'action': action, 'commit_status': self.known})
        if self.decisions >= 3:
            self.done = True
        return self.observation()

    def result(self):
        if not self.done:
            raise RuntimeError('terminal scoring only')
        return {'passed': self.passed, 'reward': float(self.passed),
                'duplicate_commit': self.commits > 1, 'commits': self.commits,
                'tool_calls': self.calls, 'inspections': self.inspections,
                'decisions': self.decisions}

    def fork(self, folder):
        """Copy a frozen state into an independent artifact directory."""
        if self.done:
            raise ValueError('cannot fork terminal state')
        target = Path(folder).resolve()
        if target == self.folder or target.is_relative_to(self.folder):
            raise ValueError('fork must be outside parent state')
        shutil.copytree(self.folder, target)  # refuses an existing destination
        child = copy.copy(self)
        child.task = copy.deepcopy(self.task)
        child.history = copy.deepcopy(self.history)
        child.plan = list(self.plan)
        if self.current.is_relative_to(self.folder):
            child.current = target / self.current.relative_to(self.folder)
        child.folder = target
        if child.state_digest() != self.state_digest():
            raise ValueError('fork changed state')
        return child

    def state_digest(self):
        files = {p.relative_to(self.folder).as_posix(): digest(p)
                 for p in sorted(self.folder.rglob('*')) if p.is_file()}
        state = {'files': files, 'current': digest(self.current), 'mode': self.mode,
                 'task_id': self.task['task_id'], 'plan': self.plan,
                 'observation': self.observation(), 'commits': self.commits,
                 'calls': self.calls, 'inspections': self.inspections}
        return hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()


def expert_action(observation):
    return {'unknown': 'inspect_commit', 'absent': 'retry',
            'committed': 'continue'}[observation['commit_status']]


def prompt(observation):
    return ('Control recovery of a table operation. A timeout may occur before or after '
            'a durable commit. Repeating a committed operation violates exactly-once '
            'requirements. The continuation runs the remaining requested analysis. '
            'Choose one letter: A=inspect_commit, B=retry, C=continue, D=abort. '
            'Reply with one letter only.\n' + json.dumps(observation, ensure_ascii=False))
