"""Small online GRPO/RL pilot for the V4 tool-use environment.

Rollouts are sampled from a trainable LoRA policy, executed by SequenceEnv,
and normalized against other rollouts for the same task. This is deliberately
small: it validates the online reward/update path before scaling up.
"""
import argparse
from collections import defaultdict
import json
import random
import tempfile
import time
from pathlib import Path

from agent.llm import parse_step
from experiments.v4_llm_export import input_text, model_input
from research.io import ROOT, digest, write_json
from research.v4_sequence_env import SequenceEnv


def select_train_tasks(tasks, limit, seed):
    """Select a seeded, pair-family-balanced training subset."""
    families = defaultdict(list)
    for task in tasks:
        if task['split'] == 'train':
            families[task['pair_family']].append(task)
    rng = random.Random(seed)
    for rows in families.values():
        rng.shuffle(rows)
    selected = []
    while len(selected) < limit and any(families.values()):
        for family in sorted(families):
            if families[family] and len(selected) < limit:
                selected.append(families[family].pop())
    return selected


class BudgetedGroupSchedule:
    """Fixed-budget static or on-policy family allocation; never reads dev tasks."""

    def __init__(self, tasks, seed, mode):
        if mode not in ('schedule_static', 'schedule_dynamic'):
            raise ValueError('invalid schedule mode')
        self.mode = mode
        self.rows = defaultdict(list)
        for task in tasks:
            if task['split'] == 'train':
                self.rows[task['pair_family']].append(task)
        if not self.rows:
            raise ValueError('no training families')
        rng = random.Random(seed)
        for rows in self.rows.values():
            rng.shuffle(rows)
        self.families = sorted(self.rows)
        rng.shuffle(self.families)
        self.position = 0
        self.streak = 0
        self.draws = defaultdict(int)
        self.groups = 0

    def next(self, previous_signal=False):
        if self.groups:
            if self.mode == 'schedule_dynamic' and previous_signal and self.streak < 2:
                self.streak += 1
            else:
                self.position = (self.position + 1) % len(self.families)
                self.streak = 1
        else:
            self.streak = 1
        family = self.families[self.position]
        rows = self.rows[family]
        task = rows[self.draws[family] % len(rows)]
        self.draws[family] += 1
        fault = bool(self.groups % 2)
        self.groups += 1
        return task, fault


def fault_conditions(mode):
    return {'clean': (False,), 'fault': (True,), 'both': (False, True)}[mode]


def count_passed(records):
    """Count terminal successes independently of shaped reward sign."""
    return sum(sum(record['passed']) for record in records)


def has_learning_signal(scores):
    """Ignore cost differences if outcome and correct prefix are identical."""
    return (len({bool(score.get('passed')) for score in scores}) > 1 or
            len({int(score.get('matched_prefix', 0)) for score in scores}) > 1)


def groups_from_scan(tasks, scan, *, seed, model, protocol_sha256, adapter_sha256,
                     group_size, temperature, max_new_tokens, limit):
    """Use only pre-scanned train groups with outcome or prefix variation."""
    if scan.get('schema_version') != 'v4-llm-signal-scan-1':
        raise ValueError('unsupported signal scan')
    checks = {'seed': seed, 'model': model, 'protocol_sha256': protocol_sha256,
              'adapter_sha256': adapter_sha256, 'group_size': group_size,
              'temperature': temperature, 'max_new_tokens': max_new_tokens}
    for key, expected in checks.items():
        if scan.get(key) != expected:
            raise ValueError(f'signal scan {key} mismatch')
    train = {task['task_id']: task for task in tasks if task['split'] == 'train'}
    selected = []
    for row in scan['records']:
        if row['signal'] not in ('outcome', 'prefix'):
            continue
        task = train.get(row['task_id'])
        if task is None or task['pair_family'] != row['pair_family']:
            raise ValueError('signal scan references an invalid training task')
        selected.append((task, bool(row['fault'])))
    if len(selected) != len(set((task['task_id'], fault) for task, fault in selected)):
        raise ValueError('signal scan has duplicate task-condition groups')
    return selected[:limit]


