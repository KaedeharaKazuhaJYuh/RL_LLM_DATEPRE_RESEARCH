# Communication Telemetry Event-Drift Gated SSL: Experiment Protocol v0.2

Date: 2026-11-10  
Status: data census complete; no model has been trained and no model outcome is known.  
Dataset: official CESNET-TLS-Year22 XS HDF5, 10,000,000 flows.  
Purpose: update v0.1 with observed archive lineage, exact calendar split, and label-budget feasibility. The algorithm hypothesis and comparisons are inherited from v0.1; this update does not establish novelty.

Archive SHA-256: `340f84491dc9c5eb8173718bea15cd7fe80abf8e945adf26859a34aaa66e7816` (locally computed; DataZoo publishes no matching SHA-256 for this generated XS file). The APP and CATEGORY enum hashes are `71661ce0b59c4eb02b4001d4366cb49e4bc7cdf0131c6b23b972a4b069f240dd` and `c10c1e3cfdab459b20fc597ba8aa9dc662b654f9a41e486394e350dedc94d4de`. The full HDF5 tables were read in bounded chunks without a read/decompression error. The provider-declared eight unavailable dates match the archive exactly. The date/class census, weekly summary, split manifest, and their hashes are in the adjacent [census record](CESNET_TLS_YEAR22_XS_CENSUS_2026_11_10.json); exact predictor and target roles are in the [input field contract](CESNET_TLS_YEAR22_XS_FEATURE_CONTRACT_2026_11_10.md).

Version rule: v0.1 remains the original design record. This v0.2 document supersedes its unverified archive/date statements and candidate label-budget feasibility only; it retains all other prospective method and comparison requirements.

## 1. Research claim under test

**Question.** On a real, temporally ordered encrypted-traffic stream, can sparse labels tell a semi-supervised continual learner when an observed packet-event shift is predictive damage and when it is only an input/measurement change, so the learner can use abundant unlabeled flows without propagating bad pseudo-labels or forgetting earlier services?

This is narrower than “SNNs are better for continual learning.” The intended methodological contribution, if supported, is a **label-anchored, view-conditional update gate for an SNN packet-event branch**. It combines three quantities that must be independently ablated: (1) unsupervised drift in packet-event and flow-summary views; (2) predictive error evidence from the period's scarce labels; and (3) reliability of candidate pseudo-labels. It does not claim that view drift, pseudo-label confidence, drift detection, or SNN temporal consensus is individually new.

The SNN is relevant because each flow has an ordered packet-event sequence. Its within-flow membrane/spike dynamics are the representation being tested. Across-week retention is separately supplied by the continual-learning method and memory budget. This separation directly reflects the advisor's two interests: learning from a few labels plus many unlabeled examples, and testing whether an SNN's temporal dimension contributes.

## 2. Proposed mechanism: three-state evidence gate

For week/window `t`, let `X^p_t` be packet-event inputs (PPI: inter-packet time, direction, size, and only fields available in the chosen protocol), `X^s_t` be non-sequence flow summaries, and `L_t` be the labels released after predictions for that window have been scored.

1. **Predict before learning.** The frozen current model predicts every flow in window `t`. The evaluator retains all labels for scoring; the learner receives none yet.
2. **Measure view-specific input change.** Compute a predeclared two-sample drift statistic `D^p_t` and `D^s_t` against the reference window using only unlabeled inputs. Its thresholds are fixed on development windows. The statistic is a trigger signal, not proof of concept drift.
3. **Measure predictive damage.** After the evaluation is sealed, reveal only the sampled label budget `L_t`. Compare the pre-update model's loss/error on `L_t` with its frozen reference-period estimate using a one-sided confidence interval and a development-fixed non-inferiority margin `δ`. Return exactly one state:
   - `damage_supported`: lower confidence bound for degradation exceeds `δ`;
   - `no_material_damage_supported`: upper confidence bound is below `δ`;
   - `insufficient_evidence`: interval crosses `δ`.
   A wide interval is not treated as evidence that the model is stable.
