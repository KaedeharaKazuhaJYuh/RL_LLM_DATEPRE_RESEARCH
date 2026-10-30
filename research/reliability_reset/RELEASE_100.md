# Reliability Reset 1.0.0 — offline audit foundation

Date: 2026-10-22. Branch: `agent-eval-reliability-reset`.

This is the first executable release of the reset research subsystem, based on the FaultDA-Bench 0.5.65-dev checkpoint. It is not a scientific benchmark release establishing the proposed evaluation error, and does not advance the frozen historical FaultDA or inherited V5 version.

## Delivered

1. Separately imported original outcome scores and contract-based reliability classification, bound to run, public input, contract, trace and state artifacts.
2. Explicit responsibility, event evidence locations, non-duplicated event IDs, repaired historical violations and preserved uncertainty.
3. Family/system confusion tables, exact FSR denominators and missingness bounds; pairwise comparisons with identical inputs/permissions/caps and explicit missing pairs.
4. Reproducible synthetic controls and mutation/rejection tests for shared provenance, swapped inputs, altered files, budget violations and score-to-label coupling.
5. Standalone source review preparation with machine scores/facts withheld and decisions left pending.

Implementation uses Python's standard library, one local JSON import and family-indexed aggregation. It adds no model runtime or persistent service. Native/C++ acceleration and Go scheduling would not improve the validity of this small offline audit and are not prerequisites. No power/energy measurements or performance improvement claims are made.

## Validation scope

The executable control suite has ten cases in one synthetic publication family and two explicitly scripted control arms, for twenty records. Cases cover healthy completion, harm then repair, environment repair, safe stop, missing history, confirmed harm with unknown terminal state, outcome false negative, unsafe noncompletion, unknown actor and unsupported stop.

The controls' outcomes are designed inputs, not observed Agent behavior. They establish that the implementation distinguishes the requested situations. They do not estimate natural error prevalence, show a new mechanism, validate a model, or justify calling these ten cases ten independent tasks.

Final local reproduction outputs are under `work/reliability-reset-1.0.0/`: `controls/`, `audit/` and `review/`. The generator and test suite are versioned. Validation and source hashes are recorded in `VALIDATION_100.json`. Existing source/results are not silently overwritten.

Validation completed: repository discovery ran 921 tests with no failures and three skips in 347.134 seconds. That run began before the final denominator clarification and the twentieth new regression test; the final reset-specific suite was subsequently rerun with all 20 tests passing. Release metadata, compilation and whitespace checks passed. Skips cover the optional Python 3.12 cross-interpreter check and two optional native-library checks; this release does not claim to have validated those paths locally.

## Gate decision

**Engineering foundation ready for adapter work; scientific GO remains HOLD.** No new API, model training, external data download, held-out construction, or independent review is included. Protocol v0.1 remains historical design provenance; the implementation choices and denominator clarification are recorded in `SCHEMA_V1.md` and this release.

Outstanding requirements before a development pilot:

| Gate | Concrete next deliverable | Status |
| --- | --- | --- |
| Non-circular adapter | One real development task with the original grader retained and a separately implemented state/trace fact extractor; mutation review of both | pending |
| Structural independence | Three candidate-family dossiers identifying source/license, state/action structure and shared ancestry; reject paraphrase/seed variants | pending |
| Matched systems | Capable Agent and strong public rule with identical interfaces, observations, caps and instrumented usage; expert only as control | pending |
| Independent review | Reviewer checks contract, responsibility, uncertainty and oracle paths before seeing scores; dissent preserved | pending |
| Decision relevance | Freeze what discrepancy would change a real selection decision before observing pilot results | pending |
| Live-run readiness | Written bounded task/system/sample/cost plan and protocol-required review before any API run | pending |

Next increment should implement and review **one** real task adapter, including healthy and ambiguity controls, before adding sources or systems. A synthetic sign reversal is not a reason to authorize an empirical run. The original 2026-11-11 provisional decision horizon is unchanged; it is a planning boundary, not an automatic GO or scheduled action.
