"""Small online GRPO/RL pilot for the V4 tool-use environment.

Rollouts are sampled from a trainable LoRA policy, executed by SequenceEnv,
and normalized against other rollouts for the same task. This is deliberately
small: it validates the online reward/update path before scaling up.
"""
import argparse
import json
import random
import tempfile
from pathlib import Path

import torch

from agent.llm import parse_step
from experiments.v4_llm_export import input_text, model_input
from research.io import ROOT, digest, write_json
from research.v4_sequence_env import SequenceEnv


def generate_action(model, tokenizer, task, observation, temperature, max_new_tokens):
    message = [{'role': 'user', 'content': input_text(model_input(task, observation))}]
    encoded = tokenizer.apply_chat_template(message, tokenize=True, add_generation_prompt=True,
                                            return_tensors='pt')['input_ids'].to(model.device)
    with torch.no_grad():
        generated = model.generate(encoded, max_new_tokens=max_new_tokens, do_sample=True,
                                   temperature=temperature, top_p=.95,
                                   pad_token_id=tokenizer.eos_token_id)
    completion = generated[0, encoded.shape[1]:]
    raw = tokenizer.decode(completion, skip_special_tokens=True).strip()
    try:
        choice, _ = parse_step(raw, task['allowed_tools'], fixed_bindings=True)
        return choice['action'], raw, completion.detach().cpu().tolist()
    except (ValueError, KeyError, TypeError):
        return None, raw, completion.detach().cpu().tolist()


def completion_logprobs(model, prompt_ids, completion_ids):
    ids = torch.tensor([prompt_ids + completion_ids], device=model.device)
    logits = model(input_ids=ids, attention_mask=torch.ones_like(ids)).logits[:, :-1]
    target = ids[:, 1:]
    logp = torch.log_softmax(logits.float(), dim=-1).gather(-1, target.unsqueeze(-1)).squeeze(-1)
    start = max(0, len(prompt_ids) - 1)
    return logp[:, start:]


def rollout(model, tokenizer, task, gold, scratch, fault, args):
    env = SequenceEnv(task, gold, scratch, fault=fault)
    actions = []
    while not env.done:
        observation = env.observation()
        message = [{'role': 'user', 'content': input_text(model_input(task, observation))}]
        prompt_ids = tokenizer.apply_chat_template(message, tokenize=True,
                                                    add_generation_prompt=True)['input_ids']
        action, raw, completion = generate_action(model, tokenizer, task, observation,
                                                   args.temperature, args.max_new_tokens)
        actions.append({'prompt_ids': prompt_ids, 'completion_ids': completion,
                        'action': action, 'raw': raw})
        if action is None:
            return 0.0, actions, {'passed': False, 'parse_error': True}
        env.step(action)
    score = env.result()
    return float(score['reward']), actions, score


