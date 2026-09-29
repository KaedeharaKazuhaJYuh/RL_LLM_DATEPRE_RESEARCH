"""Bounded LoRA supervised pilot on verified V4 tool-decision trajectories."""
import argparse
import json
import random
from pathlib import Path

from experiments.v4_llm_export import input_text
from research.io import digest, write_json
from research.stage_profile import StageProfile, scope


MODEL = 'deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B'


def examples(path, tokenizer, max_length):
    rows = [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line]
    encoded = []
    for row in rows:
        messages = [{'role': 'user', 'content': input_text(row['input'])}]
        prefix = tokenizer.apply_chat_template(messages, tokenize=True,
                                               add_generation_prompt=True)['input_ids']
        answer = json.dumps({'action': row['action']}, ensure_ascii=False, separators=(',', ':'))
        completion = tokenizer.encode(answer + tokenizer.eos_token, add_special_tokens=False)
        if len(prefix) + len(completion) > max_length:
            raise ValueError(f'example exceeds max_length: task={row["task_id"]}, tokens={len(prefix)+len(completion)}')
        ids = prefix + completion
        encoded.append({'input_ids': ids, 'attention_mask': [1] * len(ids),
                        'labels': [-100] * len(prefix) + completion})
    return rows, encoded


def run(args):
    if Path(args.out).exists():
        raise FileExistsError('new output directory required')
    profile_out = getattr(args, 'profile_out', None)
    if profile_out and Path(profile_out).exists():
        raise FileExistsError('new profile output file required')
    import torch
    from peft import LoraConfig, PeftModel, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU required for this pilot')
    profile = StageProfile(synchronize=torch.cuda.synchronize) if profile_out else None
    if profile is not None:
        torch.cuda.reset_peak_memory_stats()
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    with scope(profile, 'tokenizer_load'):
        tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.revision, trust_remote_code=False)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
    with scope(profile, 'examples_tokenize'):
        rows, dataset = examples(args.steps, tokenizer, args.max_length)
    with scope(profile, 'model_load'):
        model = AutoModelForCausalLM.from_pretrained(args.model, revision=args.revision,
                                                      dtype=torch.bfloat16,
                                                      trust_remote_code=False)
        model.config.use_cache = False
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
        model.enable_input_require_grads()
        if getattr(args, 'adapter_init', None):
            model = PeftModel.from_pretrained(model, args.adapter_init, is_trainable=True)
        else:
            model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, lora_dropout=.05,
                                                     target_modules='all-linear', bias='none',
                                                     task_type='CAUSAL_LM'))
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())

    def collate(batch):
        length = max(len(x['input_ids']) for x in batch)
        return {key: torch.tensor([x[key] + [pad] * (length - len(x[key])) for x in batch])
                for key, pad in [('input_ids', tokenizer.pad_token_id),
                                 ('attention_mask', 0), ('labels', -100)]}

    out = Path(args.out)
    out.mkdir(parents=True)
    config = TrainingArguments(output_dir=str(out / 'checkpoints'), max_steps=args.max_steps,
                               per_device_train_batch_size=1, gradient_accumulation_steps=4,
                               learning_rate=args.learning_rate, bf16=True, logging_steps=1,
                               save_strategy='no', report_to='none', remove_unused_columns=False,
                               seed=args.seed, dataloader_num_workers=0)
    class ProfiledTrainer(Trainer):
        def training_step(self, *call_args, **call_kwargs):
            with scope(profile, 'train_forward_backward'):
                return super().training_step(*call_args, **call_kwargs)

    with scope(profile, 'trainer_setup'):
        trainer = ProfiledTrainer(model=model, args=config, train_dataset=dataset, data_collator=collate)
    with scope(profile, 'train_loop'):
        result = trainer.train()
    adapter = out / 'adapter'
    with scope(profile, 'adapter_save'):
        model.save_pretrained(adapter)
        tokenizer.save_pretrained(adapter)
    summary = {'model': args.model, 'revision_requested': args.revision,
               'adapter_init': getattr(args, 'adapter_init', None),
               'adapter_init_sha256': {p.name: digest(p) for p in Path(args.adapter_init).glob('*.safetensors')}
               if getattr(args, 'adapter_init', None) else {},
               'base_commit': getattr(model.config, '_commit_hash', None),
               'local_base_weights_sha256': {p.name: digest(p) for p in Path(args.model).glob('*.safetensors')}
               if Path(args.model).is_dir() else {},
               'seed': args.seed, 'max_steps': args.max_steps,
               'examples': len(rows), 'sources': len({x['source_id'] for x in rows}),
               'training_steps_sha256': digest(args.steps), 'trainable_parameters': trainable,
               'total_parameters': total, 'training_loss': result.training_loss,
               'adapter_sha256': {p.name: digest(p) for p in adapter.glob('*.safetensors')},
               'external_test': False}
    write_json(out / 'summary.json', summary)
    if profile is not None:
        profile.write(profile_out, operation='sft_train',
                      metadata={'steps_sha256': summary['training_steps_sha256'],
                                'max_steps': args.max_steps, 'model': args.model,
                                'peak_cuda_allocated_bytes': torch.cuda.max_memory_allocated(),
                                'adapter_sha256': summary['adapter_sha256']})
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--steps', default='work/v4_llm_export_001/train_steps.jsonl')
    parser.add_argument('--model', default=MODEL)
    parser.add_argument('--adapter-init', help='continue supervised training from an existing LoRA adapter')
    parser.add_argument('--out', required=True)
    parser.add_argument('--revision', default='main')
    parser.add_argument('--max-steps', type=int, default=20)
    parser.add_argument('--max-length', type=int, default=768)
    parser.add_argument('--learning-rate', type=float, default=2e-4)
    parser.add_argument('--seed', type=int, default=20260917)
    parser.add_argument('--profile-out', help='write synchronized stage timings to a new JSON file')
    args = parser.parse_args()
    print(json.dumps(run(args), ensure_ascii=False, indent=2))
