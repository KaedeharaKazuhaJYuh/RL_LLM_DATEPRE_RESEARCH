"""Frozen V4 evaluation with an OpenVINO GenAI model on Intel NPU."""
import argparse
from collections import defaultdict
import json
import tempfile
import time
from pathlib import Path

from agent.llm import parse_step
from experiments.v4_llm_export import input_text, model_input
from research.io import ROOT, digest, write_json
from research.v4_sequence_env import SequenceEnv


def choose(pipeline, task, observation, max_new_tokens):
    prompt = input_text(model_input(task, observation))
    started = time.perf_counter()
    response = str(pipeline.generate(prompt, max_new_tokens=max_new_tokens,
                                     do_sample=False)).strip()
    latency = time.perf_counter() - started
    try:
        choice, _ = parse_step(response, task['allowed_tools'], fixed_bindings=True)
        return choice['action'], response, None, latency
    except (ValueError, KeyError, TypeError) as exc:
        return None, response, type(exc).__name__, latency


def run(args):
    if Path(args.out).exists():
        raise FileExistsError('new output file required')
    import openvino as ov
    import openvino_genai as ov_genai

    core = ov.Core()
    if args.device not in core.available_devices:
        raise RuntimeError(f'{args.device} is unavailable: {core.available_devices}')
    tasks = json.loads((Path(args.protocol) / 'tasks.json').read_text(encoding='utf-8'))
    dev = [x for x in tasks if x['split'] == 'dev']
    oracle = json.loads((Path(args.protocol) / 'dev_oracle.json').read_text(encoding='utf-8'))
    assert {x['task_id'] for x in dev} == set(oracle)
    if args.limit:
        dev = dev[:args.limit]
    pipeline_args = {}
    if args.adapter:
        adapter = ov_genai.Adapter(args.adapter)
        pipeline_args['adapters'] = ov_genai.AdapterConfig(adapter, args.adapter_alpha)
    started = time.perf_counter()
    pipeline = ov_genai.LLMPipeline(args.model, args.device, **pipeline_args)
    compile_seconds = time.perf_counter() - started
    records = []
    with tempfile.TemporaryDirectory(prefix='v4_llm_eval_npu_') as scratch:
        for task in dev:
            for fault in (False, True) if args.both_faults else (False,):
                env = SequenceEnv(task, oracle[task['task_id']], scratch, fault)
                steps = []
                while not env.done:
                    action, raw, error, latency = choose(
                        pipeline, task, env.observation(), args.max_new_tokens)
                    steps.append({'action': action, 'raw': raw, 'parse_error': error,
                                  'latency_seconds': latency})
                    if error:
                        break
                    env.step(action)
                scored = env.result() if env.done else {'passed': False, 'reward': 0.0}
                records.append({'task_id': task['task_id'], 'source_id': task['source_id'],
                                'novelty': task['composition_novelty'], 'fault': fault,
                                'passed': scored['passed'], 'reward': scored['reward'],
                                'steps': steps})
    groups = defaultdict(list)
    for record in records:
        key = f'{record["novelty"]}:{"fault" if record["fault"] else "clean"}'
        groups[key].append(record)
    latencies = [step['latency_seconds'] for record in records for step in record['steps']]
    summary = {'model': args.model, 'adapter': args.adapter,
               'adapter_alpha': args.adapter_alpha if args.adapter else None,
               'device': args.device, 'device_name': core.get_property(args.device, 'FULL_DEVICE_NAME'),
               'device_architecture': core.get_property(args.device, 'DEVICE_ARCHITECTURE'),
               'openvino': ov.__version__, 'protocol_sha256': digest(Path(args.protocol) / 'manifest.json'),
               'compile_seconds': compile_seconds, 'episodes': len(records),
               'passed': sum(r['passed'] for r in records),
               'parse_errors': sum(bool(s['parse_error']) for r in records for s in r['steps']),
               'generation_calls': len(latencies),
               'generation_seconds_mean': sum(latencies) / max(1, len(latencies)),
               'slices': {k: {'n': len(v), 'passed': sum(x['passed'] for x in v)}
                          for k, v in groups.items()},
               'greedy': True, 'external_test': False, 'records': records}
    write_json(args.out, summary)
    return {k: v for k, v in summary.items() if k != 'records'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', default=str(ROOT / 'tasks/v4/llm_pilot_v1'))
    parser.add_argument('--model', default='work/modelscope_deepseek_r1_1p5b_ov_int4')
    parser.add_argument('--adapter')
    parser.add_argument('--adapter-alpha', type=float, default=1.0)
    parser.add_argument('--device', default='NPU')
    parser.add_argument('--out', required=True)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--both-faults', action='store_true')
    parser.add_argument('--max-new-tokens', type=int, default=48)
    print(json.dumps(run(parser.parse_args()), ensure_ascii=False, indent=2))
