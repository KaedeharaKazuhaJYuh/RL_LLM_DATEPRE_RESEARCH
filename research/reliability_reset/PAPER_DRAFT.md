# When Passing Is Not Reliable: Auditing Outcome-Based Evaluation of Tool-Using Agents

**Working manuscript — evidence and protocol draft, 21 October 2026**
**Intended venues:** NeurIPS 2027 Evaluations & Datasets / KDD 2027 Datasets & Benchmarks
**Status:** not submission-ready; no independent cross-task experiment has been run. Venue choice and formatting are deferred until the study passes its preregistered decision gate.

**Novelty decision (2026-10-23, within 1.0.05):** the present broad claim has not passed its novelty gate. The focused review in `NOVELTY_REVIEW_2026_10_23.md` identifies additional direct overlap. All empirical expansion stages below remain conditional; no candidate currently qualifies for execution. This manuscript is retained as an engineering/protocol draft, not a paper with an established original contribution.

**Technical-review correction (1.0.10, 2026-10-23):** a user-supplied review explicitly authored by an agent identified control-coverage, class-balance and disclosure issues. Source-level checks support several findings and qualify others; the original completion score was 14/16, while all sixteen physical snapshots were correct. The new engineering derivative separates snapshot truth from captured termination and adds missing controls. These changes add no scientific result or independent human approval. Database/distributed-systems context is recorded in `SYSTEMS_CONTEXT_110.md`; the current sequential application-level fault controls are not concurrency or storage-crash verification.

**Implementation update (2026-10-22):** Reliability Reset 1.0.0 provides an offline artifact importer, reliability classifier, descriptive paired analysis and source-review export. Its twenty hand-built records are software controls from one synthetic family, not an empirical pilot. No new model evidence, reviewer approval or hypothesis confirmation is added to this manuscript. Implementation semantics are specified in `SCHEMA_V1.md`; the original proposal remains subject to review.

**Adapter update (2026-10-23):** 1.0.05 adds real CSV/SQLite execution and a separately implemented state/trace extractor for one historical group task. Sixteen programmatic controls validate the adapter. The original oracle's safety metric already detects the deliberate repaired-history violation, so this is not a new benchmark defect or a positive scientific pilot. Paid/live model execution remains NO-GO; independent review is pending.

## Abstract

Interactive benchmarks commonly reduce an agent run to whether a requested end state was achieved. That summary can be inadequate when an agent reaches the requested state while causing an irreversible side effect, or when it fails to reach the state despite following a safe and recoverable process. Whether this creates a practically important, cross-task evaluation error remains an open empirical question. We propose an audit of outcome-based agent evaluation that compares terminal-state scores with independently verified execution histories and durable effects under matched tasks, tools, and budgets. The study asks whether outcome-only evaluation produces consequential false-success judgments or changes comparisons between agents, and whether any such discrepancy recurs across independent task families. Our current FaultDA-Bench infrastructure provides a useful development testbed: it records tool traces, persistent state, publication effects, and independent checks. However, the available results do not establish the proposed claim. A 0.5.60 development analysis exposed a tautological score and a one-sided safety metric in one scripted task cluster; a 0.5.65 offline policy study found that a cheap fixed rule matched the registered threshold on its primary synthetic regime and that no learned arm beat the best fixed rule. These are measurement warnings, not cross-task evidence about real agents. We therefore specify a small, time-bounded falsification study with independent task clusters, state-based adjudication, paired outcome/reliability scores, and explicit stop criteria. If the pilot cannot show a material and reproducible discrepancy beyond known benchmark-audit and trajectory-evaluation work, we will retain the infrastructure as an engineering benchmark and stop pursuing the top-venue mechanism claim.

## 1. Introduction

Agent benchmarks increasingly execute systems in interactive environments rather than score isolated text answers. AgentBench spans multiple environments; WebArena and τ-bench evaluate long-horizon interaction; AgentDojo studies adversarial tool use; and recent work evaluates trust or inspects tool traces. These approaches establish that agent evaluation must account for interaction, policy, and security. They do not, by themselves, settle a narrower measurement question: when the benchmark's headline outcome says “success,” does that label track whether the run was operationally reliable?

The distinction matters in stateful tools. An agent may produce the requested final report while also publishing an incorrect intermediate version, duplicating a non-idempotent action, or leaving a corrupted artifact. Conversely, an agent may safely stop when an operation's commit state is unknown, and a terminal-only grader may count that as failure even though the system avoided an unsafe write. A single terminal score can therefore hide different operational histories. But this possibility is not itself a contribution. Existing work studies multi-turn reliability, execution traces, security properties, and benchmark/tool contract validity; recent executable-contract audits are especially close to questions about whether benchmark scores reflect actual state.

