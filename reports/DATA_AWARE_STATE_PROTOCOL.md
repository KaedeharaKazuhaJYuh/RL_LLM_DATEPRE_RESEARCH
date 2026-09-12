# Data-aware policy state protocol

## Motivation

In the initial prototype, the agent selected its first action from the task text and a fixed state vector. As a result, changing CSV values could validate rebuilt gold/reference artifacts but could not meaningfully influence routing. This protocol introduces a reproducible read-only preflight state.

## `dataset_profile_v1_read_only`

Before action selection, the runtime derives a ten-dimensional vector from the CSV: difficulty, row-count bucket, missingness rate, numeric-column count, categorical-column count, time-column flag, target-column flag, normalized aggregate numeric magnitude, normalized numeric spread, and a reserved value. It exposes aggregate statistics only, never row-level data, and consumes no tool-call budget.

## Fairness boundary

This is an observed-state ablation: the environment provides a profile before the agent chooses an action. Results using it must not be directly compared with text-only routing without labeling the added information. The same extractor is applied to every method and every value_v1 artifact.

## Next evaluation

Rerun original and value_v1 raw/contract conditions under the same `dataset_profile_v1_read_only` state. Only then can the project ask whether the changed numerical profile affects model action selection or verifier outcomes.

