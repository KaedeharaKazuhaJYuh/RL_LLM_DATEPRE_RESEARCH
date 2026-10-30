"""Read the 60 committed 1.0.35 executions as one population and classify every terminal.

Nothing here calls a model, a scorer or an environment. It opens the archived packet,
checks its digest against the public record, and reports what the recorded runs did.
The point is that every earlier release of this line quoted these runs one cell at a
time; nobody had added up the failure column.
"""

import argparse
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / 'evidence/1.0.35/deepseek-planning-mechanism-1.0.35.zip'
RECORD = HERE / 'evidence/1.0.35/PUBLIC_RECORD.json'
OUTPUT = HERE / 'evidence/terminal-taxonomy-2026-10-27/TERMINAL_TAXONOMY.json'
READS = ('status', 'inspect', 'inputs', 'catalog')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load():
    """Every execution in the packet, after checking the packet is the one it claims to be."""
    record = json.loads(RECORD.read_text(encoding='utf-8'))
    require(digest(ARCHIVE) == record['sha256'], 'archive digest does not match the public record')
    with zipfile.ZipFile(ARCHIVE) as archive:
        names = sorted(name for name in archive.namelist() if name.endswith('/execution.json'))
        runs = [json.loads(archive.read(name)) for name in names]
    expected = record['model_trajectories'] + record['backend_rule_controls']
    require(len(runs) == expected, 'packet holds %d executions, record says %d' % (len(runs), expected))
    return runs


def executed(run):
    return [step['action'] for step in run['steps']]


def first_action(run):
    return run['decisions'][0]['proposal']['action'] if run['decisions'] else None


def cause(run):
    """One of completed, cap_after_publish, cap_without_publish, escalation."""
    facts = run['native_result']
    if facts['safe_complete']:
        return 'completed'
    if facts['terminal'] == 'budget_exceeded':
        return 'cap_after_publish' if 'publish' in executed(run) else 'cap_without_publish'
    if facts['terminal'] == 'escalate':
        return 'escalation'
    return 'other:' + str(facts['terminal'])


def row(run):
    facts = run['native_result']
    return {
        'arm': run['cell']['arm'],
        'condition': run['condition'],
        'task_id': run['task_id'],
        'primary_kind': run['primary_kind'],
        'checks_used': facts['cost']['checks'],
        'checks_cap': run['caps']['checks'],
        'first_action': first_action(run),
        'executed': executed(run),
        'unexecuted_decisions': run['cost'].get('unexecuted_decisions', 0),
        'terminal': facts['terminal'],
        'terminal_correct': facts['terminal_correct'],
        'safe_complete': facts['safe_complete'],
        'false_completion': facts['false_completion'],
        'agent_wrong_publications': facts['agent_wrong_publications'],
        'duplicate_events': facts['duplicate_events'],
        'forbidden_effect': facts['forbidden_effect'],
        'source_intact': facts['source_intact'],
        'cause': cause(run),
    }


def population(runs):
    rows = [row(run) for run in runs]
    failures = [item for item in rows if not item['safe_complete']]
    model = [item for item in rows if item['primary_kind'] == 'model_api']
    rule = [item for item in rows if item['primary_kind'] != 'model_api']
    return {
        'schema': 'reliability_reset.terminal_taxonomy/1',
        'record': 'terminal-taxonomy-2026-10-27',
        'source': 'evidence/1.0.35/deepseek-planning-mechanism-1.0.35.zip',
        'source_sha256': digest(ARCHIVE),
        'api_calls': 0,
        'executions': len(rows),
        'model_executions': len(model),
        'rule_executions': len(rule),
        'terminals': dict(sorted(Counter(item['terminal'] for item in rows).items())),
        'causes': dict(sorted(Counter(item['cause'] for item in rows).items())),
        'checks_used': {str(key): value for key, value in sorted(
            Counter(item['checks_used'] for item in rows).items())},
        'checks_cap': {str(key): value for key, value in sorted(
            Counter(item['checks_cap'] for item in rows).items())},
        'first_actions': dict(sorted(Counter(item['first_action'] for item in rows).items())),
        'safe_complete': sum(item['safe_complete'] for item in rows),
        'terminal_correct': sum(item['terminal_correct'] for item in rows),
        'false_completion': sum(item['false_completion'] for item in rows),
        'agent_wrong_publications': sum(item['agent_wrong_publications'] for item in rows),
        'duplicate_events': sum(item['duplicate_events'] for item in rows),
        'forbidden_effect': sum(bool(item['forbidden_effect']) for item in rows),
        'source_intact': sum(item['source_intact'] for item in rows),
        'failures': len(failures),
        'failures_with_correct_record': sum(item['terminal_correct'] for item in failures),
        'failures_with_one_unexecuted_decision': sum(
            item['unexecuted_decisions'] == 1 for item in failures),
        'model_safe_complete': sum(item['safe_complete'] for item in model),
        'model_terminal_correct': sum(item['terminal_correct'] for item in model),
        'rule_safe_complete': sum(item['safe_complete'] for item in rule),
        'rule_terminal_correct': sum(item['terminal_correct'] for item in rule),
        'cap_first_action': dict(sorted(Counter(
            item['first_action'] for item in rows if item['cause'].startswith('cap_')).items())),
        'cap_after_publish_by_condition': dict(sorted(Counter(
            item['condition'] for item in rows
            if item['cause'] == 'cap_after_publish').items())),
        'rows': rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = population(load())
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True) + '\n')
    head = {key: value for key, value in result.items() if key != 'rows'}
    print(json.dumps(head, ensure_ascii=False, indent=1, sort_keys=True))


if __name__ == '__main__':
    main()
