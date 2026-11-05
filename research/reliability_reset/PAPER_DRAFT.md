# Auditing the Evidence for Reliability Gaps in Tool-Using Agents

**Working draft, updated 2026-11-05.** The proposed claim that native full scoring misses consequential reliability violations remains **NO-GO**; the broader research status remains **HOLD**. The original multi-family plan below is historical and is not an approved new run. See the [internal claim review](PAPER_CLAIM_REVIEW_2026_10_27.md), [later blind review and replay](APPWORLD_REVIEW_2026_11_02.md), and [research changelog](CHANGELOG.md) for the underlying records and historical development.

**Verification status:** this is an AI-assisted working draft, not a submission. The two previously returned human blind reviews are recorded in the linked study, but no human has approved these manuscript revisions or independently verified every claim and source locator. Author, institutional, disclosure, and venue requirements remain unconfirmed.

## Abstract

Can an agent receive a full benchmark pass while violating the original task contract? We examined four AppWorld development trajectories selected by their saved scores, with two human reviewers working independently and blind to those scores as confirmed by the project coordinator [E1]. Both reviewed conflicts were associated with native failures; the two native-passing cases showed no violation in the reviewed scopes. The sample was selected by score and does not estimate a benchmark-wide false-success rate. Separately, offline regrading of the same archived states changed two saved passes to failures, while both saved failures remained failures [E2]. An in-memory adaptation of an already proposed upstream zero-counter condition restored the saved passed and failed requirement labels in all four cases [E3]. That is a modified-scorer control, not a reconstruction of the historical runtime or evidence that the original live grading missed a violation. Related work and an upstream issue already cover important parts of the measurement and comparison mechanism [E4, E5]. These observations support a bounded reproducibility case, not an independent benchmark or agent-improvement claim.

## 1. Introduction

Agent benchmarks increasingly execute systems in interactive environments rather than score isolated text answers. AgentBench spans multiple environments; WebArena and τ-bench evaluate long-horizon interaction; AgentDojo studies adversarial tool use; and recent work evaluates trust or inspects tool traces. These approaches establish that agent evaluation must account for interaction, policy, and security. They do not, by themselves, settle a narrower measurement question: when the benchmark's headline outcome says “success,” does that label track whether the run was operationally reliable?

The distinction matters in stateful tools. An agent may produce the requested final report while also publishing an incorrect intermediate version, duplicating a non-idempotent action, or leaving a corrupted artifact. Conversely, an agent may safely stop when an operation's commit state is unknown, and a terminal-only grader may count that as failure even though the system avoided an unsafe write. A single terminal score can therefore hide different operational histories. But this possibility is not itself a contribution. Existing work studies multi-turn reliability, execution traces, security properties, and benchmark/tool contract validity; recent executable-contract audits are especially close to questions about whether benchmark scores reflect actual state.

We propose to test one claim, not to add another catalog of faults:

> **Does outcome-only evaluation make consequential, reproducible errors about tool-agent reliability, and do those errors persist across independent task families?**

The study will be considered useful only if an outcome label disagrees with an independent state-and-trace adjudication in ways that change a practical conclusion—for example, a materially different false-success rate or a robust reversal in system ordering. A discrepancy limited to one synthetic task family, a grader tautology, a changed tool permission, an extra source of help, or an already-known security violation will not pass the novelty gate.

This manuscript records a historical proposal and subsequent development evidence. The blind reviews and the scorer-replay observations address different questions; neither establishes an original benchmark error, RL improvement or cross-task generalization. The current claim decision and provenance are recorded below.

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

