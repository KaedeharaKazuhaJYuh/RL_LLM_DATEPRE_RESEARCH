"""Export verified expert state/action steps from training sources only."""
import argparse
import json
import tempfile
from pathlib import Path

from research.io import ROOT, append_jsonl, digest, write_json
from research.v4_sequence_env import SequenceEnv


SYSTEM = ('你是一个表格分析工具规划器。每次只选择一个动作，输出严格 JSON：'
          '{"action":"工具名"}。动作只能从 allowed_actions 中选择；'
          '参数由环境固定绑定。失败调用不会修改表，可重试。'
          '所有要求完成后选择 stop，不执行额外清理。')


def model_input(task, observation):
    return {'request': task['prompt'], 'columns': observation['columns'],
            'history': [{'action': h['action'], 'ok': h['ok'],
                         'error_type': h.get('error', '').split(':', 1)[0] if not h['ok'] else None}
                        for h in observation['history']],
            'remaining_calls': observation['remaining_calls'],
            'remaining_decisions': observation['remaining_decisions'],
            'allowed_actions': task['allowed_tools'] + ['stop']}


def input_text(sample):
    return SYSTEM + '\n当前状态：' + json.dumps(sample, ensure_ascii=False, separators=(',', ':'))


def replay(task, gold, folder, fault, collect):
    env = SequenceEnv(task, gold, folder, fault)
    steps = []
    while not env.done:
        observation = env.observation()
        completed = sum(h['ok'] for h in env.history)
        action = gold['plan'][completed] if completed < len(gold['plan']) else 'stop'
        if collect:
            steps.append({'task_id': task['task_id'], 'source_id': task['source_id'],
                          'pair_family': task['pair_family'], 'fault': fault,
                          'step': env.decisions, 'input': model_input(task, observation),
                          'action': action})
        env.step(action)
    result = env.result()
    if not result['passed']:
        raise AssertionError(f'expert replay failed: {task["task_id"]} fault={fault}')
    return steps


def run(protocol, out):
    protocol, out = Path(protocol), Path(out)
    if out.exists():
        raise FileExistsError('new output directory required')
    tasks = json.loads((protocol / 'tasks.json').read_text(encoding='utf-8'))
    train_oracle = json.loads((protocol / 'train_oracle.json').read_text(encoding='utf-8'))
    dev_oracle = json.loads((protocol / 'dev_oracle.json').read_text(encoding='utf-8'))
    manifest = json.loads((protocol / 'manifest.json').read_text(encoding='utf-8'))
    train = [t for t in tasks if t['split'] == 'train']
    dev = [t for t in tasks if t['split'] == 'dev']
    assert {t['task_id'] for t in train} == set(train_oracle)
    assert {t['task_id'] for t in dev} == set(dev_oracle)
    assert not {t['source_id'] for t in train} & {t['source_id'] for t in dev}
    out.mkdir(parents=True)
    count, episodes, dev_episodes = 0, 0, 0
    with tempfile.TemporaryDirectory(prefix='v4_llm_export_') as scratch:
        for task in train:
            for fault in (False, True):
                for step in replay(task, train_oracle[task['task_id']], scratch, fault, True):
                    append_jsonl(out / 'train_steps.jsonl', step)
                    count += 1
                episodes += 1
        for task in dev:
            for fault in (False, True):
                replay(task, dev_oracle[task['task_id']], scratch, fault, False)
                dev_episodes += 1
    summary = {'protocol': manifest['version'], 'train_tasks': len(train),
               'dev_tasks': len(dev), 'train_episodes': episodes, 'dev_expert_episodes': dev_episodes,
               'train_steps': count, 'training_sources': len({t['source_id'] for t in train}),
               'dev_sources': len({t['source_id'] for t in dev}),
               'train_steps_sha256': digest(out / 'train_steps.jsonl'),
               'dev_labels_used_for_training': False, 'external_test': False}
    write_json(out / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', default=str(ROOT / 'tasks/v4/llm_pilot_v1'))
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.protocol, args.out), ensure_ascii=False, indent=2))
