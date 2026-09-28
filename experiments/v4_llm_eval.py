"""Frozen greedy evaluation of a base or LoRA V4 decision model."""
import argparse
import copy
import json
import tempfile
from collections import defaultdict
from pathlib import Path

from agent.llm import parse_step
from experiments.v4_llm_export import input_text, model_input
from research.io import ROOT, digest, write_json
from research.stage_profile import StageProfile, scope
from research.v4_sequence_env import SequenceEnv


def eligible_actions(task, observation, no_repeat_success=False):
    if not no_repeat_success:
        return task['allowed_tools']
    completed = {row['action'] for row in observation['history'] if row['ok']}
    return [action for action in task['allowed_tools'] if action not in completed]


def choose(model, tokenizer, task, observation, max_new_tokens, profile=None,
           allowed_actions=None):
    import torch
    message = [{'role': 'user', 'content': input_text(model_input(task, observation, allowed_actions))}]
    prompt = tokenizer.apply_chat_template(message, tokenize=True, add_generation_prompt=True,
                                           return_tensors='pt')['input_ids'].to(model.device)
    with scope(profile, 'model_generate'):
        with torch.inference_mode():
            generated = model.generate(prompt, max_new_tokens=max_new_tokens, do_sample=False,
                                       pad_token_id=tokenizer.eos_token_id)
    response = tokenizer.decode(generated[0, prompt.shape[1]:], skip_special_tokens=True).strip()
    try:
        choice, _ = parse_step(response, task['allowed_tools'] if allowed_actions is None
                               else allowed_actions, fixed_bindings=True)
        return choice['action'], response, None
    except (ValueError, KeyError, TypeError) as exc:
        return None, response, type(exc).__name__


