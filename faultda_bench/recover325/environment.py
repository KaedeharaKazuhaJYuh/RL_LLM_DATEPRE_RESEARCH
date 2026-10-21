"""Initial numeric fault with a healthy legal staging tool; mode stays private."""
import json
from ..semantic.environment import SemanticEnv
from ..pilot.contract import public_observation as old_observation


class RecoverableEnv(SemanticEnv):
    def __init__(self, task, folder, *, initial_numeric_fault=False, boundary='after_commit', repair_timeout='none'):
        self._initial_numeric_fault = initial_numeric_fault
        self._initializing = True
        if repair_timeout not in ('none', 'before_commit', 'after_commit'): raise ValueError('repair timeout')
        self._before_pending = repair_timeout == 'before_commit'
        self._before_raised = False
        super().__init__(task, folder, evidence='E1', budget=4, commit_fault=True,
                         semantic_fault=False, boundary=boundary, repair_ack_loss=repair_timeout == 'after_commit')
        self._initializing = False

    def _compute(self, params):
        record = super()._compute(params)
        if self._initializing and self._initial_numeric_fault:
            record['output'] = {k: v+1.0 for k, v in record['output'].items()}
        return record

    def _commit(self, record, request_id, expected_revision, mode, actor):
        if actor == 'agent' and self._before_pending:
            self._before_pending = False; self._before_raised = True
            raise TimeoutError('injected before commit')
        return super()._commit(record, request_id, expected_revision, mode, actor)

    def step(self, action, params=None):
        result = super().step(action, params)
        if self._before_raised:
            # The original executor already charged the exact attempted action
            # and caught the injected failure before any ledger/request write.
            self._before_raised = False
            old = self.history[-1]['response']; new = {'ok': False, 'error': 'timeout'}
            encode = lambda x: json.dumps(x, ensure_ascii=False, allow_nan=False).encode()
            self.cost['response_bytes'] += len(encode(new))-len(encode(old))
            self.history[-1]['response'] = new; result = self.observation()
        return result


def observation(env):
    result = old_observation(env)
    result['reliability_contract']['limits'] = (
        'Initial and corrective timeouts do not certify commitment. Writes may fail before commit '
        'or commit without acknowledgement. Reconcile the public ledger before retry or stop. '
        'Raw sources are immutable; source corruption and concurrent writers are excluded.')
    return result
