"""Generate local continuations while recording the chat-template boundary."""

import json
import sys
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, logging


def main():
    logging.set_verbosity_error()
    logging.disable_progress_bar()
    tokenizer = AutoTokenizer.from_pretrained(sys.argv[1], local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(sys.argv[1], dtype=torch.float16, local_files_only=True)
    model.to("cuda").eval()
    print(json.dumps({"ready": True, "device": str(next(model.parameters()).device)}), flush=True)
    for line in sys.stdin:
        request = json.loads(line)
        started = time.perf_counter()
        prompt = tokenizer.apply_chat_template(request["messages"], tokenize=False, add_generation_prompt=True)
        template_opens_think = prompt.rstrip().endswith("<think>")
        if request["close_think"]:
            if not template_opens_think:
                raise ValueError("This intervention requires a template with an open thinking segment")
            prompt += "</think>\n"
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
        with torch.inference_mode():
            generated = model.generate(**inputs, max_new_tokens=request["max_tokens"], do_sample=False,
                                       pad_token_id=tokenizer.eos_token_id)
        continuation = generated[0, inputs["input_ids"].shape[1]:]
        finished = len(continuation) < request["max_tokens"] or continuation[-1].item() == tokenizer.eos_token_id
        print(json.dumps({"content": tokenizer.decode(continuation, skip_special_tokens=True),
                          "finish_reason": "stop" if finished else "length",
                          "template_opens_think": template_opens_think,
                          "prefix_closed_by_controller": request["close_think"],
                          "input_tokens": inputs["input_ids"].shape[1],
                          "output_tokens": len(continuation),
                          "seconds": time.perf_counter() - started,
                          "peak_gpu_bytes": torch.cuda.max_memory_allocated()}), flush=True)


if __name__ == "__main__":
    main()