4. **Choose the next-window update.**
   - `damage_supported`: supervised update is allowed; unlabeled temporal-branch updates are allowed only for pseudo-labels whose reliability gate passes.
   - `no_material_damage_supported`: do not make a large temporal-branch update solely because `D^p_t` is high; keep the event encoder stable and permit the preregistered low-rate supervised/head update.
   - `insufficient_evidence`: use the labeled examples only; do not use pseudo-labels to change the temporal encoder.
   `D^s_t` and `D^p_t` are reported separately and can modulate update size only according to a rule fixed before the held-out sequence. No test-window-specific thresholds or hand-coded Week-10 rule are allowed.
5. **Estimate pseudo-label reliability without reusing labels as if independent.** Use out-of-fold or pre-update predictions on the revealed labeled sample to estimate class-conditional pseudo-label precision; shrink low-support classes toward a global estimate. The exact estimator, confidence level, minimum support and thresholds must be selected on development windows and frozen. If the label budget cannot support a class-level estimate, that class receives no temporal-branch pseudo-label update.
6. **Retain prior service knowledge.** All compared update policies use the same fixed byte budget and the same replay policy. The gate is not credited for a gain produced by extra memory or update FLOPs.

The method has three distinct controls: **always update**, **never use unlabeled updates**, and **label-only on insufficient evidence**. The gate must beat these under matched budgets to support the mechanism claim.

## 3. Data stream and temporal protocol

### Main natural-change sequence

Use the pinned DataZoo source snapshot documented in `CESNET_TLS_YEAR22_CONTINUAL_DATA_CONTRACT_AUDIT_2026_11_09.md`. The dataset has known missing collection dates; weeks are evaluated only when their available-day coverage is reported from the selected archive. Week 10 (2022-03-07–13) is excluded from the natural-change main sequence because the exporter update changed packet retransmission handling.

| Use | ISO weeks in 2022 | Operation |
|---|---|---|
| Initialization | W11–W14 (2022-03-14–04-10; 28 dates, 1,086,644 flows) | Initial training; choose the fixed initial service vocabulary only from this period; no later labels used. |
| Development | W15–W18 (2022-04-11–05-08; 28 dates, 994,127 flows) | Select hyperparameters, confidence procedure, drift thresholds, and practical non-inferiority margin. No headline result. |
| Frozen prequential evaluation | W19–W51 (2022-05-09–12-25; 229 dates, 6,120,730 flows) | Predict each week with the model frozen from the previous update; score first; then expose unlabeled inputs and only the week's sampled label budget for updating the next week. No per-flow test labels enter before that week's predictions are sealed. W50 has only five available dates. |
| Partial tail | W52 (2022-12-26–28; 3 dates, 24,017 flows) | Report separately as partial-window sensitivity only; exclude from the primary average. |
| Known measurement-change stress test | W10 (2022-03-07–13; 7 dates, 254,636 flows) | Separate transfer test around exporter change; use a pre-change model and fixed policy. Never tune on this window or merge it into the natural-change average. |

The executable exact-date manifest is [CESNET_TLS_YEAR22_XS_SPLIT_MANIFEST_2026_11_10.csv](CESNET_TLS_YEAR22_XS_SPLIT_MANIFEST_2026_11_10.csv), SHA-256 `00b4baed8fe2543e568094e92596cb8a37b4a7bc6d62708779efcf036b99cc7a`. It keys each date by **ISO year and week**, not week number alone: 2022-01-01/02 are ISO 2021-W52 and are excluded from the 2022 partial-tail phase. The file contains 357 dates, 10,000,000 flows, and the exact 2022 missing-date set. The early separate period W1–W9 contains 60 dates and 1,498,658 flows. The census read aggregate APP counts for all dates, including W19–W51; no per-flow evaluation outcomes or model predictions were generated. Therefore the held-out interval is untouched by model fitting, but its aggregate class support is no longer label-blind.

### Label budgets

Use fixed per-week total annotation budgets sampled uniformly without replacement from that week's eligible training population; do not use true classes to select examples. Keep 50 and 200 as extreme-low-label stress points, 1,000 as the primary low-label candidate, 5,000 as a moderate-label point, and 10,000 as a high-label reference. These are candidate values to be finalized using W15–W18 only before any model evaluation; the latter three do not imply that every service is observed. A stratified class-balanced label policy is a separate, explicitly oracle-assisted secondary condition and must not be presented as passive labeling.

