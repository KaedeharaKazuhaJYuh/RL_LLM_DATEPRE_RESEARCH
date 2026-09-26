"""Probe Intel NPU execution and optionally benchmark an OpenVINO GenAI LLM."""
import argparse
import json
import platform
import time
from pathlib import Path

import numpy as np
import openvino as ov
from openvino import opset13 as ops


def device_info(core, device):
    return {
        'available_devices': core.available_devices,
        'target_device': device,
        'full_name': core.get_property(device, 'FULL_DEVICE_NAME'),
        'architecture': core.get_property(device, 'DEVICE_ARCHITECTURE'),
    }


def verify_graph(core, device):
    parameter = ops.parameter([1, 16], np.float32, name='input')
    model = ov.Model([ops.relu(parameter)], [parameter], 'npu_relu_probe')
    started = time.perf_counter()
    compiled = core.compile_model(model, device)
    compile_seconds = time.perf_counter() - started
    input_data = np.arange(-8, 8, dtype=np.float32).reshape(1, 16)
    started = time.perf_counter()
    output = compiled([input_data])[0]
    inference_seconds = time.perf_counter() - started
    expected = np.maximum(input_data, 0)
    return {'passed': bool(np.array_equal(output, expected)),
            'compile_seconds': compile_seconds,
            'inference_seconds': inference_seconds}


def benchmark_llm(model_path, device, prompt, max_new_tokens, adapter_path=None,
                  adapter_alpha=1.0):
    import openvino_genai as ov_genai

    started = time.perf_counter()
    pipeline_args = {}
    if adapter_path:
        adapter = ov_genai.Adapter(str(adapter_path))
        pipeline_args['adapters'] = ov_genai.AdapterConfig(adapter, adapter_alpha)
    pipeline = ov_genai.LLMPipeline(str(model_path), device, **pipeline_args)
    compile_seconds = time.perf_counter() - started
    config = ov_genai.GenerationConfig()
    config.max_new_tokens = max_new_tokens
    config.do_sample = False
    started = time.perf_counter()
    output = pipeline.generate(prompt, config)
    generation_seconds = time.perf_counter() - started
    return {'model': str(model_path), 'adapter': str(adapter_path) if adapter_path else None,
            'adapter_alpha': adapter_alpha if adapter_path else None, 'prompt': prompt,
            'max_new_tokens': max_new_tokens, 'compile_seconds': compile_seconds,
            'generation_seconds': generation_seconds, 'output': str(output)}


def run(args):
    core = ov.Core()
    if args.device not in core.available_devices:
        raise RuntimeError(f'{args.device} is unavailable: {core.available_devices}')
    result = {'schema_version': 'v4-npu-probe-1', 'python': platform.python_version(),
              'openvino': ov.__version__, **device_info(core, args.device),
              'graph_probe': verify_graph(core, args.device)}
    if args.model:
        model_path = Path(args.model)
        if not model_path.exists():
            raise FileNotFoundError(model_path)
        adapter_path = Path(args.adapter) if args.adapter else None
        if adapter_path and not adapter_path.exists():
            raise FileNotFoundError(adapter_path)
        result['llm'] = benchmark_llm(model_path, args.device, args.prompt,
                                      args.max_new_tokens, adapter_path,
                                      args.adapter_alpha)
    if args.out:
        out = Path(args.out)
        if out.exists():
            raise FileExistsError('new output file required')
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', default='NPU')
    parser.add_argument('--model')
    parser.add_argument('--adapter')
    parser.add_argument('--adapter-alpha', type=float, default=1.0)
    parser.add_argument('--prompt', default='Return only JSON with action set to stop.')
    parser.add_argument('--max-new-tokens', type=int, default=16)
    parser.add_argument('--out')
    print(json.dumps(run(parser.parse_args()), ensure_ascii=False, indent=2))
