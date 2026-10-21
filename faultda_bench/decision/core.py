"""Public-only advice and privately scored semantic judgements."""
import copy
import math
from decimal import Decimal

from ..semantic.environment import SemanticEnv
from ..semantic.oracle import reference, record_correct, evaluate
from ..semantic.policies import choose

STATES = ('committed_correct', 'committed_wrong')
ARMS = ('raw', 'advice')


def prepare(task, folder, state):
    if state not in STATES:
        raise ValueError('unknown state')
    env = SemanticEnv(task, folder, commit_fault=False,
                      semantic_fault=state == 'committed_wrong', evidence='E0', budget=6)
    env.step('inspect')
    return env


def public_input(observation, arm):
    result = copy.deepcopy(observation)
    if arm == 'advice':
        result['optional_rule_advice'] = {
            'description': 'Deterministic public-data baseline suggestion. You may accept or reject it. '
                           'This is not an evaluator verdict; only your chosen action executes.',
            'decision': choose(copy.deepcopy(observation), 'task_semantic')}
    elif arm != 'raw':
        raise ValueError('unknown arm')
    return result


def judgement_reference(env):
    # Score the supplied inspection, not potentially changed hidden current state.
    inspection = [h['response'] for h in env.history if h['action'] == 'inspect' and h['response'].get('ok')][-1]
    version, values = reference(env.task)
    records = inspection['records']
    return {'expected_version': version, 'expected_output': {k: str(v) for k, v in values.items()},
            'observed_report_correct': len(records) == 1 and record_correct(records[0], env.task)}


def score_judgement(answer, expected):
    if not isinstance(answer, dict):
        return {'version': False, 'output': False, 'correctness': False, 'exact': False}
    output = answer.get('expected_output')
    numeric = isinstance(output, dict) and set(output) == set(expected['expected_output'])
    if numeric:
        for key, value in output.items():
            if type(value) not in (int, float) or not math.isfinite(value):
                numeric = False
                break
            target = Decimal(expected['expected_output'][key])
            if abs(Decimal(str(value)) - target) > max(Decimal('1e-9'), abs(target) * Decimal('1e-9')):
                numeric = False
                break
    result = {'version': answer.get('expected_version') == expected['expected_version'],
              'output': numeric,
              'correctness': type(answer.get('observed_report_correct')) is bool and
                             answer['observed_report_correct'] == expected['observed_report_correct']}
    result['exact'] = all(result.values()) and set(answer) == set(expected)
    return result


def transition(env, decision):
    before = evaluate(env)['terminal_correct']
    env.step(decision['action'], decision.get('params'))
    after = evaluate(env)['terminal_correct']
    return {'before_correct': before, 'after_correct': after,
            'regression': before and not after, 'repair': not before and after}
