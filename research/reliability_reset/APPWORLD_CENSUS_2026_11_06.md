# AppWorld 0.1.0 historical train/dev replay census

**Status: completed descriptive engineering audit; not independent scientific confirmation.** This report contains aggregate counts only. Task-level files, extracted benchmark data, and per-task replay output remain in the private `work/` directory and are not included in the repository.

## Question and scope

**[事实]** Does replaying the archived GPT-4o ReAct Code Agent databases with the released AppWorld 0.1.0 scorer reproduce the saved per-task score and requirement labels for the official train/dev archive?

The frozen input inventory contains 90 train and 57 dev tasks for one historical lineage: GPT-4o (2024-05-13), ReAct Code Agent. The experiment used the corresponding AppWorld 0.1.0 data bundle and 0.1.3 experiment-output bundle. Inputs were hash-checked before extraction. Only train/dev tasks were replayed; no test or challenge records were used. Each scorer evaluation ran in a fresh Windows process under Python 3.12.14 and AppWorld 0.1.0. The agent was not executed and no model API was called.

## Results

| Split | Tasks | Saved pass | Saved fail | Replay pass | Replay fail | Pass → fail | Fail → pass | Exact check-label match |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Train | 90 | 47 | 43 | 13 | 77 | 34 | 0 | 21 |
| Dev | 57 | 29 | 28 | 12 | 45 | 17 | 0 | 17 |
| **Total** | **147** | **76** | **71** | **25** | **122** | **51** | **0** | **38** |

**[事实]** The replay completed for all 147 records with no scorer-process errors. Binary pass/fail agreed in 96/147 cases. Fifty-one of 76 saved passes became replay failures; none of the 71 saved failures became a pass. Exact passed/failed requirement-label lists matched in 38/147 cases. Each of the 51 pass-to-fail records contained exactly one assertion failure in the replay output.

## Interpretation and limits

**[推断]** This is a large within-archive replay discrepancy, and it confirms that the four-case result was not unique to those selected cases. It measures how the released scorer behaves on the databases preserved in this one historical output archive.

**[事实]** The source archive inventory found no `model_hashes.json` file in any of the 147 task database directories. **[推断]** The uniform pass-to-fail direction and one assertion per newly failing replay are consistent with the previously documented zero-counter / absent-change-metadata comparison path. This census did not retain or inspect the 51 assertion traces to establish per-case causal identity, and it did not run the adapted PR #219 predicate across all 147 tasks.

This result does **not** show that the original live evaluator missed violations, that any of the 51 agents behaved unreliably, that scores or rankings were wrong at original run time, or that the effect generalizes to other benchmarks, task families, model families, or contemporary systems. The source archive is one model/agent lineage, one benchmark, and historical train/dev material. The task set is not an independently sampled cross-benchmark population. The condition and broad framing also have direct upstream and literature coverage.

Therefore the result strengthens the engineering diagnosis of replay sensitivity, but it does not change the paper-claim decision: **NO-GO for a novel evaluator-error claim; scientific status HOLD**. No live model, strong-rule, or independent-task experiment was run.

## Near-neighbor and contribution decision — 2026-11-06

**[Fact]** Ding et al., *Re-executing Coding-Agent Evaluations: Unchanged Decisions and Unresolved Policy Risk* (arXiv:2610.14460v1, submitted 2026-10-10), re-executes 1,929 archived SWE-bench evaluations. It reports 5,999/6,006 archived verdicts reproduced, 23 disagreements with the archive, and no change to its two prespecified fixed-history decisions (best-agent selection and system-arm ranking). Seven of the 23 disagreements were tied to a revised reference-test list; the study also reports host/image sensitivity. [Primary paper](https://arxiv.org/html/2610.14460v1).

**[Inference]** This is a direct methodological neighbor for any claim that re-running archived agent evaluations reveals score drift or changes system selection. The current AppWorld census differs in benchmark domain and a specific archive condition: its 147 records are train/dev data from one historical GPT-4o ReAct lineage, and all archived database directories lack `model_hashes.json`. Yet the AppWorld zero-hash comparison condition was already reported upstream in [issue #218](https://github.com/StonyBrookNLP/appworld/issues/218) and addressed by the still-open [PR #219](https://github.com/StonyBrookNLP/appworld/pull/219) as checked on 2026-11-06. This census has no second model, no ranking decision, no independently adjudicated violation, and no evidence about the original live scorer.

**Decision: NO-GO for presenting the 147-case replay as an independent paper contribution.** It is a substantial, reproducible engineering case study of archive-sensitive rescoring. A future data-agent paper would need a distinct, preregistered question and an outcome that changes a prespecified decision beyond existing replay audits; merely repeating a replay audit on another benchmark or increasing the number of archived records is insufficient. The full-corpus PR #219 adapted control was not completed; the four-case control remains the only adapted-predicate result.

## Reproduction

The public script is [replay_census.py](replay_census.py). It accepts local encrypted bundles, verifies their exact recorded SHA-256 values, extracts only the train/dev task data and archived output databases into a new private directory, and runs a fresh scorer process for each task. It writes a per-task JSON file only in that private output directory and prints aggregate split summaries. The source archives and extracted protected task data are not redistributed here.

Frozen input SHA-256 values:

- AppWorld 0.1.0 data bundle: `fd9f9608c2ec71ed0ac25c3633a738b9129a318a129e31230425b9188e508250`
- AppWorld 0.1.3 experiment-output bundle: `e5ec6367d32b1883d28aaa25e4fe5026c89a08d5fb7a5742a83bfb65fe6bb2da`
- Local Python package freeze: SHA-256 `2b6f6954a48931220e233cb107571235fb09552298c39cdc947f2d5eb3c8f9c5` (retained with the private run output).

Run from the repository root in an environment with `appworld==0.1.0` installed:

```powershell
python research/reliability_reset/replay_census.py `
  work/reliability-reset-1.0.90/official-data-0.1.0.bundle `
  work/reliability-reset-1.0.90/official-experiment-outputs-0.1.3.bundle `
  work/reliability-reset-1.0.90/census147-private
```

The destination must not already exist. The protected data usage and output remain subject to the [AppWorld license](https://github.com/StonyBrookNLP/appworld#lock_with_ink_pen-license) and [development-data restrictions](https://github.com/StonyBrookNLP/appworld#no_entry_sign-agent-development-restrictions). A matching digest identifies an input archive; it does not independently authenticate the original historical execution.