def generate_action(model, tokenizer, task, observation, temperature, max_new_tokens):
    import torch
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
    import torch
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
    import torch
    started = time.perf_counter()
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
    all_tasks = json.loads((Path(args.protocol) / 'tasks.json').read_text(encoding='utf-8'))
    oracle = json.loads((Path(args.protocol) / 'train_oracle.json').read_text(encoding='utf-8'))
    scan_sha256 = None
    schedule = None
    if args.sampling_mode != 'legacy':
        if args.signal_scan or args.updates != 1 or args.fault_mode != 'both':
            raise ValueError('budgeted schedule requires no scan, one update and both conditions')
        if args.episode_budget <= 0 or args.episode_budget % args.group_size:
            raise ValueError('episode budget must be positive and divisible by group size')
        schedule = BudgetedGroupSchedule(all_tasks, args.seed, args.sampling_mode)
        tasks, groups = [], []
        scheduled_groups = args.episode_budget // args.group_size
    elif args.signal_scan:
        scan_path = Path(args.signal_scan)
        scan = json.loads(scan_path.read_text(encoding='utf-8'))
        adapter_hash = {p.name: digest(p) for p in Path(args.adapter).glob('*.safetensors')}
        groups = groups_from_scan(
            all_tasks, scan, seed=args.seed, model=args.model,
            protocol_sha256=digest(Path(args.protocol) / 'manifest.json'),
            adapter_sha256=adapter_hash, group_size=args.group_size,
            temperature=args.temperature, max_new_tokens=args.max_new_tokens,
            limit=args.signal_limit)
        if not groups:
            raise ValueError('scan has no trainable signal groups')
        scan_sha256 = digest(scan_path)
        tasks = list(dict((task['task_id'], task) for task, _ in groups).values())
    else:
        tasks = select_train_tasks(all_tasks, args.limit, args.seed)
        groups = [(task, fault) for task in tasks for fault in fault_conditions(args.fault_mode)]
    if schedule is None:
        scheduled_groups = len(groups)
    records, losses, rewards, env_rewards, progresses, clip_fractions, ref_kls = [], [], [], [], [], [], []
    updated_groups = skipped_zero_advantage_groups = skipped_nonsemantic_groups = 0
    with tempfile.TemporaryDirectory(prefix='v4_grpo_') as scratch:
        for update in range(args.updates):
            previous_signal = False
            for group_index in range(scheduled_groups):
                task, fault = (schedule.next(previous_signal) if schedule else groups[group_index])
                # Normal and injected-fault rollouts remain separate groups.
                group = []
                for member in range(args.group_size):
                    episode_folder = (Path(scratch) /
                                      f'update_{update}_task_{task["task_id"]}_fault_{int(fault)}_member_{member}')
                    reward, trajectory, score = rollout(policy, tokenizer, task,
                                                        oracle[task['task_id']], episode_folder,
                                                        fault=fault, args=args)
                    if args.reward_mode == 'outcome':
                        reward = float(score.get('passed', False))
                    group.append((reward, trajectory, score))
                scores = [score for _, _, score in group]
                previous_signal = (len({bool(score.get('passed')) for score in scores}) > 1
                                   if args.reward_mode == 'outcome' else has_learning_signal(scores))
                values = torch.tensor([x[0] for x in group], dtype=torch.float32)
                if float(values.std(unbiased=False)) == 0:
                    advantages = torch.zeros_like(values)
                else:
                    advantages = (values - values.mean()) / (values.std(unbiased=False) + 1e-6)
                group_record = {'update': update, 'task_id': task['task_id'],
                                'pair_family': task['pair_family'], 'fault': fault,
                                'rewards': values.tolist(),
                                'environment_rewards': [float(x[2].get('reward', 0.0)) for x in group],
                                'task_signal': previous_signal,
                                'passed': [bool(x[2].get('passed')) for x in group],
                                'advantages': advantages.tolist(),
                                'members': [{'actions': [s['action'] for s in trajectory],
                                             'parse_error': bool(score.get('parse_error')),
                                             'tool_calls': score.get('tool_calls'),
                                             'decisions': score.get('decisions'),
                                             'matched_prefix': score.get('matched_prefix'),
                                             'progress': score.get('progress'),
                                             'extra_calls': score.get('extra_calls')}
                                            for _, trajectory, score in group]}
                rewards.extend(values.tolist())
                env_rewards.extend(float(score.get('reward', 0.0)) for _, _, score in group)
                progresses.extend(float(score.get('progress', 0.0)) for _, _, score in group)
                if not bool(torch.any(advantages)) or ((args.signal_scan or schedule)
                                                      and not previous_signal):
                    # Avoid Adam amplifying floating-point KL noise when a
                    # group contains no task-level relative learning signal.
                    group_record['updated'] = False
                    if bool(torch.any(advantages)):
                        skipped_nonsemantic_groups += 1
                    else:
                        skipped_zero_advantage_groups += 1
                    records.append(group_record)
                    print(f'group family={task["pair_family"]} fault={fault} updated=False', flush=True)
                    continue
                updated_groups += 1
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
                    # Backpropagate one decision at a time. Holding every
                    # trajectory graph until a single backward can exhaust
                    # laptop GPU memory when dynamic sampling finds long runs.
                    step_count = max(1, sum(len(x[1]) for x in group))
                    objective_value = 0.0
                    clip_count, token_count, kl_total = 0, 0, 0.0
                    for advantage, (_, trajectory, _), old_steps in zip(advantages, group, behavior):
                        for step, (old_lp, ref_lp) in zip(trajectory, old_steps):
                            new_lp = completion_logprobs(policy, step['prompt_ids'], step['completion_ids'])
                            ratio = torch.exp((new_lp - old_lp).clamp(-20, 20))
                            clipped = ratio.clamp(1.0 - args.clip_range, 1.0 + args.clip_range)
                            adv = advantage.to('cuda')
                            step_objective = -torch.minimum(ratio * adv, clipped * adv).mean()
                            # Non-negative sampled KL estimator, clipped against numerical overflow.
                            ref_diff = (ref_lp - new_lp).clamp(-20, 20)
                            kl = torch.exp(ref_diff) - ref_diff - 1.0
                            step_objective = step_objective + args.kl_beta * kl.mean()
                            objective_value += float(step_objective.detach().cpu()) / step_count
                            (step_objective / step_count).backward()
                            clip_count += int(((ratio < 1 - args.clip_range) |
                                               (ratio > 1 + args.clip_range)).sum().item())
                            token_count += ratio.numel()
                            kl_total += float(kl.detach().sum().cpu())
                    torch.nn.utils.clip_grad_norm_(policy.parameters(), 1.0)
                    optimizer.step()
                    losses.append(objective_value)
                    clip_fractions.append(clip_count / max(1, token_count))
                    ref_kls.append(kl_total / max(1, token_count))
                group_record['updated'] = True
                records.append(group_record)
                print(f'group family={task["pair_family"]} fault={fault} updated=True', flush=True)
    out = Path(args.out)
    out.mkdir(parents=True)
    adapter = out / 'adapter'
    policy.save_pretrained(adapter)
    tokenizer.save_pretrained(adapter)
    if schedule:
        tasks = list(dict((row['task_id'],
                           next(task for task in all_tasks if task['task_id'] == row['task_id']))
                          for row in records).values())
    summary = {'model': args.model, 'adapter_init': args.adapter, 'method': 'online-grpo-clipped-pilot',
               'seed': args.seed, 'updates': args.updates, 'tasks': len(tasks),
               'task_ids': [x['task_id'] for x in tasks],
               'pair_families': [x['pair_family'] for x in tasks],
               'selection_mode': (args.sampling_mode if schedule else
                                  'training_signal_scan' if scan_sha256 else 'seeded_family_balance'),
               'signal_scan_sha256': scan_sha256, 'selected_groups': scheduled_groups,
               'episode_budget': args.episode_budget if schedule else None,
               'reward_mode': args.reward_mode,
               'fault_mode': args.fault_mode, 'group_size': args.group_size,
               'ppo_epochs': args.ppo_epochs, 'episodes': len(rewards),
               'temperature': args.temperature, 'max_new_tokens': args.max_new_tokens,
               'learning_rate': args.learning_rate,
               'updated_groups': updated_groups,
               'skipped_zero_advantage_groups': skipped_zero_advantage_groups,
               'skipped_nonsemantic_groups': skipped_nonsemantic_groups,
               'episode_passed': count_passed(records),
               'reward_mean': sum(rewards) / max(1, len(rewards)),
               'environment_reward_mean': sum(env_rewards) / max(1, len(env_rewards)),
               'task_signal_groups': sum(bool(row['task_signal']) for row in records),
               'elapsed_seconds': time.perf_counter() - started,
               'progress_mean': sum(progresses) / max(1, len(progresses)),
               'full_prefix_episodes': sum(x == 1.0 for x in progresses),
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
    parser.add_argument('--fault-mode', choices=('clean', 'fault', 'both'), default='both')
    parser.add_argument('--temperature', type=float, default=.8)
    parser.add_argument('--max-new-tokens', type=int, default=48)
    parser.add_argument('--learning-rate', type=float, default=5e-6)
    parser.add_argument('--clip-range', type=float, default=.2)
    parser.add_argument('--kl-beta', type=float, default=.02)
    parser.add_argument('--seed', type=int, default=20260918)
    parser.add_argument('--signal-scan', help='completed train-only scan summary.json')
    parser.add_argument('--signal-limit', type=int, default=8)
    parser.add_argument('--sampling-mode', choices=('legacy', 'schedule_static', 'schedule_dynamic'),
                        default='legacy')
    parser.add_argument('--episode-budget', type=int, default=32)
    parser.add_argument('--reward-mode', choices=('shaped', 'outcome'), default='shaped')
    args = parser.parse_args()
    print(json.dumps(run(args), ensure_ascii=False, indent=2))
