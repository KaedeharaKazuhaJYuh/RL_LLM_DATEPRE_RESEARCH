"""Local DeepSeek LoRA conditional-recovery pilot with an exact 4-action policy.

The action distribution is the softmax of next-token logits for A/B/C/D.
It is NOT unconstrained JSON generation or end-to-end task planning.
"""
import argparse
import json
import random
import tempfile
import time
from pathlib import Path

from research.io import ROOT, digest, write_json
from research.v5_recovery_env import ACTIONS, RecoveryEnv, expert_action, prompt
from research.v5_recovery_protocol import PROTOCOL, load


def schedule(tasks, seed):
    by_family = {f: [t for t in tasks if t['split'] == 'train' and t['pair_family'] == f]
                 for f in range(3)}
    rng = random.Random(seed)
    for rows in by_family.values():
        rng.shuffle(rows)
    result = []
    for pair in range(8):
        task = by_family[pair % 3][pair // 3]
        modes = ('none', 'none') if pair in (0, 4) else ('before_commit', 'after_commit')
        for mode in modes:
            result.append((task, mode, bool(pair % 2), pair))
    return result


class Policy:
    def __init__(self, model_path, adapter):
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=False)
        self.model = PeftModel.from_pretrained(
            AutoModelForCausalLM.from_pretrained(model_path, dtype=torch.bfloat16,
                                                 trust_remote_code=False).cuda(),
            adapter, is_trainable=True)
        self.model.load_adapter(adapter, adapter_name='reference', is_trainable=False)
        self.model.set_adapter('default')
        self.model.eval()
        tokens = [self.tokenizer.encode(x, add_special_tokens=False) for x in 'ABCD']
        if any(len(x) != 1 for x in tokens) or len({x[0] for x in tokens}) != 4:
            raise ValueError('four unique single-token action labels required')
        self.labels = [x[0] for x in tokens]
        self.forward_tokens = 0

    def encode(self, observation):
        return self.tokenizer.apply_chat_template(
            [{'role': 'user', 'content': prompt(observation)}], tokenize=True,
            add_generation_prompt=True)['input_ids']

    def log_probs(self, ids, reference=False):
        torch = self.torch
        self.model.set_adapter('reference' if reference else 'default')
        self.model.eval()
        tensor = torch.tensor([ids], device='cuda')
        self.forward_tokens += len(ids)
        logits = self.model(input_ids=tensor, attention_mask=torch.ones_like(tensor),
                            use_cache=False).logits[0, -1, self.labels].float()
        return logits.log_softmax(-1)

    def act(self, observation, rng=None):
        ids = self.encode(observation)
        with self.torch.no_grad():
            lp = self.log_probs(ids).cpu()
        if rng is None:
            index = int(lp.argmax())
        else:
            u = rng.random()
            cumulative = 0.0
            index = 3
            for i, probability in enumerate(lp.exp().tolist()):
                cumulative += probability
                if u < cumulative:
                    index = i
                    break
        return index, {'ids': ids, 'action': index, 'old_log_probs': lp.tolist()}


