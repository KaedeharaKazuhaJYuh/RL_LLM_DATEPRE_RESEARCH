"""Crossed-source matrix with per-source/intent reporting and frozen evidence."""
import argparse
import gzip
import itertools
import json
from pathlib import Path
import tempfile

from ..semantic.policies import POLICIES
from ..semantic.run import episode, summarize
from ..semantic.tasks import REPO, sha
from . import VERSION
from .tasks import MANIFEST, load, write_json, code_hashes


def summaries(rows):
    return {'overall': summarize(rows), 'by_source_intent': [
        {'source_id': source, 'family': family,
         'summary': summarize([r for r in rows if r['source_id'] == source and r['family'] == family])}
        for source in sorted({r['source_id'] for r in rows}) for family in ('group', 'version')]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=REPO / 'work/cross_source_v2_results.json')
    args = parser.parse_args()
    audit = args.output.with_suffix('.jsonl.gz')
    protocol = args.output.with_suffix('.protocol.json')
    if any(p.exists() for p in (args.output, audit, protocol)):
        parser.error('output already exists; select a new path to preserve earlier evidence')
    plan = {'version': VERSION, 'manifest_sha256': sha(MANIFEST), 'code_sha256': code_hashes(),
            'policies': list(POLICIES), 'evidence': ['E0', 'E1'], 'budgets': [2, 4],
            'deduplicate': False, 'task_ids': [t['id'] for t in load()],
            'conditions': [[False, False], [False, True], [True, False], [True, True]],
            'scope': 'crossed historical development; no causal source-generalization claim'}
    write_json(protocol, plan)
    rows = []
    with tempfile.TemporaryDirectory(prefix='faultda_crossed_') as temporary:
        for task, policy, evidence, budget, c, s in itertools.product(
                load(), POLICIES, ('E0', 'E1'), (2, 4), (False, True), (False, True)):
            rows.append(episode(task, Path(temporary) / str(len(rows)), policy,
                                evidence=evidence, budget=budget, deduplicate=False, commit_fault=c, semantic_fault=s))
    with audit.open('xb') as stream:
        stream.write(gzip.compress(('\n'.join(json.dumps(r, ensure_ascii=False, allow_nan=False) for r in rows) + '\n').encode(), mtime=0))
    write_json(args.output, {'version': VERSION, 'protocol': protocol.name, 'protocol_sha256': sha(protocol),
                             'audit': {'file': audit.name, 'sha256': sha(audit), 'episodes': len(rows)},
                             'summaries': summaries(rows)})
    print(json.dumps({'episodes': len(rows), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