def run(args):
    if Path(args.out).exists():
        raise FileExistsError('new output directory required')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU required for this pilot')
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    if not args.adapter:
        raise ValueError('--adapter is required so the pilot starts from SFT/DPO')
    policy = PeftModel.from_pretrained(
        AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16,
                                             trust_remote_code=False).cuda(),
        args.adapter, is_trainable=True)
    # Keep a frozen copy of the starting SFT/DPO adapter on the shared base model.
    policy.load_adapter(args.adapter, adapter_name='reference', is_trainable=False)
    # Keep the policy in eval mode so rollout, old-policy, reference, and update
    # log probabilities use the same deterministic network (sampling remains
    # stochastic through generate(do_sample=True)). Gradients still flow.
    policy.eval()
    optimizer = torch.optim.AdamW((p for p in policy.parameters() if p.requires_grad), lr=args.learning_rate)
    tasks = json.loads((Path(args.protocol) / 'tasks.json').read_text(encoding='utf-8'))
    oracle = json.loads((Path(args.protocol) / 'train_oracle.json').read_text(encoding='utf-8'))
    tasks = [t for t in tasks if t['split'] == 'train'][:args.limit]
    records, losses, rewards, clip_fractions, ref_kls = [], [], [], [], []
    with tempfile.TemporaryDirectory(prefix='v4_grpo_') as scratch:
        for update in range(args.updates):
            for task in tasks:
                group = []
                for member in range(args.group_size):
                    episode_folder = Path(scratch) / f'update_{update}_task_{task["task_id"]}_member_{member}'
                    reward, trajectory, score = rollout(policy, tokenizer, task,
                                                        oracle[task['task_id']], episode_folder,
                                                        fault=bool(member % 2), args=args)
                    group.append((reward, trajectory, score))
                values = torch.tensor([x[0] for x in group], dtype=torch.float32)
                if float(values.std(unbiased=False)) == 0:
                    advantages = torch.zeros_like(values)
                else:
                    advantages = (values - values.mean()) / (values.std(unbiased=False) + 1e-6)
                # Snapshot behavior-policy and reference token log probabilities before update.
                behavior = []
                with torch.no_grad():
                    policy.set_adapter('default')
                    policy.eval()
                    for _, trajectory, _ in group:
                        seq = []
                        for step in trajectory:
                            old_lp = completion_logprobs(policy, step['prompt_ids'], step['completion_ids'])
                            policy.set_adapter('reference')
                            policy.eval()
                            ref_lp = completion_logprobs(policy, step['prompt_ids'], step['completion_ids'])
                            policy.set_adapter('default')
                            policy.eval()
                            seq.append((old_lp.detach(), ref_lp.detach()))
                        behavior.append(seq)
                for _ppo_epoch in range(args.ppo_epochs):
                    optimizer.zero_grad(set_to_none=True)
                    objective = torch.zeros((), device='cuda')
                    clip_count, token_count, kl_total = 0, 0, 0.0
                    for advantage, (_, trajectory, _), old_steps in zip(advantages, group, behavior):
                        for step, (old_lp, ref_lp) in zip(trajectory, old_steps):
                            new_lp = completion_logprobs(policy, step['prompt_ids'], step['completion_ids'])
                            ratio = torch.exp((new_lp - old_lp).clamp(-20, 20))
                            clipped = ratio.clamp(1.0 - args.clip_range, 1.0 + args.clip_range)
                            adv = advantage.to('cuda')
                            objective = objective - torch.minimum(ratio * adv, clipped * adv).mean()
                            # Non-negative sampled KL estimator, clipped against numerical overflow.
                            ref_diff = (ref_lp - new_lp).clamp(-20, 20)
                            kl = torch.exp(ref_diff) - ref_diff - 1.0
                            objective = objective + args.kl_beta * kl.mean()
                            clip_count += int(((ratio < 1 - args.clip_range) | (ratio > 1 + args.clip_range)).sum().item())
                            token_count += ratio.numel()
                            kl_total += float(kl.detach().mean().cpu())
                    objective = objective / max(1, sum(len(x[1]) for x in group))
                    objective.backward()
                    torch.nn.utils.clip_grad_norm_(policy.parameters(), 1.0)
                    optimizer.step()
                    losses.append(float(objective.detach().cpu()))
                    clip_fractions.append(clip_count / max(1, token_count))
                    ref_kls.append(kl_total / max(1, token_count))
                rewards.extend(values.tolist())
                records.append({'update': update, 'task_id': task['task_id'],
                                'rewards': values.tolist(), 'passed': [bool(x[2].get('passed')) for x in group],
                                'advantages': advantages.tolist()})
    out = Path(args.out)
    out.mkdir(parents=True)
    adapter = out / 'adapter'
    policy.save_pretrained(adapter)
    tokenizer.save_pretrained(adapter)
    summary = {'model': args.model, 'adapter_init': args.adapter, 'method': 'online-grpo-clipped-pilot',
               'seed': args.seed, 'updates': args.updates, 'tasks': len(tasks),
               'group_size': args.group_size, 'ppo_epochs': args.ppo_epochs, 'episodes': len(rewards),
               'episode_passed': sum(x > 0 for x in rewards), 'reward_mean': sum(rewards) / max(1, len(rewards)),
               'loss_first': losses[0] if losses else None, 'loss_last': losses[-1] if losses else None,
               'clip_range': args.clip_range, 'kl_beta': args.kl_beta,
               'clip_fraction_mean': sum(clip_fractions) / max(1, len(clip_fractions)),
               'reference_kl_mean': sum(ref_kls) / max(1, len(ref_kls)),
               'protocol_sha256': digest(Path(args.protocol) / 'manifest.json'),
               'trainable_parameters': sum(p.numel() for p in policy.parameters() if p.requires_grad),
               'adapter_sha256': {p.name: digest(p) for p in adapter.glob('*.safetensors')},
               'external_test': False, 'records': records}
    write_json(out / 'summary.json', summary)
    return {k: v for k, v in summary.items() if k != 'records'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', default=str(ROOT / 'tasks/v4/llm_pilot_v1'))
    parser.add_argument('--model', default='work/modelscope_deepseek_r1_1p5b')
    parser.add_argument('--adapter', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--limit', type=int, default=2)
    parser.add_argument('--updates', type=int, default=2)
    parser.add_argument('--group-size', type=int, default=2)
    parser.add_argument('--ppo-epochs', type=int, default=2)
    parser.add_argument('--temperature', type=float, default=.8)
    parser.add_argument('--max-new-tokens', type=int, default=48)
    parser.add_argument('--learning-rate', type=float, default=5e-6)
    parser.add_argument('--clip-range', type=float, default=.2)
    parser.add_argument('--kl-beta', type=float, default=.02)
    parser.add_argument('--seed', type=int, default=20260918)
    args = parser.parse_args()
    print(json.dumps(run(args), ensure_ascii=False, indent=2))
