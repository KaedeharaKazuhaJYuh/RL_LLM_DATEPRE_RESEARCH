# WorkBench Revisited outcome audit — 2026-11-06

## Decision

**Scientific status: HOLD.** The failure-conditioned side-effect ratio is a useful interpretation check, but it is a deterministic decomposition of WorkBench's published outcome categories and does not establish an independent paper contribution. A second, narrower trace observation is reproducible: ten terminally correct, no-write-gold episodes contain a create-then-delete sequence. This is an empirical lead, not evidence of real-world harm or a benchmark scoring bug. The main final-state metrics do not count these transient writes as harmful; the released auxiliary `exact_match` flag marks the same runs as action mismatches. A recent close neighbor, SABench, already uses a trace-based authorization oracle and reports collateral damage among goal-satisfied runs.

## Evidence and method

**[Fact] Data.** The analysis uses only the official WorkBench Revisited `revisited_2026` group at official repository commit [`49c7dfd00c03d384ec59ea57374f50b766aa5613`](https://github.com/olly-styles/WorkBench/tree/49c7dfd00c03d384ec59ea57374f50b766aa5613). The pinned item-level CSV gzip has SHA-256 `6035FB112BBB4FB48CD56D643898CAC43C42D2D11BC6D2BB0E595D8D31EA2216`; the subset has 16,560 rows, 690 task IDs, 24 models, and 69 `base_template` clusters. The source repository is MIT-licensed.

**[Fact] Published claim and metric boundary.** The paper reports task completion and unconditional unwanted side effects over all 690 tasks, and its Figure 1 presents three outcome categories—correct, failed-but-harmless, and harmful side effects—for a subset of models. In the pinned evaluator, `is_correct` compares final tool-state tables, while `has_side_effects` returns `state_changed and not correct`. Therefore the side-effect flag is defined to be false for every terminally correct run. The evaluator also computes `exact_match` and prints a “correct but not exact match” diagnostic; this auxiliary field means the action-path difference is not absent from the full result artifact.

**[Fact] Conditional composition.** Let `C = P(correct)`, `H = P(unwanted_side_effect)`, and `Q = P(unwanted_side_effect | not correct)`. Because `H` is a subset of failures by construction, `H = (1-C)Q`. Across the 24 fixed models, Spearman correlation is `rho(C,H) = -0.941`; after conditioning on failure it is `rho(C,Q) = +0.350`. A paired bootstrap over 69 task-template clusters (10,000 resamples; seed 20261106) gives `rho(C,Q) - rho(C,H) = +1.291`, 95% percentile interval `[+0.774, +1.520]`; `rho(C,Q)` itself has interval `[-0.187, +0.605]`. Two bootstrap draws had a model with zero sampled failures and an undefined `Q`, so the reported intervals use 9,998 finite draws. This is a fixed-panel descriptive sensitivity, not a model-population test. Six records have both a nonempty `error` field and an unwanted-side-effect flag; a valid-record-only sensitivity remains similar (`rho(C,Q)=+0.353`) but does not change the interpretation.

**[Fact] Compensated writes.** A hash-pinned scan found 10 result rows with `correct=True`, `unwanted_side_effects=False`, an empty ground-truth action list, and a predicted action sequence containing a calendar-event or project-task creation followed by deletion of ID `00000300`. They span 8 task IDs and 4 models (`Gemini 3.1 Pro`: 2; `GLM-4.6`: 2; `Mistral Medium 3.5`: 1; `Qwen 3.5 Flash`: 5). The task prompts are conditional requests whose ground-truth action list is empty. In the pinned tool implementation both create functions allocate the next ID; the two initial CSVs contain IDs through `00000299`, and deletion removes ID `00000300`. The sequence therefore adds and then removes the newly created local row, restoring the final state. These are transient mutations in a simulated workspace; the files do not establish that any external recipient or real system was affected.

**[Fact] Small aggregate impact.** If these 10 candidate episodes were counted as trace-level authorization violations, the overall rate would increase by 10/16,560 (0.060 percentage points). In the post-hoc closest-harm-count pair, Gemini 3.1 Pro changes from 20 to 22 harm events while Gemini 3.5 Flash remains at 21, swapping their adjacent unconditional-harm order. A paired 69-template bootstrap gives the Gemini 3.1-minus-3.5 difference as `-0.145` percentage points before reclassification (95% interval `[-2.319,+2.174]`) and `+0.145` after it (95% interval `[-2.029,+2.464]`). Both intervals include zero. This exploratory reclassification does not robustly change model selection; the ten rows are concentrated in eight task IDs and four model outputs.

## Research interpretation

**[Inference]** The conditional-ratio result changes the descriptive association, but the identity `H=(1-C)Q` and the paper's own three-way outcome plot make the ratio a re-expression of released outcomes. The large paired correlation difference is expected from changing the denominator and does not by itself establish a new safety mechanism. This candidate is **NO-GO as a standalone contribution**.

**[Inference]** The create/delete traces are a more concrete reliability observation. They demonstrate that terminal equality and trajectory authorization are different questions in this benchmark. However, `exact_match` already flags these runs, and SABench already defines a deterministic trace-based oracle that checks every successful write against an authorization set. Its paper reports nonzero collateral damage among goal-satisfied runs. Thus neither the general method nor the broad claim that final-state success can miss unauthorized actions is novel here. The ten episodes could only support a narrowly framed WorkBench reanalysis if a complete trace-level regrade produced a material, uncertainty-aware change to a prespecified model-selection decision and independent review confirmed the task-contract labels.

**[Neighbor update]** CAREFUL-Bench (arXiv:2611.02978) now directly evaluates intermediate destructive calls, duplicate writes, redundant reads, and surplus steps in 800 multi-turn reference trajectories across 11 open models, with deterministic replay scoring. This further narrows the possible WorkBench contribution: a create-then-delete census or an action-aware metric alone is not sufficient. A surviving claim would need to establish a distinct, validated distinction between transient simulated mutations and user-visible/persistent harm, then show a robust decision consequence not captured by CAREFUL-Bench or SABench. The current WorkBench records do not establish that distinction or consequence; candidate remains **NO-GO** as a paper headline.

## Stop/go gate for any follow-up

Do not expand this into a new benchmark or run more models unless a bounded replay first shows all of the following:

1. The action actually mutated state before compensation (not merely a failed/no-op tool call).
2. The write violated the user-facing task contract; a different but legitimate path is not counted as unauthorized.
3. The full result artifact's `exact_match` diagnostic does not already answer the intended operational question.
4. Reclassification changes a predeclared model-selection conclusion with task-cluster uncertainty, rather than only swapping a pair separated by one or two events.
5. The contribution is distinguished from SABench's trace-authorization oracle and the recent cross-benchmark validity audit.

If any item fails, retain this as a release-analysis note and close the candidate. No model/API runs were used. No WSL2/Docker setup was needed for this offline audit.

## Reproduction

The bounded calculation is in [`workbench_outcome_audit.py`](workbench_outcome_audit.py). It refuses inputs whose SHA-256 differs from the pinned official item-level artifact. It prints the model-panel correlations, paired template-bootstrap intervals, the post-hoc adjacent-model sensitivity, and the no-write create/delete trace census. Example: `python workbench_outcome_audit.py <path-to-item_level_results.csv.gz>`.

## Sources

- WorkBench Revisited, arXiv:2606.13715v2: https://arxiv.org/abs/2606.13715
- Pinned WorkBench evaluator: https://github.com/olly-styles/WorkBench/blob/49c7dfd00c03d384ec59ea57374f50b766aa5613/src/evals/evaluation.py
- Pinned WorkBench metrics pipeline: https://github.com/olly-styles/WorkBench/blob/49c7dfd00c03d384ec59ea57374f50b766aa5613/src/evals/metrics.py
- Pinned item-level outcomes: https://github.com/olly-styles/WorkBench/blob/49c7dfd00c03d384ec59ea57374f50b766aa5613/data/results/item_level_results.csv.gz
- Task Success Is Not Enough: Side-effect-Aware Evaluation of Tool-Using Language Model Agents (SABench), arXiv:2610.34167v1: https://arxiv.org/abs/2610.34167
- Safety, or Just Capability? A Validity Audit of Agent-Safety Benchmarks, arXiv:2607.28685v2: https://arxiv.org/abs/2607.28685
