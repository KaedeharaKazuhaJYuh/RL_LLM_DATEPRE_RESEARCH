"""Repeated precommit failure contrast, preserving the old frozen environment."""
from ..recover325.environment import RecoverableEnv, observation as prior_observation


class QualificationEnv(RecoverableEnv):
    def __init__(self, task, folder, *, before_failures=0, after_loss=False, check_budget=4):
        if type(before_failures) is not int or not 0 <= before_failures <= 2:
            raise ValueError('before failures')
        if type(after_loss) is not bool or (before_failures and after_loss):
            raise ValueError('exclusive fault profile')
        if type(check_budget) is not int or check_budget not in (3, 4, 5):
            raise ValueError('check budget')
        self._before_failures_remaining = before_failures
        super().__init__(task, folder, initial_numeric_fault=True,
                         repair_timeout='after_commit' if after_loss else 'none')
        self.budget = check_budget

    def _commit(self, record, request_id, expected_revision, mode, actor):
        if actor == 'agent' and self._before_failures_remaining:
            self._before_failures_remaining -= 1
            self._before_raised = True
            raise TimeoutError('injected repeated precommit failure')
        return super()._commit(record, request_id, expected_revision, mode, actor)


def observation(env):
    value = prior_observation(env)
    value['reliability_contract']['limits'] = (
        'Initial and corrective timeouts do not certify commitment. Precommit write failures '
        'can repeat; a retry is not guaranteed to succeed. A write can also commit without '
        'acknowledgement. Raw sources are immutable and concurrent writers are excluded. '
        'Use publicly observed evidence and respect budgets; no hidden fault count is available.')
    return value
