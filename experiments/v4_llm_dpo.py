"""Action-level DPO pilot using the verified V4 environment trajectories.

The preferred completion is the expert next action. Rejected completions are
early stop and an incorrect allowed action, so the objective directly targets
the observed unseen-composition failure mode.
"""
import argparse
import json
import random
from pathlib import Path

from agent.tools import ACTIONS
from experiments.v4_llm_export import input_text
from research.io import digest, write_json


def pairs(path, tokenizer, max_length):
    rows = [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line]
    out = []
    for row in rows:
        preferred = row['action']
        rejected = ['stop' if preferred != 'stop' else ACTIONS[0]]
        rejected += [a for a in ACTIONS if a != preferred][:1]
        messages = [{'role': 'user', 'content': input_text(row['input'])}]
        prompt = tokenizer.apply_chat_template(messages, tokenize=True,
                                                add_generation_prompt=True)['input_ids']
        for bad in rejected:
            chosen = tokenizer.encode(json.dumps({'action': preferred}, ensure_ascii=False,
                                                 separators=(',', ':')) + tokenizer.eos_token,
                                     add_special_tokens=False)
            refused = tokenizer.encode(json.dumps({'action': bad}, ensure_ascii=False,
                                                 separators=(',', ':')) + tokenizer.eos_token,
                                     add_special_tokens=False)
            if max(len(prompt) + len(chosen), len(prompt) + len(refused)) > max_length:
                raise ValueError(f'example exceeds max_length: {row["task_id"]}')
            out.append({'prompt': prompt, 'chosen': chosen, 'rejected': refused,
                        'source_id': row['source_id'], 'task_id': row['task_id'],
                        'preferred': preferred, 'rejected_action': bad})
    return rows, out


def sequence_logprob(model, input_ids, labels):
    import torch
    logits = model(input_ids=input_ids, attention_mask=torch.ones_like(input_ids)).logits[:, :-1]
    target = labels[:, 1:]
    mask = target.ne(-100)
    token_logp = torch.log_softmax(logits, dim=-1).gather(-1, target.clamp_min(0).unsqueeze(-1)).squeeze(-1)
    return (token_logp.float() * mask).sum(-1) / mask.sum(-1).clamp_min(1)


def run(args):
    if Path(args.out).exists():
        raise FileExistsError('new output directory required')
    import torch
    from peft import LoraConfig, PeftModel, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU required for this pilot')
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    rows, data = pairs(args.steps, tokenizer, args.max_length)
    base = AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16,
                                                trust_remote_code=False).cuda()
    if args.init_adapter:
        base = PeftModel.from_pretrained(base, args.init_adapter).cuda().eval()
        policy = PeftModel.from_pretrained(
            AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16,
                                                 trust_remote_code=False).cuda(),
            args.init_adapter, is_trainable=True).cuda()
    else:
        base = base.eval()
        policy = get_peft_model(AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16,
                                                                      trust_remote_code=False).cuda(),
                                LoraConfig(r=8, lora_alpha=16, lora_dropout=.05,
                                           target_modules='all-linear', bias='none', task_type='CAUSAL_LM'))
    policy.train()
    optimizer = torch.optim.AdamW((p for p in policy.parameters() if p.requires_grad), lr=args.learning_rate)
    beta = args.beta
    losses = []
    for step in range(args.max_steps):
        item = data[step % len(data)]
        chosen = item['prompt'] + item['chosen']
        rejected = item['prompt'] + item['rejected']
        cids = torch.tensor([chosen], device='cuda')
        rids = torch.tensor([rejected], device='cuda')
        clabel = torch.tensor([[-100] * len(item['prompt']) + item['chosen']], device='cuda')
        rlabel = torch.tensor([[-100] * len(item['prompt']) + item['rejected']], device='cuda')
        pi_c = sequence_logprob(policy, cids, clabel)
        pi_r = sequence_logprob(policy, rids, rlabel)
        with torch.no_grad():
            ref_c = sequence_logprob(base, cids, clabel)
            ref_r = sequence_logprob(base, rids, rlabel)
        loss = -torch.nn.functional.logsigmoid(beta * ((pi_c - pi_r) - (ref_c - ref_r))).mean()
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(policy.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.detach().cpu()))
    out = Path(args.out)
    out.mkdir(parents=True)
    adapter = out / 'adapter'
    policy.save_pretrained(adapter)
    tokenizer.save_pretrained(adapter)
    summary = {'model': args.model, 'method': 'action-level-dpo', 'seed': args.seed,
               'max_steps': args.max_steps, 'beta': beta, 'learning_rate': args.learning_rate,
               'examples': len(data), 'sources': len({r['source_id'] for r in rows}),
               'training_steps_sha256': digest(args.steps), 'loss_first': losses[0],
               'loss_last': losses[-1], 'trainable_parameters': sum(p.numel() for p in policy.parameters() if p.requires_grad),
               'adapter_sha256': {p.name: digest(p) for p in adapter.glob('*.safetensors')},
               'external_test': False}
    write_json(out / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--steps', default='work/v4_llm_export_001/train_steps.jsonl')
    parser.add_argument('--model', default='work/modelscope_deepseek_r1_1p5b')
    parser.add_argument('--out', required=True)
    parser.add_argument('--init-adapter')
    parser.add_argument('--max-steps', type=int, default=40)
    parser.add_argument('--learning-rate', type=float, default=1e-5)
    parser.add_argument('--beta', type=float, default=.1)
    parser.add_argument('--max-length', type=int, default=768)
    parser.add_argument('--seed', type=int, default=20260918)
    args = parser.parse_args()
    print(json.dumps(run(args), ensure_ascii=False, indent=2))