The support audit computes the expected number of distinct service labels in a uniform weekly sample without replacement. Across W19–W51, the mean expected coverage out of 180 active service classes is 34.4 at 50 labels, 74.8 at 200, 132.8 at 1,000, 168.3 at 5,000, and 172.6 at 10,000. This is a design constraint, not an observed label draw or model result. At low budgets, class-conditional pseudo-label reliability cannot be estimated for many services; the default for insufficient class support must be “no unlabeled event-branch update” unless development data validate a preregistered pooled estimator. Macro-F1 and class support must be reported with explicit minimum-support rules fixed on W15–W18.

## 4. Primary comparison and controls

All methods receive identical flow IDs, packet/statistic fields, windows, label draws, unlabeled examples, update opportunities and memory bytes. Match trainable parameters as closely as feasible and report actual parameter/FLOP/time differences where exact matching is impossible.

| Arm | Purpose |
|---|---|
| ANN sequence encoder + supervised online update | Strong architecture-matched non-spiking reference. |
| ANN sequence encoder + replay + SSL | Tests whether generic continual SSL explains the benefit. |
| SNN packet-event encoder + supervised online update | Isolates the SNN representation from SSL and the gate. |
| SNN + SpikeMatch-style multi-time-step consistency | Direct control for known SNN temporal-consensus pseudo-labeling. |
| SNN + always-on SSL | Tests whether drift-conditioned gating is needed. |
| SNN + proposed three-state gate | Candidate method. |
| SNN + sparse-label-only update | Tests the value and harm of unlabeled updates. |
| Offline joint-label upper bound | Diagnostic ceiling only; not a fair online competitor. |

DietCL should be reproduced or mapped at equal update-compute budget. SOUL components (replay, gradient protection, pseudo-labeling) should be included if their implementation is portable without changing its original role. A generic online SSL stream baseline (e.g. SLEADE) is a priority literature/protocol comparison; direct inclusion depends on comparable multi-class traffic setup and a faithful implementation, not merely renaming its components.

## 5. Questions, metrics and decision criteria

### Primary endpoint

The primary endpoint is mean weekly **prequential macro-F1** over W19–W51, with each week weighted equally; publish the weekly curve and a paired interval over week blocks and label seeds. If the selected archive lacks enough support for a stable macro metric, define a minimum support rule from the development period and report excluded classes/windows transparently.

### Key secondary endpoints

- Old-service retention and forgetting: per class, compare current score with the best prior score after initial training; summarize over classes and weeks, not individual flows as independent samples.
- Label efficiency: area under the prequential performance-versus-cumulative-label curve.
- Pseudo-label precision and coverage by class and week, split by event-view drift state.
- Week-10 stress: pre/post change in PPI-view performance, flow-summary performance, calibration and recovery after returning to post-change weeks; present as one dataset-specific stress case, not a general causal estimate.
- Compute and memory: update FLOPs, wall-clock latency, peak memory and replay bytes. No energy claim without target-hardware measurement.

### Claim criteria

1. **Semi-supervised value:** at least one preregistered low-label budget improves over the same architecture's labeled-only arm on the primary endpoint without a worse predeclared forgetting limit.
2. **SNN-specific value:** SNN exceeds the matched ANN sequence arm under identical input and learning protocol, and shuffling/removing within-flow temporal order removes the gain. Otherwise report no independent SNN advantage.
3. **Gate-specific value:** the proposed gate improves the prequential macro-F1/forgetting trade-off over always-on SSL, label-only update, and unlabeled-drift-only triggers; improvements must appear in multiple held-out windows and label seeds, not only Week 10.
4. **Mechanism evidence:** changes in `D^p`, `D^s` and label-supported predictive damage must predict which branch update helps, and the frozen rule must have fewer harmful updates than matched controls. This is assessed on held-out windows, not demonstrated by a source-paper statement that Week 10 changed.

These criteria are prospective. They are not current results or a novelty conclusion.

## 6. Ablations that identify where any gain comes from

