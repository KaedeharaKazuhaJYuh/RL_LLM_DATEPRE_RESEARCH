# 1.0.05 technical/scientific decision — 2026-10-23

**GO:** offline adapter validation and independent review preparation.
**NO-GO:** paid/live model execution, held-out expansion and a claim of a new evaluation mechanism.
**Scientific status:** HOLD. Independent review: pending. New API budget approved by this record: **0 requests / 0 spend**.

## Evidence behind the decision

The adapter executes one known development task through real CSV and SQLite operations and reconstructs relevant facts without importing the existing oracle or tool math. This closes the first release's implementation gap: imported facts can now be traced back to original artifacts for this supported task.

The deliberately repaired wrong publication has `contract_complete=true`, but the original oracle also has `safe_complete=false` and `forbidden_effect=true`. The new extractor agrees. Thus, selecting only the old terminal submetric would reproduce a distinction the old benchmark already reports. It cannot be presented as a newly discovered defect or a reason to fund model runs.

Both arms are deterministic programs; the stress sequence is designed to violate the contract. The conditions are developer controls, not natural failure prevalence estimates. There is no capable LLM arm, cross-model comparison, independent task family, blinded adjudication, novel decision-impact result or reviewed sample-size plan.

## Next bounded step

Prepare one review package for the existing adapter and a candidate-family **design dossier**, without creating a new task set. A candidate must identify an actually used outcome-only scoring decision, original task/side-effect contracts, a source-independent state/action structure, licensing, and an externally checkable effect. The reviewer should be able to reject the candidate if existing full metrics already cover it.

Do not expand sources in response to this engineered positive control. Revisit empirical GO only if a reviewed candidate has a discrepancy that survives use of all relevant original metrics, an identical-budget public rule and unambiguous responsibility. A subsequent run memo must freeze systems, sample allocation, decision-relevance threshold, provider request/token/spend ceilings and human/scientific review. None is approved by this document.

The 2026-11-11 provisional reset decision boundary remains in place; it is not an automatic authorization or scheduled execution.

## Same-version novelty/design review — 2026-10-23

The focused review in `NOVELTY_REVIEW_2026_10_23.md` adds direct prior work on evidence bounds/ranking, state-based damage, evaluator validity, assessment binding and oracle integrity. The current broad originality claim fails this internal screen. `CANDIDATE_SCREEN_2026_10_23.md` considers three structurally different sources but admits zero designs: no precise gap beyond full original metrics and close work is established. This is a bounded design screen, not a full code audit or independent scientific verdict.

The existing sixteen engineering controls and validation are unchanged. No new execution, dataset acquisition, model request or approval is added. The route remains engineering/review preparation only. New independent technical/scientific opinions are pending in `FOCUSED_REVIEW_105.md`.
