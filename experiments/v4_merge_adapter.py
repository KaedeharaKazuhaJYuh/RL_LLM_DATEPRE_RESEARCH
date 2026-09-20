"""Merge a PEFT adapter into a base causal LM for deployment export."""
import argparse
import json
from pathlib import Path

from research.io import digest, write_json


def run(args):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    out = Path(args.out)
    if out.exists():
        raise FileExistsError('new output directory required')
    base = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=torch.bfloat16, trust_remote_code=False)
    merged = PeftModel.from_pretrained(base, args.adapter).merge_and_unload()
    out.mkdir(parents=True)
    merged.save_pretrained(out, safe_serialization=True)
    AutoTokenizer.from_pretrained(args.model, trust_remote_code=False).save_pretrained(out)
    weights = sorted(out.glob('*.safetensors'))
    summary = {'schema_version': 'v4-merged-adapter-1', 'model': args.model,
               'adapter': args.adapter,
               'adapter_sha256': digest(Path(args.adapter) / 'adapter_model.safetensors'),
               'weights_sha256': {path.name: digest(path) for path in weights}}
    write_json(out / 'merge_summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='work/modelscope_deepseek_r1_1p5b')
    parser.add_argument('--adapter', required=True)
    parser.add_argument('--out', required=True)
    print(json.dumps(run(parser.parse_args()), ensure_ascii=False, indent=2))
