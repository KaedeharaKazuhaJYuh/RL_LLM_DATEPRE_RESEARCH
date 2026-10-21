"""Bounded DeepSeek development pilot; never sends evaluator labels or secrets in logs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import random
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from agent.deepseek_config import settings, credential_present
from . import VERSION
from .environment import SemanticEnv, TOOLS
from .oracle import evaluate
from .run import summarize
from .tasks import load, ROOT, MANIFEST, sha

SYSTEM = ('You operate a data-analysis report service. Complete the public contract using only legal tools. '
          'A timeout does not prove that a publication failed. A committed report may still have incorrect analysis. '
          'Use available evidence to decide whether to inspect, recompute and correct, or escalate. '
          'Return only a JSON object with action and params (an object, empty for read/stop/escalate). '
          'stage computes a candidate without publishing. publish requires stage_id, request_id, '
          'expected_revision and mode (replace or append). replace supersedes old reports atomically if revision matches. '
          'Repeated append can create duplicate reports. No filesystem access or code execution is available. '
          'Do not claim completion if unable to establish it. Do not exceed remaining budgets.')


class Client:
    def __init__(self, max_calls=96):
        if not credential_present():
            raise RuntimeError('DeepSeek credential not configured')
        config = settings()
        self.key = config['DEEPSEEK_API_KEY']
        self.model = config.get('DEEPSEEK_MODEL', 'deepseek-chat')
        self.calls, self.max_calls, self.lock = 0, max_calls, threading.Lock()

    def choose(self, observation):
        with self.lock:
            if self.calls >= self.max_calls:
                return None, {'error': 'pilot_call_cap'}
            self.calls += 1
        body = {'model': self.model, 'temperature': 0, 'max_tokens': 800,
                'response_format': {'type': 'json_object'},
                'messages': [{'role': 'system', 'content': SYSTEM},
                             {'role': 'user', 'content': json.dumps(observation, ensure_ascii=False)}]}
        request = urllib.request.Request('https://api.deepseek.com/chat/completions',
                                        data=json.dumps(body).encode(), method='POST',
                                        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.key})
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                answer = json.load(response)
            usage = {'usage': answer.get('usage', {}), 'response_id': answer.get('id'),
                     'model': answer.get('model'), 'seconds': time.perf_counter() - start}
            text = answer['choices'][0]['message']['content']
            try:
                choice = json.loads(text)
                if not isinstance(choice, dict) or not isinstance(choice.get('action'), str) or choice['action'] not in TOOLS:
                    raise ValueError('invalid action')
                if not isinstance(choice.get('params', {}), dict):
                    raise ValueError('invalid params')
                return choice, usage
            except (ValueError, TypeError):
                # Count invalid decisions without silently converting them to success.
                return {'action': 'invalid_model_output'}, {**usage, 'parse_error': True}
        except Exception as error:
            # Exception text can include remote data; record only class and HTTP status.
            return None, {'error': type(error).__name__, 'http_status': getattr(error, 'code', None),
                          'seconds': time.perf_counter() - start}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/semantic_v1_deepseek.json')
    parser.add_argument('--max-calls', type=int, default=96)
    args = parser.parse_args()
    if args.max_calls < 1 or args.max_calls > 96:
        parser.error('pilot max-calls must be between 1 and 96')
    client = Client(args.max_calls)
    # One instance per family, four paired conditions. This is API integration,
    # not a representative model comparison or the complete 12-instance suite.
    tasks = [t for t in load() if t['id'].endswith('-01')]
    jobs = [(t, c, s) for t in tasks for c in (False, True) for s in (False, True)]
    random.Random(20261009).shuffle(jobs)
    protocol = {'version': VERSION, 'track': 'single_model_integration_pilot', 'model': client.model,
                'temperature': 0, 'max_tokens': 800, 'max_calls': args.max_calls,
                'manifest_sha256': sha(MANIFEST), 'system': SYSTEM, 'evidence': 'E0', 'budget': 6,
                'deduplicate': False, 'concurrency': 3,
                'order': [{'task_id': t['id'], 'commit_fault': c, 'semantic_fault': s} for t, c, s in jobs],
                'code_sha256': {p.name: sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    protocol_file = args.output.with_suffix('.protocol.json')
    protocol_file.write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='faultda_api_') as temporary:
        def run(job):
            task, c, s = job
            env = SemanticEnv(task, Path(temporary) / f'{task["id"]}-{c}-{s}',
                              commit_fault=c, semantic_fault=s, evidence='E0', budget=6)
            calls = []
            while not env.terminal:
                choice, metadata = client.choose(env.observation())
                calls.append(metadata)
                if choice is None:
                    env.terminal = 'provider_error'
                else:
                    env.step(choice['action'], choice.get('params'))
            result = {'task_id': task['id'], 'source_id': task['source_id'], 'family': task['contract']['family'],
                      'policy': 'deepseek', 'commit_fault': c, 'semantic_fault': s,
                      'evidence': 'E0', 'budget': 6, 'deduplicate': False, **evaluate(env), 'api_calls': calls}
            print(json.dumps({'task': task['id'], 'C': c, 'S': s, 'terminal': env.terminal,
                              'complete': result['contract_complete'], 'calls': len(calls)}), flush=True)
            return result
        with ThreadPoolExecutor(max_workers=3) as pool:
            rows = list(pool.map(run, jobs))
    output = {'protocol': protocol_file.name, 'protocol_sha256': sha(protocol_file),
              'version': VERSION, 'calls': client.calls, 'summary': summarize(rows), 'episodes': rows,
              'limitation': '12 episodes, three historical instances, one provider; no RL, no significance claim'}
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