def run(args):
    import torch
    out = Path(args.out)
    if out.exists():
        raise FileExistsError('new run directory required')
    tasks, oracle, manifest = load(args.protocol)
    if args.arm not in manifest['arms'] or args.seed not in manifest['seeds']:
        raise ValueError('run not in frozen protocol')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA required')
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    started = time.perf_counter()
    policy = Policy(args.model, args.adapter)
    optimizer = torch.optim.AdamW([p for p in policy.model.parameters() if p.requires_grad],
                                 lr=manifest['learning_rate'])
    records = []
    updates = 0
    budget = {'terminal_branches': 0, 'tool_calls': 0, 'inspections': 0,
              'decisions': 0, 'training_action_targets': 0}
    with tempfile.TemporaryDirectory(prefix='recovery_train_', dir=ROOT/'work') as temporary:
        scratch = Path(temporary)
        for group, (task, mode, reset, pair) in enumerate(schedule(tasks, args.seed)):
            env = RecoveryEnv(task, oracle[task['task_id']], scratch/f'root_{group}', mode)
            if reset and mode != 'none':
                env.step('inspect_commit')
            budget['tool_calls'] += env.calls
            budget['inspections'] += env.inspections
            budget['decisions'] += env.decisions
            frozen_hash = env.state_digest()
            trajectories, scores = [], []
            for member in range(4):
                branch = env.fork(scratch/f'branch_{group}_{member}')
                # Paired mode uses common uniforms across paired fault contexts;
                # each group's advantages still use ONLY its own observation.
                stream = pair if args.arm == 'paired' else group + 100
                rng = random.Random(args.seed * 10000 + stream * 100 + member)
                steps = []
                while not branch.done:
                    obs = branch.observation()
                    if args.arm == 'sft':
                        index = ACTIONS.index(expert_action(obs))
                        step = {'ids': policy.encode(obs), 'action': index}
                    else:
                        index, step = policy.act(obs, rng)
                        if not steps and args.arm in ('counterfactual', 'paired'):
                            index = member
                            step['action'] = index
                    steps.append(step)
                    branch.step(ACTIONS[index])
                score = branch.result()
                scores.append(score)
                trajectories.append(steps)
                budget['terminal_branches'] += 1
                budget['tool_calls'] += branch.calls - env.calls
                budget['inspections'] += branch.inspections - env.inspections
                budget['decisions'] += branch.decisions - env.decisions
            if env.state_digest() != frozen_hash:
                raise ValueError('branch contaminated shared root')
            rewards = torch.tensor([float(s['passed']) for s in scores], device='cuda')
            advantage = rewards - rewards.mean()
            if args.arm in ('grpo', 'branch') and rewards.std(unbiased=False) > 0:
                advantage = advantage / rewards.std(unbiased=False)
            train_steps = ([s for tr in trajectories for s in tr] if args.arm in ('sft', 'grpo')
                           else [tr[0] for tr in trajectories])
            do_update = args.arm == 'sft' or bool(torch.any(advantage))
            if do_update:
                for step in train_steps:
                    if args.arm != 'sft':
                        with torch.no_grad():
                            step['reference'] = policy.log_probs(step['ids'], reference=True).detach()
                policy.model.set_adapter('default')
                for _ in range(manifest['ppo_epochs']):
                    optimizer.zero_grad(set_to_none=True)
                    if args.arm in ('counterfactual', 'paired'):
                        first = trajectories[0][0]
                        lp = policy.log_probs(first['ids'])
                        # Enumeration, not sampled PPO: exact root expectation for
                        # sampled fixed-behavior continuation returns. Centering
                        # is a constant baseline and does not change the gradient.
                        ref = first['reference']
                        loss = -(lp.exp() * advantage).sum()
                        loss = loss + manifest['kl_beta'] * (lp.exp() * (lp-ref)).sum()
                        loss.backward()
                        budget['training_action_targets'] += 4
                    else:
                        n = len(train_steps)
                        for member, trajectory in enumerate(trajectories):
                            chosen = trajectory if args.arm in ('sft', 'grpo') else trajectory[:1]
                            for step in chosen:
                                lp = policy.log_probs(step['ids'])
                                action = step['action']
                                if args.arm == 'sft':
                                    loss = -lp[action]
                                else:
                                    old = step['old_log_probs'][action]
                                    ratio = (lp[action]-old).exp()
                                    loss = -torch.minimum(ratio * advantage[member],
                                                         ratio.clamp(.8, 1.2) * advantage[member])
                                    loss = loss + manifest['kl_beta'] * (
                                        lp.exp() * (lp-step['reference'])).sum()
                                (loss/n).backward()
                                budget['training_action_targets'] += 1
                    torch.nn.utils.clip_grad_norm_(policy.model.parameters(), 1.0)
                    optimizer.step()
                    updates += 1
            records.append({'group': group, 'pair': pair, 'task_id': task['task_id'],
                            'mode': mode, 'reset_after_inspection': reset,
                            'state_sha256': frozen_hash, 'scores': scores,
                            'updated': do_update,
                            'actions': [[ACTIONS[s['action']] for s in tr] for tr in trajectories]})
            print(f'{args.arm} seed={args.seed} group={group+1}/16 success={int(rewards.sum())}/4 updated={do_update}', flush=True)
    out.mkdir(parents=True)
    policy.model.set_adapter('default')
    policy.model.save_pretrained(out/'adapter', selected_adapters=['default'])
    summary = {'schema_version': 'v5-recovery-train-1', 'arm': args.arm, 'seed': args.seed,
               'protocol_sha256': digest(Path(args.protocol)/'manifest.json'),
               'model_sha256': digest(Path(args.model)/'model.safetensors'),
               'initial_adapter_sha256': digest(Path(args.adapter)/'adapter_model.safetensors'),
               'adapter_sha256': digest(out/'adapter/adapter_model.safetensors'),
               'optimizer_steps': updates, 'budget': budget,
               'forward_input_tokens': policy.forward_tokens,
               'elapsed_seconds': time.perf_counter()-started,
               'trainable_parameters': sum(p.numel() for p in policy.model.parameters() if p.requires_grad),
               'records': records}
    write_json(out/'summary.json', summary)
    return {k:v for k,v in summary.items() if k != 'records'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', default=str(PROTOCOL))
    parser.add_argument('--model', default='work/modelscope_deepseek_r1_1p5b')
    parser.add_argument('--adapter', required=True)
    parser.add_argument('--arm', required=True)
    parser.add_argument('--seed', required=True, type=int)
    parser.add_argument('--out', required=True)
    print(json.dumps(run(parser.parse_args()), ensure_ascii=False, indent=2))
