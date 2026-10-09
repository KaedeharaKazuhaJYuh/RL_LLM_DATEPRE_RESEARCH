"""Recompute published development summaries without network or model calls."""
import gzip
import json
import argparse
import tempfile
from pathlib import Path

from .environment import SemanticEnv
from .oracle import evaluate
from .run import summarize
from .tasks import ROOT, MANIFEST, sha, load


def verify(replay=False):
    report = ROOT / 'reports'
    offline = json.loads((report / 'semantic_v1_results.json').read_text(encoding='utf-8'))
    audit = report / offline['audit']['file']
    if sha(audit) != offline['audit']['sha256'] or sha(MANIFEST) != offline['manifest_sha256']:
        raise ValueError('offline artifact hash mismatch')
    rows = [json.loads(line) for line in gzip.decompress(audit.read_bytes()).decode().splitlines()]
    keys = [(r['task_id'], r['policy'], r['evidence'], r['budget'], r['deduplicate'], r['commit_fault'], r['semantic_fault']) for r in rows]
    if len(rows) != offline['audit']['episodes'] or len(set(keys)) != len(keys):
        raise ValueError('missing or duplicated offline episodes')
    if summarize(rows) != offline['summary']:
        raise ValueError('offline summary differs from trace aggregation')
    pilot = json.loads((report / 'semantic_v1_deepseek.json').read_text(encoding='utf-8'))
    protocol_path = report / pilot['protocol']
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    if sha(protocol_path) != pilot['protocol_sha256'] or protocol['manifest_sha256'] != sha(MANIFEST):
        raise ValueError('pilot protocol hash mismatch')
    if summarize(pilot['episodes']) != pilot['summary']:
        raise ValueError('pilot summary differs from trace aggregation')
    if len(pilot['episodes']) != len(protocol['order']):
        raise ValueError('pilot execution count mismatch')
    for artifact in (offline, protocol):
        for name, checksum in artifact['code_sha256'].items():
            if sha(Path(__file__).parent / name) != checksum:
                raise ValueError('implementation changed since run: ' + name)
    if replay:
        tasks = {t['id']: t for t in load()}
        with tempfile.TemporaryDirectory(prefix='faultda_replay_') as folder:
            for i, row in enumerate(rows + pilot['episodes']):
                env = SemanticEnv(tasks[row['task_id']], Path(folder) / str(i),
                                  **{k: row[k] for k in ('commit_fault', 'semantic_fault', 'evidence', 'budget', 'deduplicate')})
                for step in row['trace']:
                    env.step(step['action'], step['params'])
                    if env.history[-1]['response'] != step['response']:
                        raise ValueError(f'tool replay mismatch at episode {i}')
                if row['terminal'] == 'provider_error':
                    env.terminal = 'provider_error'
                for key, value in evaluate(env).items():
                    if row[key] != value:
                        raise ValueError(f'oracle replay mismatch: episode {i}, {key}')
    return {'offline_episodes': len(rows), 'pilot_episodes': len(pilot['episodes']), 'status': 'verified'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--replay', action='store_true', help='rebuild all environments and replay saved actions; no API calls')
    print(json.dumps(verify(parser.parse_args().replay)))
