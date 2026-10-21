# FaultDA-Bench overview (English, 0.5.60-dev)

FaultDA-Bench is an engineering diagnostic benchmark for verifiable data-analysis agents. It asks whether an agent, when tool execution state is ambiguous, an analysis artifact may be wrong, and checking costs something, can gather the necessary evidence, repair correctly and avoid duplicate side effects. It is a runnable **development** benchmark: no independent final test exists yet, and the project is under a scientific **HOLD** (no new model, API or RL runs are approved). Primary documentation is in Chinese ([README](../../README.md)); this page summarises it for paper readers. Every number below names the repository file it comes from.

## Research questions

From the README section "研究问题" ([README](../../README.md)):

1. **Commit vs correctness** – does a tool reporting "committed" mean the artifact satisfies the analysis contract?
2. **Evidence and decisions** – can an agent check, repair, stop, or escalate when information is insufficient?
3. **Attribution and generalisation** – do failures come from analysis, fault recovery or interface wording, and what do simple rules vs learned policies solve?

The original four-cell mechanism design can be bypassed by cheap uniform recomputation and has been stopped as the main experiment; question R is kept only as a correct-termination diagnosis under equal tool permissions and budget, and the mechanism route is paused ([R_COMPARISON_0520.md](../../faultda_bench/docs/R_COMPARISON_0520.md)).

## Environment and task design

- **24 development tasks** on **3 historical public sources**, all `split: historical_development`; design "three sources x two intents x four variants; shared slices are correlated" ([cross_source_v2.json](../../faultda_bench/protocols/cross_source_v2.json), fields `tasks`, `source_clusters`, `design`). The two intents are `group` and `version` analyses (8 tasks per source). A separate time-window diagnosis is kept outside the crossed design because two sources lack real timestamps (`transformations`).
- Sources (field `attribution`, all CC BY 4.0): UCI Auto MPG (doi:10.24432/C5859H), UCI Glass Identification (doi:10.24432/C5WW2P), UCI Occupancy Detection (doi:10.24432/C5X01N).
- Tools and state (README "已实现"): real CSV computation, persistent SQLite reports, staged corrections replaced only after a version comparison (stage then CAS), idempotent requests, and an audit of historical side effects.
- Fault factors: commit-acknowledgement loss (`commit_fault`) and semantic perturbation (`semantic_fault`), crossed with evidence availability (`E0`/`E1`) and check budget (2/4). The scripted cross-source run covers 24 tasks × 2 × 2 × 2 × 2 cells × 6 program policies = **2,304 executions** ([cross_source_v2_results.json](../../faultda_bench/reports/cross_source_v2_results.json) `audit.episodes`; rows in `cross_source_v2_results.jsonl.gz`).

## Private verifier separation

Execution flow: public task contract → agent selects tools → state/artifact update → **private independent verification** → per-condition aggregation. Verification answers and fault labels never enter the agent's tool observations (README "执行流程"). Policies receive only public JSON observations; environment objects and the private reference verifier (an independent Decimal reference) stay in the trusted runner ([faultda_bench/README.md](../../faultda_bench/README.md)). There is **no OS-level isolation** against arbitrary malicious local code.

## Evidence that exists and its boundaries

All results are re-counts of frozen, already graded historical development data on seen clusters. Intervals and exact tests come from the 0.5.60 descriptive audit ([summary.md](../../faultda_bench/reports/stats560/summary.md), [summary.json](../../faultda_bench/reports/stats560/summary.json); 95% Wilson intervals; 10,000 cluster-bootstrap resamples, seed 560).

| ID | Evidence (version) | Arms / kind | Counts | Boundary |
| --- | --- | --- | --- | --- |
| C1 | Receipt-fact diagnosis, 12 paired rows (0.3.95; [coherent_v38_accounting.json](../../faultda_bench/reports/coherent_v38_accounting.json)) | contextual vs explicit instruction; real DeepSeek requests | all fields correct 0/12 vs 6/12 (Wilson 0.000–0.242 vs 0.254–0.746); discordant 6/0, exact McNemar p = 0.03125, Holm-adjusted p = 0.125 | one seen development cluster; independent review pending |
| C2 | Instruction-clarity pair, 12 pairs (0.2.05; [clarity_v2_comparison.json](../../faultda_bench/reports/clarity_v2_comparison.json)) | original vs explicit; real DeepSeek requests | safe completion 4/12 vs 4/12; no discordant pairs, p = 1.0 | three seen historical tasks, one per source |
| C3 | Cross-source program policies, 384 cells each (0.2.05; [cross_source_v2_results.jsonl.gz](../../faultda_bench/reports/cross_source_v2_results.jsonl.gz)) | abstain, blind_retry, generic_verify, version_refresh, static_semantic, task_semantic; scripted programs | safe completion 0, 96, 192, 216, 288, 288 of 384 | scripted programs, not LLM results; 3 source clusters too few for inference |
| C4 | Explicit one-step termination diagnosis, 72 rows × 2 information conditions (0.5.50; [termination550/qualification.json](../../faultda_bench/reports/termination550/qualification.json)) | complete public rule vs always-stop / always-escalate; scripted controls | supported correct termination 72 / 24 / 48 of 72 per condition; actual safe completion 24 / 36 / 0 of 72 | one old development cluster (one data source); no model run |
| C5 | Registered grading of the same 144 packets (0.5.55; [termination555/qualification.json](../../faultda_bench/reports/termination555/qualification.json)) | registered complete-rule grade only | 144/144 supported correct termination, 48/144 actual safe completion; identical to the C4 rule grade row by row | single arm, no paired test; `independent_development_clusters: 1` |

