"""Post-run evidence-use diagnosis; does not change scores or call a model."""
import argparse
import json
from pathlib import Path
import tempfile

from ..semantic.environment import SemanticEnv
from ..semantic.oracle import record_correct
from ..semantic.tasks import REPO, load as load_v1, sha
from .tasks import clarify, write_json
from .verify import verify


def diagnose(report):
    verify(report)
    rows = json.loads(Path(report).read_text(encoding='utf-8'))['episodes']
    tasks = {t['id']: t for t in load_v1()}
    result = {}
    with tempfile.TemporaryDirectory(prefix='faultda_evidence_audit_') as temporary:
        for arm in ('original', 'explicit'):
            stats = {'escalated': 0, 'correct_terminal': 0, 'has_correct_stage': 0,
                     'wrong_terminal_with_correct_stage': 0, 'episodes': []}
            for index, row in enumerate(rows):
                if row['arm'] != arm or row['terminal'] != 'escalate':
                    continue
                task = tasks[row['task_id']]
                if arm == 'explicit':
                    task = clarify(task)
                env = SemanticEnv(task, Path(temporary) / str(index))
                stage = any(h['action'] == 'stage' and h['response'].get('ok') and
                            record_correct(h['response'], env.task) for h in row['trace'])
                stats['escalated'] += 1
                stats['correct_terminal'] += row['terminal_correct']
                stats['has_correct_stage'] += stage
                stats['wrong_terminal_with_correct_stage'] += stage and not row['terminal_correct']
                stats['episodes'].append({'order_index': row['order_index'], 'task_id': row['task_id'],
                                          'correct_terminal': row['terminal_correct'], 'correct_stage_observed': stage})
            result[arm] = stats
    return {'input_report_sha256': sha(report), 'derivation_code_sha256': sha(__file__),
            'scope': 'post-hoc diagnostic, no claim about model internal reasoning or causal mechanism',
            'arms': result}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    parser.add_argument('--output', type=Path, default=REPO / 'work/clarity_evidence_diagnosis.json')
    args = parser.parse_args()
    write_json(args.output, diagnose(args.report))
