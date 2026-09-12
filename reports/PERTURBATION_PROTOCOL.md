# Prompt-robustness protocol

## Purpose

The fixed 50-task benchmark is useful for controlled ablations, but repeated API calls alone do not test whether a policy relies on surface wording. I therefore add a first robustness split, `tasks/variants/wording_v1.jsonl`.

## What changes

Each task receives one of five natural-language instruction wrappers. The task ID, CSV path, task contract, allowed tools, budget, gold answer, and reference output remain unchanged. This means the existing verifier is still valid and results can be compared directly to the original task set.

## What does not change yet

This split does not change CSV values or column names. A value-changing split needs newly computed independent gold/reference artifacts before it can be used in a paper-quality comparison. It is deliberately kept separate from wording robustness.

## Planned comparison

Run the 50 wording variants under:

1. Rule Router, to measure keyword-routing sensitivity.
2. Raw LLM routing, to measure unconstrained prompt robustness.
3. Operation-family contract masking, to determine whether the contract improves robustness without revealing the exact action.

All LLM conditions must retain their provider, model, temperature, and replicate metadata. The constrained condition remains an ablation rather than an unconstrained LLM result.