How to read the table: exact McNemar/sign tests assume independent pairs, but pairs here are correlated within task/source clusters, and C3–C4 arms are deterministic scripts, so their very small p-values describe count asymmetry only. Several cluster-bootstrap intervals have zero width because every cluster has the same rate (balanced design); that is not certainty. Not available, and therefore not reported with numbers: any model arm on the 0.5.50/0.5.55 packets, learned SFT/DPO/GRPO arms on the 24 tasks, source-level clustering for C1/C4/C5, and any independent held-out test (`unavailable` in summary.json).

Other recorded evidence:

- Integrity: 660 frozen files are hash-pinned by [acceptance_v46.json](../../faultda_bench/protocols/acceptance_v46.json), plus 11 files in [performance555_v1.json](../../faultda_bench/protocols/performance555_v1.json) `optimization_files`. Hashes check consistency only; they do not authenticate the provider or history.
- Engineering: the 0.5.55 batch registration/grading of 144 cases went from 6.372 s to 0.898 s (median of 3 paired runs on one machine); energy was not measured ([PERFORMANCE_0555.md](../../faultda_bench/reports/PERFORMANCE_0555.md)).
- Human review: 24/24 development tasks passed a five-dimension human review ([SCIENTIFIC_REVIEW_24.md](../../faultda_bench/reports/SCIENTIFIC_REVIEW_24.md)); the latest 37 technical-review groups and the 12 formally registered referent-pair opinions cover only their stated scope (README "当前证据", "当前限制与下一步"). Human interface-validity review is still pending.
- Background only: the inherited V5 model line reported SFT 28/240 and GRPO/branch 0/240 on its own protocol ([CHANGELOG.md](../../CHANGELOG.md), V5.0.15-beta.2). Protocols differ between stages, so these are not comparable with FaultDA results and earlier local RL gains did not hold up against stronger supervised controls (README "项目演进").

## Reproduction

From the repository root, Python 3.11+, no GPU or API key:

```sh
python -m pip install -e .
python -m unittest discover -s tests
python -m faultda_bench.termination555.performance_audit
python -m faultda_bench.stats560.audit --output work/stats560.json
python -m scripts.release_version --check
```

Optionally `python -m pip install -e .[test]` and `python -m pytest -q`. Audits never overwrite existing outputs and refuse frozen locations. Historical entry points are listed in [docs/REPRODUCIBILITY.md](../REPRODUCIBILITY.md).

## Known limitations

- Only three seen sources with controlled parameter binding; synthetic dimension duplication and version revisions are not real production incidents (README "当前限制与下一步"; `limitations` in cross_source_v2.json: "no held-out source", "three sources do not support confirmatory inference").
- Within the FaultDA line, real-model evidence is limited to small paired pilots (12 pairs in C1 and C2) on seen clusters; the second model is deferred.
- At α = 0.05 an exact sign test needs at least 6 discordant pairs, all in one direction; the normal-approximation minimum detectable difference is 0.572 at n = 12 and 0.233 at n = 72 per arm, before accounting for clustering (summary.json `power`).
- The JSON tool interface is not an OS security sandbox.

## KDD-readiness gaps

1. An independent held-out test set (new sources not used in development).
2. More sources and tasks, so that source-level clustering supports inference.
3. Multi-model evaluation under equal tools, budgets and public inputs.
4. Completed human interface-validity review.
5. A repository license: there is no LICENSE file; the choice is the owner's decision.
6. Pre-registered analysis plan applying the stats560 reporting (Wilson + cluster bootstrap + exact paired tests + Holm) to any future runs.
