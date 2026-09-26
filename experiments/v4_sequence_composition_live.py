"""Bounded DeepSeek development probe on the new unseen pair combinations."""
import argparse
import json
import time
from pathlib import Path

from agent.llm import LLMClient
from research.io import append_jsonl, write_json
from research.v4_sequence_env import SequenceEnv


def run(protocol, out, max_requests=48, temperature=0.0):
    protocol, out = Path(protocol), Path(out)
    if out.exists():
        raise FileExistsError('new output directory required')
    tasks = json.loads((protocol / 'tasks.json').read_text(encoding='utf-8'))
    gold = json.loads((protocol / 'oracle.json').read_text(encoding='utf-8'))
    if len(tasks) * 4 > max_requests:
        raise ValueError('request cap below worst-case clean evaluation')
    client = LLMClient()
    client.temperature = temperature
    out.mkdir(parents=True)
    usage = {'prompt_tokens': 0, 'completion_tokens': 0}
    records = []
    requests = 0
    for task in tasks:
        env = SequenceEnv(task, gold[task['task_id']], out / task['task_id'])
        started = time.perf_counter()
        error_type = None
        actions = []
        while not env.done:
            requests += 1
            observation = env.observation()
            try:
                decision = client.choose_step({**task, 'fixed_bindings': True}, observation, task['allowed_tools'])
                actions.append(decision['action'])
                env.step(decision['action'])
            except Exception as exc:
                error_type = type(exc).__name__
                env.decisions += 1
                env.done = True
            for key in usage:
                usage[key] += client.last_usage.get(key, 0)
            append_jsonl(out / 'requests.jsonl', {'task_id': task['task_id'], 'request': requests,
                'usage': dict(client.last_usage), 'response_id': client.last_response_id,
                'error_type': error_type, 'format_repaired': client.last_format_repaired})
        result = env.result()
        record = {'task_id': task['task_id'], 'source_id': task['source_id'],
                  'template_id': task['template_id'], 'actions': actions, 'error_type': error_type,
                  'wall_seconds': time.perf_counter() - started, **result}
        records.append(record)
        append_jsonl(out / 'episodes.jsonl', record)
        summary = {'protocol': 'v4-composition-dev-1', 'model': client.model,
                   'temperature': client.temperature, 'condition': 'clean only',
                   'request_cap': max_requests, 'requests': requests, 'usage': usage,
                   'episodes': len(records), 'passed': sum(r['passed'] for r in records),
                   'format_failures': sum(r['error_type'] in ('ValueError', 'JSONDecodeError') for r in records),
                   'mean_reward': sum(r['reward'] for r in records) / len(records), 'records': records}
        write_json(out / 'summary.json', summary)
        if error_type and error_type not in ('ValueError', 'JSONDecodeError'):
            raise RuntimeError('API connection or service failure; partial summary retained')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--max-requests', type=int, default=48)
    parser.add_argument('--temperature', type=float, default=0.0)
    args = parser.parse_args()
    result = run(args.protocol, args.out, args.max_requests, args.temperature)
    print(json.dumps({k: v for k, v in result.items() if k != 'records'}, ensure_ascii=False, indent=2))
