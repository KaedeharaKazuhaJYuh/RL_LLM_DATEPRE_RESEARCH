"""Frozen greedy evaluation of a base or LoRA V4 decision model."""
import argparse
import json
import tempfile
from collections import defaultdict
from pathlib import Path

from agent.llm import parse_step
from experiments.v4_llm_export import input_text, model_input
from research.io import ROOT, digest, write_json
from research.stage_profile import StageProfile, scope
from research.v4_sequence_env import SequenceEnv


def choose(model, tokenizer, task, observation, max_new_tokens, profile=None):
    import torch
    message = [{'role': 'user', 'content': input_text(model_input(task, observation))}]
    prompt = tokenizer.apply_chat_template(message, tokenize=True, add_generation_prompt=True,
                                           return_tensors='pt')['input_ids'].to(model.device)
    if profile is not None:
        torch.cuda.synchronize()
    with scope(profile, 'model_generate'):
        with torch.inference_mode():
            generated = model.generate(prompt, max_new_tokens=max_new_tokens, do_sample=False,
                                       pad_token_id=tokenizer.eos_token_id)
        if profile is not None:
            torch.cuda.synchronize()
    response = tokenizer.decode(generated[0, prompt.shape[1]:], skip_special_tokens=True).strip()
    try:
        choice, _ = parse_step(response, task['allowed_tools'], fixed_bindings=True)
        return choice['action'], response, None
    except (ValueError, KeyError, TypeError) as exc:
        return None, response, type(exc).__name__


def run(args):
    if Path(args.out).exists():
        raise FileExistsError('new output file required')
    if getattr(args, 'profile_out', None) and Path(args.profile_out).exists():
        raise FileExistsError('new profile file required')
    profile = StageProfile() if getattr(args, 'profile_out', None) else None
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU required for this pilot')
    tasks = json.loads((Path(args.protocol) / 'tasks.json').read_text(encoding='utf-8'))
    dev = [x for x in tasks if x['split'] == 'dev']
    oracle = json.loads((Path(args.protocol) / 'dev_oracle.json').read_text(encoding='utf-8'))
    assert {x['task_id'] for x in dev} == set(oracle)
    if args.limit:
        dev = dev[:args.limit]
    with scope(profile, 'model_load'):
        tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.revision, trust_remote_code=False)
        model = AutoModelForCausalLM.from_pretrained(args.model, revision=args.revision, dtype=torch.bfloat16,
                                                      trust_remote_code=False).to('cuda').eval()
        if args.adapter:
            model = PeftModel.from_pretrained(model, args.adapter).eval()
    records = []
    with tempfile.TemporaryDirectory(prefix='v4_llm_eval_') as scratch:
        for task in dev:
            for fault in (False, True) if args.both_faults else (False,):
                env = SequenceEnv(task, oracle[task['task_id']], scratch, fault, profile=profile)
                steps = []
                while not env.done:
                    with scope(profile, 'observation'):
                        observation = env.observation()
                    action, raw, error = choose(model, tokenizer, task, observation,
                                                args.max_new_tokens, profile)
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
                records.append({'task_id': task['task_id'], 'source_id': task['source_id'],
                                'novelty': task['composition_novelty'], 'fault': fault,
                                'passed': scored['passed'], 'reward': scored['reward'],
                                'steps': steps})
    groups = defaultdict(list)
    for record in records:
        groups[f'{record["novelty"]}:{"fault" if record["fault"] else "clean"}'].append(record)
    summary = {'model': args.model, 'revision_requested': args.revision,
               'base_commit': getattr(model.config, '_commit_hash', None),
               'adapter': args.adapter, 'protocol_sha256': digest(Path(args.protocol) / 'manifest.json'),
               'episodes': len(records), 'passed': sum(r['passed'] for r in records),
               'slices': {k: {'n': len(v), 'passed': sum(x['passed'] for x in v)} for k, v in groups.items()},
               'greedy': True, 'external_test': False, 'records': records}
    write_json(args.out, summary)
    if profile is not None:
        profile.write(args.profile_out, operation='greedy_eval',
                      metadata={'protocol_sha256': summary['protocol_sha256'],
                                'episodes': len(records), 'model': args.model,
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
    parser.add_argument('--max-new-tokens', type=int, default=48)
    parser.add_argument('--profile-out')
    args = parser.parse_args()
    print(json.dumps(run(args), ensure_ascii=False, indent=2))