1. ANN vs SNN, identical PPI sequence and supervised labels.
2. SNN with shuffled packet order vs original packet order.
3. SNN temporal consensus SSL vs single-readout SSL vs labeled-only.
4. Gate without flow-stat view, without event view, without sparse-label error test, and without pseudo-label precision calibration.
5. Always-update vs never-update vs three-state gate.
6. Replay off/on under identical byte budget; learning-rate, update-step and pseudo-label-count matched.
7. Natural-change main sequence vs Week-10 measurement-change stress test.

## 7. Analysis and reproducibility commitments

- Use at least 5 label-draw seeds in development and held-out test; model seeds are additional, not substitutes for independent weeks.
- Bootstrap paired results over week blocks and service classes. Flow-level confidence intervals alone are invalid because flows are correlated by service and time.
- Publish exact data revision, DataZoo commit, manifest, service-map hash, preprocessing, seed list, per-week class counts, label indices (or deterministic hash-derived IDs if redistribution is restricted), model checkpoints/configs and raw per-week predictions.
- The census read all labels only to produce aggregate support metadata. Keep this disclosure in any report; no model outputs, predictions, or per-flow evaluation results have yet been created.
- Report a complete run ledger including failed runs and planned compute. Preserve PPI and statistic-view schemas; never expose `TLS_SNI`, label-derived fields or future timestamp features to the classifier.
- Keep a separate untouched final segment of weeks for the gate's final estimate only after all thresholds and methods are frozen. This is the only evidence used for a headline claim.

## 8. Closest prior work and what it rules out

- **DietCL** already combines scarce labels and an unlabeled stream in continual learning with a compute budget. That combination alone is not an increment. [ICLR 2024 paper](https://openreview.net/forum?id=Xvfz8NHmCj)
- **SOUL** already applies semi-supervised continual learning to network intrusion detection with replay, gradient protection and pseudo-labels. The data/task distinction must be exact, and transferable controls should be included. [SOUL](https://arxiv.org/abs/2412.00911)
- **SLEADE** already addresses sparsely labeled evolving streams with disagreement-weighted pseudo-labels and unsupervised drift detection. A drift detector plus confidence-weighted SSL is not enough to claim novelty. [TKDE paper](https://doi.org/10.1109/TKDE.2025.3647050)
- **Semi-supervised input/concept drift separation** predates modern SNN methods. Unsupervised input shift plus sparse-label predictive monitoring is not a new generic concept. [Information Sciences 2016](https://doi.org/10.1016/j.ins.2016.03.034)
- **SpikeMatch** already uses SNN multi-time-step agreement for pseudo-labels in static visual SSL; time-step agreement alone is not novel. [SpikeMatch](https://arxiv.org/html/2509.22581v1)
- CESNET's Year22 data offers a real ISP stream with a documented measurement-process change as well as natural traffic variation. It provides a concrete communications-domain setting to test the interaction above, but one collector event alone does not establish generality. [Dataset paper](https://www.nature.com/articles/s41597-024-03927-4)

Accordingly, the candidate independent contribution is not a new generic drift detector. It is the experimentally isolated interaction of (a) packet-event SNN temporal representation, (b) a separate flow-summary view, (c) delayed scarce labels used as evidence of predictive damage, and (d) the resulting selective continual-SSL update policy under a real, long-horizon network trace. Whether this crosses the novelty threshold remains subject to a full method and protocol comparison, and then to the paired experiments above.

## 9. Immediate execution order

1. Audit the permitted input field whitelist and determine whether any client/session identity or repeated-flow grouping is required; current census only confirms schema and aggregate support.
2. Use W15–W18 to freeze label budgets, label seeds, class-support rule, baseline hyperparameters, confidence intervals, pseudo-label calibration and update FLOP/byte budgets.
3. Run a no-headline compute smoke on a development week: same flow IDs, PPI tensors, summary fields and labels reach matched ANN/SNN encoders; assert `APP`, `CATEGORY`, SNI, time and identity fields cannot enter model inputs.
4. Generate and hash label-draw indices after preprocessing is frozen; do not use evaluation labels for per-class tuning.
5. Run the paired ANN controls, then SNN controls and only then the three-state gate. Keep W43–W51 as a late chronological evaluation tranche whose model outputs remain sealed until all choices are frozen.

