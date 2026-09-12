# Data-aware value_v1: run-0 precheck

## Conditions

The agent receives `dataset_profile_v1_read_only` before choosing its first tool. The profile is an aggregate ten-dimensional CSV representation; it contains no row-level data and does not consume tool budget. All value_v1 runs use rebuilt gold and reference artifacts.

| Data condition | Raw routing | Operation-family contract |
|---|---:|---:|
| Original | 29 / 50 (58.0%) | 49 / 50 (98.0%) |
| value_v1 | 33 / 50 (66.0%) | 48 / 50 (96.0%) |

## Interpretation

The precheck verifies the new state, transformed CSVs, rebuilt verifier artifacts, and both policy conditions run together. It does not establish that numerical values improve or harm routing: there is one independent API call for each condition, and adding the profile itself changes the LLM input from the earlier text-only experiments.

## Observed errors

The original-contract condition fails only T11. The value_v1 contract condition fails T03 and T11. Raw failures are broader and differ across the two calls, which is compatible with API-call variability as well as possible profile sensitivity.

## Required next step

Evaluate every one of the four data-aware conditions with repeated independent API calls, then compare means, standard deviations, and per-task failure frequencies. Keep all data-aware figures separate from text-only figures.