We propose to test one claim, not to add another catalog of faults:

> **Does outcome-only evaluation make consequential, reproducible errors about tool-agent reliability, and do those errors persist across independent task families?**

The study will be considered useful only if an outcome label disagrees with an independent state-and-trace adjudication in ways that change a practical conclusion—for example, a materially different false-success rate or a robust reversal in system ordering. A discrepancy limited to one synthetic task family, a grader tautology, a changed tool permission, an extra source of help, or an already-known security violation will not pass the novelty gate.

This manuscript is a proposal with a limited retrospective development audit. Its current outputs are a measurement question, an engineering adjudication/comparison protocol, and recorded go/no-go conditions. These are useful project artifacts; the present evidence does not establish them as original scientific contributions. The focused review below strengthens the reason to withhold claims of a new benchmark result, mechanism, RL improvement or generalization.

## 2. Research questions and falsifiable hypotheses

### RQ1: Outcome-score validity

Among runs labeled successful by a benchmark's ordinary terminal-state evaluator, what fraction contains an independently verified reliability violation that matters under the task contract?

Define the **false-success rate** for task cluster (k):

\[
FSR_k = \frac{\#\{i: O_i=1,\ R_i=0\}}{\#\{i: O_i=1\}},
\]

where (O_i) is the benchmark's frozen outcome score and (R_i=0) means an independently adjudicated contract-level reliability violation. `unresolved` cases are excluded from the point estimate but reported separately with best/worst-case sensitivity bounds; they must never be silently coded as violations or discarded. Safe non-completion is not a false success. Report its denominator and interval; do not merge task families or treat repeated seeds as independent tasks.

### RQ2: Decision impact

Does replacing outcome-only scoring with state-and-trace scoring materially change a comparison between agents or agent systems under the same tool permissions and resource limits? Report both orderings and their cluster-level paired uncertainty. A score difference without a decision change or a task-contract consequence is descriptive only.

### RQ3: Cross-task stability

Does a predeclared discrepancy recur in independent task families with separate data/task lineage, state machines, and outcome oracles? Stability is a claim over families, not prompt paraphrases, seeds, fault variants, or sources inside one application family.

**Candidate hypothesis H1 (kept conditional):** outcome-only evaluation has a non-negligible false-success rate and/or changes at least one practically relevant agent comparison in a direction consistent across the preregistered task families.

**Null / stopping hypothesis H0:** observed disagreements are rare, task-local, explained by known grader/tool-contract defects, or disappear under a strong matched rule and independent adjudication. H0 is a valid result and triggers scope reduction; it is not an invitation to invent a new mechanism post hoc.

Before any confirmatory run, reviewers must set the smallest practically meaningful threshold for FSR and comparison reversal, agree on the harm taxonomy, and approve the cluster-level analysis. This draft intentionally leaves those numerical thresholds **unfrozen**; selecting them after seeing outcomes would invalidate confirmation.

## 3. Related work and the novelty boundary

Interactive benchmarks such as AgentBench, WebArena, and τ-bench broaden evaluation beyond static question answering. τ-bench explicitly studies tool-agent-user interaction and repeated-run reliability. AgentDojo evaluates task utility together with prompt-injection security. These works mean that “agents need interactive reliability evaluation” is not a novel claim.

Trajectory-centric evaluation is also established. AgentAudit describes full-lifecycle trace dimensions and failure attribution; formal runtime-monitoring work evaluates action-history properties; and safety/security benchmarks can report policy violations that a task-success score does not encode. Consequently, simply adding trace labels, failure categories, or a safe-stop metric would be insufficient novelty.

The earlier comparison concentrated on executable-contract audits and recovery benchmarks. That is insufficient after the 23 October screen. [Evidence-Supported Bounds](https://arxiv.org/html/2605.10448v1) keeps native scores beside an evidence assessment and addresses uncertainty and ranking support. [AgentRelBench](https://arxiv.org/html/2608.15286v1) separately measures task success and state-based damage. [Tool-Veritas](https://arxiv.org/html/2607.02577v1) examines evaluator validity, including rejection of valid alternatives. [AgentEval](https://arxiv.org/html/2610.21177v1) distinguishes behavior, evidential support and assessment qualification. These are direct constraints on the current framing, not merely background citations.

The earlier proposed paired misclassification/decision-impact design is therefore not currently a demonstrated distinction. Comparing more task families alone would not establish a novel mechanism or evaluation methodology. A future proposal would need an exact original task, its full metric suite, a contract-grounded consequential disagreement and a specific gap relative to these works. The present engineering controls supply none of that incremental evidence. The manuscript remains an engineering/protocol draft while that gate is unresolved.

| Work | What it already covers | Implication for this study |
|---|---|---|
| AgentBench / WebArena | Interactive tasks and task-completion evaluation | Do not claim interaction itself is new |
| τ-bench | Tool-agent-user interaction and multi-run reliability | Compare exact reliability estimand and task setup |
| AgentDojo | Task utility paired with security violations | Security-only discrepancy is not sufficient novelty |
| AgentAudit and runtime monitors | Trace dimensions, policy properties, failure attribution | Adding trace labels alone is not enough |
| Executable-contract benchmark audit (2026) | Tool implementation/advertised contract and score provenance defects | Closest overlap; must be addressed directly before any GO |
| FaultDA-Bench 0.5.65 | State, tool, replay, and offline cost infrastructure; no held-out experiment | Infrastructure only; no cross-task conclusion |
| Evidence-Supported Bounds | Native/evidence views, Unknown cases and supported ranking | Dual scoring and missingness bounds are not standalone novelty |
| AgentRelBench | Success/damage separation using state differences | Collateral damage and single-run misses require direct comparison |
| Tool-Veritas | Evaluator validity, path rigidity and decomposed scoring | A false-negative pivot is not automatically novel |
| AgentEval | Contract-bound evidence/assessment semantics | Binding and assessment records are existing close work |
| Oracle-integrity study, v2 | Stateful-oracle checks and corrected comparison | Mutation checks or ranking changes alone do not distinguish this draft |

## 4. Study design (proposed, not yet run)

### 4.1 Unit and matched comparison

The inferential unit is a **task instance nested in an independently sourced task family**. Each evaluated system receives the same task specification, observable state, tool interface, action cap, token/compute cap, and environment seed. Run-level data include the original benchmark score, complete ordered tool trace, before/after durable state, externally visible side effects, costs, and the adjudicator's evidence references.

At least two systems should be compared to make score-ordering effects testable: a capable agent and a strong public rule or reference system that uses only the same public observations and tools. A scripted expert oracle may validate task solvability but cannot be compared as a model. If only one agent can be evaluated, the study can estimate misclassification but cannot make a ranking-reversal claim.

### 4.2 Independent reliability adjudication

Reliability is a task-contract judgment over observable evidence, not a second language-model opinion. A machine-checkable adjudicator should inspect:

1. whether required terminal artifacts and values are correct;
2. whether any irreversible, duplicate, unauthorized, or invalid intermediate effect occurred;
3. whether writes/commits are supported by the actual environment state, rather than the agent's text or an unverified tool receipt;
4. whether a stop or escalation was permitted by the public contract and available evidence; and
5. whether an apparent failure was safe, recoverable, and correctly reported.

The outcome grader and reliability adjudicator must not share the function, reference data, or label path that produces the score being audited. The benchmark's original outcome score remains unchanged and is stored alongside the independent label. Ambiguous cases are marked unresolved and receive blinded human adjudication; they must not be silently dropped after outcomes are known.

### 4.3 Task-family independence and data lineage

The development pilot should span at least three structurally different task families and should use frozen source lineage, task-generation scripts, licenses, input hashes, and oracle definitions. Examples of family candidates include persistent data/report updates, transactional workflow tools, and repository or environment-state changes. These are candidates, not approved datasets; their inclusion depends on verifying licenses, feasibility, a genuinely different state/action structure, and no contamination from the current agent's training or development.

Three families can reveal feasibility and obvious task-locality, but they are not enough for a broad stability claim. A confirmatory study should target at least six independent families across at least three application types, with adequate task clusters justified by power/sensitivity analysis. Family count—not the number of paraphrases, seeds, or fault variants—drives cross-task uncertainty.

### 4.4 Measures

- **Outcome success:** the benchmark's frozen primary score.
- **Reliable success:** required terminal outcome achieved with no prohibited durable effect and correct termination/reporting.
- **False-success rate:** outcome-success runs that fail independent reliability adjudication.
- **Safe non-completion:** no success, but no prohibited effect and a justified stop/escalation.
- **Unsafe-effect rate:** runs with a prohibited or materially harmful persistent effect, whether or not the final state passes.
- **Decision impact:** paired change in agent ordering under outcome-only vs reliability-aware scoring, with task-family cluster intervals.
- **Cost:** model/token/compute, calls, tool reads/writes, elapsed time, and adjudication cost reported separately.

Do not collapse false success and safe non-completion into one score without preregistered utility weights. Report per-family confusion tables and missing/ambiguous cases.

### 4.5 Analysis and safeguards

Freeze the systems, prompts, task set, rules, thresholds, and analysis plan before confirmatory evaluation. Keep development and final task families separate. Compute paired estimates within family; aggregate with family as the top-level resampling unit. Report raw counts, intervals, and all per-family effects, including negative and contradictory results. Where exact inference has too few clusters, state that the study is descriptive rather than implying population-level stability.

Preregister control checks for evaluator tautology, label leakage, shared-code oracle, tool contract divergence, unequal help, uncounted computation, and action-source ambiguity. Preserve full traces with secrets redacted, and publish a reproducible manifest, adjudication rules, and safe-to-release evidence. A local hash verifies artifact identity; it does not prove historical immutability or vendor response authenticity.

## 5. Existing evidence: development audit only

No new independent experiment has been run for this manuscript. The following repository results motivate the question but cannot answer it.

### 5.1 A metric can reverse its apparent interpretation (0.5.60)

In a single scripted development cluster with 72 pre-existing states, the `complete_public_rule` arm obtained 72/72 on `supported_correct_termination`, but the rule and grader called the same public-evidence function; the result was a definitional identity, not independent evidence. A one-sided `actual_safe_completion` metric made `always_stop` appear better than the rule (36/72 versus 24/72), while the omitted side contained 36 unsafe stops. Under the protocol's resolved-state denominator, the rule achieved correct termination on 48/48 and `always_stop` on 24/48. This is a documented evaluator-design failure in one development fixture, not an agent result, not an external benchmark audit, and not cross-task evidence.

### 5.2 Strong fixed rules constrain the old mechanism (0.5.65)

The offline VeriCost study found that, on its preregistered synthetic primary regime, a nine-cell fixed lookup reached normalized regret 0.031539 under the registered 0.05 threshold. Across the full 30-profile development set, the best registered fixed rule had regret 0.014189; the best learned arm, Thompson sampling, had 0.024159, and other learned policies were worse. A separate synthetic D1 pass had only a 0.002296 margin and was overturned under a larger informational fixed-rule family. The registered live hypotheses, new sources, held-out split, and model runs were not executed. This is evidence against continuing the prior mechanism claim, not evidence for H1.

### 5.3 Current evidence ledger

| Evidence item | What it supports | What it does not support |
|---|---|---|
| 0.5.60 metric audit | A score/denominator can create a misleading within-fixture comparison | Agent unreliability, other benchmark defects, cross-task replication |
| 0.5.65 offline policy comparison | Cheap fixed rules constrain the old evidence-allocation mechanism | Behavior of an LLM agent or external tasks |
| Existing FaultDA tools | Feasibility of logging durable state, traces, costs, and independent checks | Independent validation of these tools or a new scientific contribution |
| Existing historical model runs | Development diagnostics under their recorded protocols | Reusable confirmatory data; they share task lineage and were used for iteration |

All existing results are development evidence. The historical studies must not be pooled into a synthetic cross-task sample.

## 6. Three-week falsification plan

The three-week clock begins when the reset protocol is frozen. A provisional decision date is **11 November 2026**.

| Window | Work | Exit condition |
|---|---|---|
| Days 1–4 | Compare the estimand and protocol with τ-bench, AgentAudit/runtime-monitoring work, and the 2026 executable-contract audit; freeze claim and novelty boundary | A reviewer can name the exact non-overlap; otherwise stop the paper route |
| Days 5–8 | Select three candidate task families; document lineage, license, tool state machine, outcome oracle and reliability oracle; implement adjudicator on hand-authored positive/negative controls | All controls pass; outcome and reliability scoring paths demonstrably independent |
| Days 9–12 | Lock matched systems, budgets, sample plan, thresholds, and analysis; dry-run without model calls using deterministic fixtures | No evaluator tautology, leakage, unequal help, or unresolved contract ambiguity |
| Days 13–17 | If the local pilot is authorized and feasible, run a small paired development set; preserve all traces and costs | At least one material discrepancy is observed and independently attributable in more than one family; otherwise no expansion |
| Days 18–21 | Review negative controls, family-level effects, costs, and close-work overlap; write decision memo | GO only to a separate held-out, cross-model design; otherwise HOLD/engineering-only pivot |

**Pilot decision rule (thresholds to be signed before the run):** GO requires (a) at least one discrepancy beyond a known tool-contract defect or security-only category, (b) an independently verifiable persistent-state or action-history consequence, (c) recurrence in at least two of the three pilot families, (d) no disappearance under a same-permission strong rule and blinded adjudication, and (e) a credible path to a held-out set with enough independent families. This is only a design-screening gate; it cannot establish cross-task generalization. If any condition fails, stop expansion and retain an engineering benchmark.

No external dataset download, paid provider request, fine-tuning, or test-set construction is authorized by this draft. Any such step requires a later explicit go decision after the design and cost are concrete.

## 7. Limitations and current conclusion

The central claim is not established. The current project has one dominant application family, development data repeatedly used during iteration, a history of changing metric definitions, and no new held-out model run. Existing 0.5.60 evidence is program-generated and single-cluster. Existing 0.5.65 evidence is offline and explicitly non-generalizing. The nearest prior work may cover much of the proposed score/state discrepancy. A three-family pilot would only test feasibility and initial recurrence; it would not support a top-venue stability claim.

Accordingly, this manuscript is a **research proposal plus a transparent development audit**, not a completed benchmark paper. It is not ready to claim NeurIPS or KDD contribution. The next substantive progress must come from passing or failing the predeclared measurement-validity gate, not from another code release.

## References

1. Liu et al. “AgentBench: Evaluating LLMs as Agents.” ICLR 2024. [arXiv:2308.03688](https://arxiv.org/abs/2308.03688).
2. Zhou et al. “WebArena: A Realistic Web Environment for Building Autonomous Agents.” ICLR 2024. [arXiv:2307.13854](https://arxiv.org/abs/2307.13854).
3. Yao et al. “τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains.” ICLR 2025. [arXiv:2406.12045](https://arxiv.org/abs/2406.12045).
4. Debenedetti et al. “AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents.” NeurIPS 2024 Datasets & Benchmarks. [arXiv:2406.13352](https://arxiv.org/abs/2406.13352).
5. Nag et al. “AgentAudit: An Open, Extensible Framework for Full-Lifecycle Trust Evaluation of AI Agents.” 2026 preprint. [arXiv:2609.09875](https://arxiv.org/abs/2609.09875).
6. Bellibatlu, Wang, and Zhang. “Do Agent Benchmarks Do What They Say? An Executable-Contract Audit of Tool-Using Agent Environments.” 2026 preprint. [arXiv:2609.37315](https://arxiv.org/abs/2609.37315).
7. Kekatos et al. “Formal Runtime Verification for Tool-Using LLM Agents: An Offline Same-Benchmark Study on AgentDojo and STAC.” 2026 preprint. [arXiv:2610.09793](https://arxiv.org/abs/2610.09793).
8. FaultDA-Bench. “0.5.60-dev: Frozen-Result Uncertainty Reporting and Metric-Semantics Audit.” Internal development report, 2026-10-20.
9. FaultDA-Bench. “0.5.65-dev: Offline Verification-Cost Diagnosis.” Internal development report, 2026-10-21.
10. Gao and Zhou. “Can Agent Benchmarks Support Their Scores? Evidence-Supported Bounds for Interactive-Agent Evaluation.” 2026 preprint, v1. [arXiv:2605.10448v1](https://arxiv.org/abs/2605.10448v1).
11. Khurdi. “No Task Fails Every Time: Why One-Shot Audits Are Structurally Blind to Agent Damage.” 2026 preprint, v1. [arXiv:2608.15286v1](https://arxiv.org/abs/2608.15286v1).
12. Bhat et al. “Benchmarking the Benchmarks: A Validity Audit of Tool-Calling Evaluation.” 2026 preprint, v1. [arXiv:2607.02577v1](https://arxiv.org/abs/2607.02577v1).
13. Gao. “AgentEval: Evidence-Bounded Assessment of Stateful Agents.” 2026 preprint, v1. [arXiv:2610.21177v1](https://arxiv.org/abs/2610.21177v1).
14. Chen. “When Agent Evaluation Becomes Unreliable: An Empirical Study of Oracle Failures and Configuration-Dependent Measurement in an LLM Agent Benchmark.” 2026 preprint, v2. [arXiv:2610.16067v2](https://arxiv.org/abs/2610.16067v2).

## Venue positioning (provisional)

NeurIPS E&D is a fit only if the final work yields a broadly useful evaluation methodology, released and independently auditable task assets, and evidence across task families. KDD D&B may fit if the benchmark's data lineage, task construction, and empirical use are the central contribution. At current maturity, neither fit is demonstrated. Revisit venue selection after the pilot; do not optimize the manuscript for a track before there is a non-overlapping result.