def run(args):
    if Path(args.out).exists():
        raise FileExistsError('new output file required')
    if getattr(args, 'profile_out', None) and Path(args.profile_out).exists():
        raise FileExistsError('new profile file required')
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU required for this pilot')
    profile = StageProfile(synchronize=torch.cuda.synchronize) if getattr(args, 'profile_out', None) else None
    if profile is not None:
        torch.cuda.reset_peak_memory_stats()
    manifest = json.loads((Path(args.protocol) / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('frozen_model_weights_sha256') and (
            digest(Path(args.model) / 'model.safetensors') != manifest['frozen_model_weights_sha256']):
        raise ValueError('model weights differ from frozen protocol')
    if manifest.get('frozen_adapter_weights_sha256') and (
            not args.adapter or digest(Path(args.adapter) / 'adapter_model.safetensors') !=
            manifest['frozen_adapter_weights_sha256']):
        raise ValueError('adapter weights differ from frozen protocol')
    tasks = json.loads((Path(args.protocol) / 'tasks.json').read_text(encoding='utf-8'))
    dev = [x for x in tasks if x['split'] == 'dev']
    oracle = json.loads((Path(args.protocol) / 'dev_oracle.json').read_text(encoding='utf-8'))
    assert {x['task_id'] for x in dev} == set(oracle)
    if args.limit:
        dev = dev[:args.limit]
    requested_modes = getattr(args, 'fault_modes', None)
    if requested_modes:
        if args.both_faults:
            raise ValueError('--fault-modes and --both-faults are exclusive')
        modes = requested_modes.split(',')
        if (len(modes) != len(set(modes)) or
                any(mode not in ('none', 'transient_read', 'timeout', 'partial_write')
                    for mode in modes)):
            raise ValueError('invalid or duplicate fault mode')
        if any(not task.get('constraints', {}).get('isolated_tools') for task in dev):
            raise ValueError('fault modes require isolated tools')
    else:
        modes = ('none', 'transient_read') if args.both_faults else ('none',)
    with scope(profile, 'model_load'):
        tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.revision, trust_remote_code=False)
        model = AutoModelForCausalLM.from_pretrained(args.model, revision=args.revision, dtype=torch.bfloat16,
                                                      trust_remote_code=False).to('cuda').eval()
        if args.adapter:
            model = PeftModel.from_pretrained(model, args.adapter).eval()
    records = []
    with tempfile.TemporaryDirectory(prefix='v4_llm_eval_') as scratch:
        for task in dev:
            for mode in modes:
                env_task = copy.deepcopy(task) if mode in ('timeout', 'partial_write') else task
                if env_task is not task:
                    env_task['constraints']['tool_timeout_seconds'] = .15
                fault = mode != 'none'
                env = SequenceEnv(env_task, oracle[task['task_id']], scratch,
                                  fault=mode == 'transient_read', profile=profile,
                                  fault_mode=mode if mode in ('timeout', 'partial_write') else None)
                steps = []
                while not env.done:
                    with scope(profile, 'observation'):
                        observation = env.observation()
                    allowed = (eligible_actions(task, observation, True)
                               if getattr(args, 'no_repeat_success', False) else None)
                    action, raw, error = choose(model, tokenizer, task, observation,
                                                args.max_new_tokens, profile, allowed)
                    steps.append({'action': action, 'raw': raw, 'parse_error': error})
                    if error:
                        break
                    with scope(profile, 'environment_step'):
                        env.step(action)
                if env.done:
                    with scope(profile, 'environment_result'):
                        scored = env.result()
                else:
                    scored = {'passed': False, 'reward': 0.0}
                record = {'task_id': task['task_id'], 'source_id': task['source_id'],
                          'novelty': task['composition_novelty'], 'fault': fault,
                          'passed': scored['passed'], 'reward': scored['reward'],
                          'steps': steps}
                if task.get('constraints', {}).get('isolated_tools'):
                    record['tool_history'] = env.history
                if requested_modes:
                    record['fault_kind'] = mode
                    record['injection_applied'] = env.injected
                records.append(record)
    groups = defaultdict(list)
    for record in records:
        group_fault = record['fault_kind'] if requested_modes else ('fault' if record['fault'] else 'clean')
        groups[f'{record["novelty"]}:{group_fault}'].append(record)
    summary = {'model': args.model, 'revision_requested': args.revision,
               'base_commit': getattr(model.config, '_commit_hash', None),
               'adapter': args.adapter, 'protocol_sha256': digest(Path(args.protocol) / 'manifest.json'),
               'episodes': len(records), 'passed': sum(r['passed'] for r in records),
               'slices': {k: {'n': len(v), 'passed': sum(x['passed'] for x in v)} for k, v in groups.items()},
               'greedy': True, 'external_test': bool(manifest.get('external_test', False)), 'records': records}
    if getattr(args, 'no_repeat_success', False):
        summary['action_guard'] = 'exclude_successful_actions'
    if requested_modes:
        summary['fault_modes'] = list(modes)
    write_json(args.out, summary)
    if profile is not None:
        profile.write(args.profile_out, operation='greedy_eval',
                      metadata={'protocol_sha256': summary['protocol_sha256'],
                                'episodes': len(records), 'model': args.model,
                                'peak_cuda_allocated_bytes': torch.cuda.max_memory_allocated(),
                                'adapter': args.adapter})
    return {k: v for k, v in summary.items() if k != 'records'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', default=str(ROOT / 'tasks/v4/llm_pilot_v1'))
    parser.add_argument('--model', default='deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B')
    parser.add_argument('--revision', default='main')
    parser.add_argument('--adapter')
    parser.add_argument('--out', required=True)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--both-faults', action='store_true')
    parser.add_argument('--fault-modes',
                        help='comma-separated isolated modes: none,transient_read,timeout,partial_write')
    parser.add_argument('--max-new-tokens', type=int, default=48)
    parser.add_argument('--profile-out')
    parser.add_argument('--no-repeat-success', action='store_true',
                        help='diagnostic mask; exclude already successful actions')
    args = parser.parse_args()
    print(json.dumps(run(args), ensure_ascii=False, indent=2))
