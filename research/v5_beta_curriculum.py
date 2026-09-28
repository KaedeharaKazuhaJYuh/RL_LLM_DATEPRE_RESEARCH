"""Create train-only two-step RL curriculum from existing V4 synthetic sources."""
import copy
import hashlib
import json
from pathlib import Path

from research.io import ROOT, digest, write_json
from research.v4_real_protocol import PLANS, PROMPTS

VERSION = 'v5-beta-two-step-curriculum-1'
PARENT = ROOT / 'tasks/v4/llm_composition_v1'


def build(out=ROOT / 'tasks/v5/beta_curriculum_v1'):
    out = Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('new output directory inside repository required')
    parent_tasks = json.loads((PARENT / 'tasks.json').read_text(encoding='utf-8'))
    by_source = {}
    for task in parent_tasks:
        if task['split'] == 'train':
            by_source.setdefault(task['source_id'], task)
    if len(by_source) != 16:
        raise ValueError('expected 16 frozen training sources')
    tasks, oracle = [], {}
    for source_id, base in sorted(by_source.items()):
        params = base['params']
        names = {'value': params['column'], 'metric': params['other_column'],
                 'category': params['category_column']}
        for family, plan in enumerate(PLANS):
            for paraphrase, template in enumerate(PROMPTS[family]):
                task = copy.deepcopy(base)
                task_id = hashlib.sha256(
                    f'{VERSION}/{source_id}/{family}/{paraphrase}'.encode()).hexdigest()[:16]
                task.update(schema_version=VERSION, task_id=task_id,
                            pair_family=family, paraphrase_id=paraphrase,
                            composition_novelty='train_two_step',
                            prompt=template.format(**names),
                            constraints={'max_steps': 4, 'max_tool_calls': 3,
                                         'max_seconds': 120, 'isolated_tools': True,
                                         'tool_timeout_seconds': 10},
                            reward={'success': 1.0, 'progress': 1.0,
                                    'tool_call_cost': 0.02, 'decision_cost': 0.01})
                tasks.append(task)
                oracle[task_id] = {'plan': list(plan)}
    out.mkdir(parents=True)
    write_json(out / 'tasks.json', tasks)
    write_json(out / 'train_oracle.json', oracle)
    write_json(out / 'dev_oracle.json', {})
    manifest = {'version': VERSION, 'parent_manifest_sha256': digest(PARENT / 'manifest.json'),
                'synthetic': True, 'external_test': False,
                'train_sources': sorted(by_source), 'train_tasks': len(tasks),
                'dev_tasks': 0, 'train_only': True,
                'tasks_sha256': digest(out / 'tasks.json'),
                'train_oracle_sha256': digest(out / 'train_oracle.json'),
                'dev_oracle_sha256': digest(out / 'dev_oracle.json')}
    write_json(out / 'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    print(json.dumps(build(), ensure_ascii=False, indent=2))