The 25 October review also constrains the later local interface-development route. [AFT-Bench](https://arxiv.org/html/2608.23628v2) directly studies controlled operational interface changes, including uncertain effects and policy-correct non-action. [INTENT](https://arxiv.org/html/2602.11541v1) addresses hard-budget tool planning, while [HyperAgent](https://arxiv.org/html/2608.02650v1) addresses schema-dependent planning and execution-state support. Our current implementation supplies no independently established algorithmic increment over these adjacent approaches. The exact section-level comparison and remaining unverified coverage questions are recorded in [DIRECT_COMPARISON_160.md](DIRECT_COMPARISON_160.md).

Later screening also found an [upstream zero-counter issue and proposed fix](https://github.com/StonyBrookNLP/appworld/issues/218), and a [study of regrading and leaderboard instrument errors](https://arxiv.org/html/2611.04399v1) [E4, E5]. Neither examines our exact four archived states. Their prior coverage, combined with the controls below, rules out treating the present replay mechanism as a standalone contribution on the current evidence.

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
| AFT-Bench | Controlled operability interventions, uncertain effects and policy-correct termination | Direct overlap with the current receipt/interface route; no first-operability claim |
| INTENT | Hard-budget inference-time tool planning | Budget salience or affordable-action filtering is not an original planning algorithm |
| HyperAgent | Schema dependencies and state-conditioned tool support | Explicit dependencies, dynamic tool contexts and completion support need a differentiated result |
| EpiSEM-Bench | Missing evidence, useful recovery, false abstention and costs | Combining these existing dimensions is not independently novel |
| AgentAbstain | Should-act/should-abstain pairs and calibrated restraint | A safe-stop pivot needs more than paired abstention metrics |
| TelemetrySuffBench | Observational ambiguity, evidence sufficiency and origin attribution | Evidence-gated diagnosis is already a direct neighboring problem |

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

The following evidence includes retrospective blind reviews and offline scorer controls. It does not include a new independent held-out, cross-task study.

### 5.1 A metric can reverse its apparent interpretation (0.5.60)

In a single scripted development cluster with 72 pre-existing states, the `complete_public_rule` arm obtained 72/72 on `supported_correct_termination`, but the rule and grader called the same public-evidence function; the result was a definitional identity, not independent evidence. A one-sided `actual_safe_completion` metric made `always_stop` appear better than the rule (36/72 versus 24/72), while the omitted side contained 36 unsafe stops. Under the protocol's resolved-state denominator, the rule achieved correct termination on 48/48 and `always_stop` on 24/48. This is a documented evaluator-design failure in one development fixture, not an agent result, not an external benchmark audit, and not cross-task evidence.

### 5.2 Strong fixed rules constrain the old mechanism (0.5.65)

The offline VeriCost study found that, on its preregistered synthetic primary regime, a nine-cell fixed lookup reached normalized regret 0.031539 under the registered 0.05 threshold. Across the full 30-profile development set, the best registered fixed rule had regret 0.014189; the best learned arm, Thompson sampling, had 0.024159, and other learned policies were worse. A separate synthetic D1 pass had only a 0.002296 margin and was overturned under a larger informational fixed-rule family. The registered live hypotheses, new sources, held-out split, and model runs were not executed. This is evidence against continuing the prior mechanism claim, not evidence for H1.

### 5.3 Historical blind review and offline regrading

From one official historical GPT-4o agent archive, four development tasks from different scenarios were selected by their saved native outcomes: two passes and two failures. Two reviewers independently examined the cases without seeing those saved outcomes, according to their forms and coordinator confirmation; three AI opinions were auxiliary. Both cases with reviewed task conflicts were native failures, and neither native-passing case had a confirmed violation within its reviewed scope [E1]. This is not an exhaustive inspection of all possible effects. The raw human review forms are private, so the public bundle cannot independently authenticate the reviews.

The same four saved states were regraded in fresh processes using the released 0.1.0 package and a current local environment. In the unmodified replay, two saved passes became failures and two saved failures remained failures; three of four cases had a changed passed/failed requirement label [E2]. The scores are comparisons on deliberately selected cases, not a population rate. No agent was rerun and no model API was called.

A separate, locally pre-specified control adapted only the zero-counter comparison condition from the already-open upstream PR to the 0.1.0 method in memory. It reproduced the saved passed/failed requirement labels for all four without adding synthetic markers [E3]. This is not a test of the full upstream patch, recovery of the historical counter, or proof of the original runtime identity. Earlier synthetic-marker controls achieved the same check-label agreement for the four cases [E2].

### 5.4 Evidence ledger

| Evidence item | What it supports | What it does not support |
|---|---|---|
| 0.5.60 metric audit | A score/denominator can create a misleading within-fixture comparison | Agent unreliability, other benchmark defects, cross-task replication |
| 0.5.65 offline policy comparison | Cheap fixed rules constrain the old evidence-allocation mechanism | Behavior of an LLM agent or external tasks |
| Existing FaultDA tools | Feasibility of logging durable state, traces, costs, and independent checks | Independent validation of these tools or a new scientific contribution |
| Existing historical model runs | Development diagnostics under their recorded protocols | Reusable confirmatory data; they share task lineage and were used for iteration |
| Four blinded AppWorld development reviews [E1] | Two reviewed conflicts were detected by saved native failures; no reviewed-scope violation was confirmed for the two native passes | A benchmark-wide miss rate, independent verification of private forms, or an out-of-scope no-harm finding |
| Four-case archived-state regrading [E2, E3] | A selected 0.1.0 replay can disagree with saved check labels and binary outcomes; an adaptation of an existing proposed condition matches those labels here | Original live false success, a validated full upstream fix, or an effect on a leaderboard |
| Six-scenario model pilot [E6] | The documented setup produced no native full-score passes; some runs were resource-censored | Comparable model ranking, false-success rate, or cross-task evidence |

All existing results are development evidence. The historical studies must not be pooled into a synthetic cross-task sample.

### Evidence locators for this update

The records below identify sources for the new claims; links and counts were checked locally, but a human manuscript verifier has not yet signed off on the updated claims.

| ID | Source | Role |
|---|---|---|
| E1 | [Blind review and replay report](APPWORLD_REVIEW_2026_11_02.md) | Sampling, human-review scope, and limitations |
| E2 | [Original encrypted review/replay bundle](evidence/appworld-review-2026-11-02.bundle) | Saved and unmodified replay results, plus synthetic-marker control |
| E3 | [Encrypted upstream-condition control bundle](evidence/appworld-pr219-control-2026-11-05.bundle) | Local protocol, adapted-condition results, and replay script |
| E4 | [AppWorld issue #218](https://github.com/StonyBrookNLP/appworld/issues/218) and [PR #219](https://github.com/StonyBrookNLP/appworld/pull/219) | Prior public report and proposed zero-counter condition |
| E5 | [Liu, 2026](https://arxiv.org/html/2611.04399v1) | Prior leaderboard and regrading measurement study |
| E6 | [Six-scenario pilot](APPWORLD_PILOT_115.md) | Model outcomes, unequal limits, and cost scope |

## 6. Three-week falsification plan (historical proposal)

The schedule below was proposed before the later AppWorld review and novelty screen. It is retained for context and is not an instruction to expand tasks, contact providers, or start a new clock; the current decision is NO-GO for the existing paper claim.

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

The central claim is not established. The current project has one dominant application family, development data repeatedly used during iteration, a history of changing metric definitions, and no new held-out model run. The four blind reviews do not establish an original-score false success, and the separate regrading discrepancy is partly explained by a publicly reported comparison condition. Existing 0.5.60 evidence is program-generated and single-cluster. Existing 0.5.65 evidence is offline and explicitly non-generalizing. The nearest prior work covers much of the proposed score/state discrepancy. A future pilot would require a differentiated, independently reviewed design before execution.

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
15. Wang, Zihao. “Callability Is Not Operability: Controlled Interface Interventions for LLM Agents.” 2026 preprint, v2. [arXiv:2608.23628v2](https://arxiv.org/abs/2608.23628v2).
16. Liu, Hanbing, et al. “Budget-Constrained Agentic Large Language Models: Intention-Based Planning for Costly Tool Use.” 2026 preprint, v1. [arXiv:2602.11541v1](https://arxiv.org/abs/2602.11541v1).
17. Zhai, Zian, et al. “HyperAgent: Planning and Acting over Tool-Schema Hypergraphs for Tool-Use LLM Agents.” 2026 preprint, v1. [arXiv:2608.02650v1](https://arxiv.org/abs/2608.02650v1).
18. Zhang, Qijin, et al. “EpiSEM-Bench: Evaluating Safety and Evidence Recovery in LLM Agents under Missing Evidence.” 2026 preprint, v1. [arXiv:2610.31650v1](https://arxiv.org/abs/2610.31650v1).
19. Liu, Xun, et al. “AgentAbstain: Do LLM Agents Know When Not to Act?” 2026 preprint, v1. [arXiv:2607.10059v1](https://arxiv.org/abs/2607.10059v1).
20. Zhu, Yuxuan, and Peng Pu. “TelemetrySuffBench: Is Agent Telemetry Sufficient for Failure-Origin Diagnosis?” 2026 preprint, v1. [arXiv:2608.07899v1](https://arxiv.org/abs/2608.07899v1).
21. Liu, Yangze. “Silent Instrument Errors Reorder Agent Leaderboards.” 2026 preprint, v1. [arXiv:2611.04399v1](https://arxiv.org/abs/2611.04399v1).
22. Kassis, T., Agarwal, V., He, Y., Patel, D., and Brueckner, A. M. “Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents.” 2026. [arXiv:2609.00065](https://arxiv.org/abs/2609.00065). This writing workflow was used for the 2026-11-05 revision.

## Venue positioning (provisional)

NeurIPS E&D is a fit only if the final work yields a broadly useful evaluation methodology, released and independently auditable task assets, and evidence across task families. KDD D&B may fit if the benchmark's data lineage, task construction, and empirical use are the central contribution. At current maturity, neither fit is demonstrated. Revisit venue selection after the pilot; do not optimize the manuscript for a track before there is a non-overlapping result.
