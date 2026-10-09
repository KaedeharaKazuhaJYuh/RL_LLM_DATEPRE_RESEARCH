"""Rules receive public observation only; no injected labels or evaluator state."""


def recovery_rule(observation):
    status = observation['knowledge']
    history = observation['history']
    if status == 'known_not_committed':
        return 'execute_tool'
    if status == 'known_committed':
        if history and history[-1]['action'] == 'inspect_artifact' and history[-1]['response']['ok']:
            return 'stop'
        return 'inspect_artifact'
    if history and history[-1]['action'] == 'query_operation_status':
        return 'inspect_artifact'
    if history and history[-1]['action'] == 'inspect_artifact':
        return 'escalate'
    return 'query_operation_status'


def blind_retry(observation):
    if not observation['initial_feedback']['ok'] and not observation['history']:
        return 'execute_tool'
    if not observation['history'] or observation['history'][-1]['action'] == 'execute_tool':
        return 'inspect_artifact'
    return 'stop'


def abstain_all(observation):
    return 'escalate'
