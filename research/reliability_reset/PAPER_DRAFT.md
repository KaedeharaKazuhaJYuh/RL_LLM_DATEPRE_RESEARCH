# Auditing the Evidence for Reliability Gaps in Tool-Using Agents

**[事实 / 推断 / 待补] Venue-neutral working draft, updated 2026-11-06.** The proposed claim that native full scoring misses consequential reliability violations remains **NO-GO**; the broader research status remains **HOLD**. The original multi-family plan below is historical and is not an approved new run. See the [internal claim review](PAPER_CLAIM_REVIEW_2026_10_27.md), [blind review and four-case replay](APPWORLD_REVIEW_2026_11_02.md), [147-case replay census](APPWORLD_CENSUS_2026_11_06.md), and [research changelog](CHANGELOG.md) for the underlying records and historical development. **[待补] Target venue: user confirmation.**

**[事实 / 待补] Verification status:** this is an AI-assisted working draft, not a submission. The two previously returned human blind reviews are recorded in the linked study, but no human has approved these manuscript revisions or independently verified every claim and source locator. Author, institutional, disclosure, and venue requirements remain unconfirmed. Both the 147-case AppWorld census and the 2,624-trajectory τ²-bench analysis are offline reanalyses of archived outputs; neither involved a new task execution or model run.

**Evidence labels:** `[事实]` denotes a statement directly supported by a cited project record or primary source; `[推断]` denotes interpretation or a research-design judgment; `[待补]` denotes evidence, verification, or a decision not yet available. Labels are placed at paragraph or table-row level; mixed paragraphs carry more than one label. Bibliography entries inherited from project materials remain subject to final source-by-source verification.

## Abstract

**[事实]** This manuscript reports an AppWorld retrospective replay and a τ²-bench archive reanalysis. In four score-stratified AppWorld cases, two human reviewers found conflicts only in cases that had failed native grading; unmodified offline replay changed two saved passes to failures, while a locally adapted upstream predicate restored saved check labels in all four [E1–E3]. A separate AppWorld census replayed all 147 archived train/dev tasks from the same GPT-4o ReAct lineage: 51 of 76 saved passes became replay failures, no saved failure became a replay pass, and exact check-label lists matched in 38/147 cases [E9]. **[事实]** An independent event-order implementation applied to 2,624 published τ²-bench trajectories reproduced the prior report's 11/1,755 native-pass violations and 13/869 native-fail violations; subtracting those pass violations did not change within-domain observed result-group order [E10]. The τ²-bench rule and result were already reported by prior work [E10]. **[推断]** The AppWorld replay results establish sensitivity to replay conditions, not an original live-evaluator miss; the τ²-bench reanalysis confirms a previously reported narrow event-order discrepancy but shows no result-group order change under that rule. **[待补]** A top-conference claim requires an incremental finding that changes an evaluation conclusion beyond these works.

**[推断] Current contribution decision:** no scientifically novel contribution is established. The following are evidence-backed statements about the project artifacts, not claims of priority or novelty:

1. **[事实]** Two reviewed task conflicts among four score-stratified historical cases were paired with saved native failures; **[推断]** this does not estimate false-success prevalence [E1].
2. **[事实]** In these four cases, unmodified offline replay changed two saved passes to failures; a modified predicate control restored saved check labels in all four [E2, E3].
3. **[事实]** The project releases encrypted, locally re-runnable materials for the four-case replay and predicate control [E2, E3].

**[待补]** Whether any statement merits a paper contribution remains unresolved pending independent literature review and evaluation against the confirmed target venue.

## 1. Introduction

**[事实]** AgentBench spans multiple environments; WebArena and τ-bench evaluate interactive tasks; AgentDojo studies adversarial tool use; and cited work evaluates trust and tool traces [1–7]. **[推断]** These approaches motivate a narrower measurement question: when a benchmark reports “success,” does that label track operational reliability?

**[推断]** In stateful tools, a requested final artifact can coexist with a harmful intermediate side effect, while a safe stop after an uncertain commit can be scored as non-completion. A terminal score may therefore hide different histories, but that possibility is not itself a contribution. **[事实]** Existing work studies multi-turn reliability, traces, security, and benchmark/tool contracts [3–7, 10–20].

**[待补] Proposed question, not an established result:**

> **[待补：待验证研究问题] Does outcome-only evaluation make consequential, reproducible errors about tool-agent reliability, and do those errors persist across independent task families?**

**[推断]** The study would be useful only if an outcome label disagreed with independent state-and-trace adjudication in a way that changes a practical conclusion. A discrepancy limited to one synthetic task family, a grader tautology, changed tool permissions, unequal help, or an already-known security violation would not pass the novelty gate.

**[事实]** This manuscript records a historical proposal and subsequent development evidence. The blind reviews and scorer-replay observations address different questions; neither establishes an original benchmark error, RL improvement, or cross-task generalization. The current claim decision and provenance are recorded below.

## 2. Background & Motivation

**[事实]** The local AppWorld archive contains official historical train/dev task outputs, saved evaluation reports, and per-task database snapshots for one GPT-4o (2024-05-13) ReAct Code Agent lineage [E1, E9]. The current offline replay applies the released AppWorld 0.1.0 scorer to these saved databases; it does not re-execute the archived agent trajectory.

**[推断]** A saved report and a later replay answer different questions when the archive omits runtime metadata used by a state-change check. Therefore, score reproduction must be distinguished from evaluating the original live run. The census below measures the former only.

## 3. Research questions and falsifiable hypotheses

### RQ1: Outcome-score validity [待补：待验证]

**[待补]** Among runs labeled successful by a benchmark's ordinary terminal-state evaluator, what fraction contains an independently verified reliability violation that matters under the task contract?

**[待补: proposed estimand]** Define the **false-success rate** for task cluster (k):

\[
FSR_k = \frac{\#\{i: O_i=1,\ R_i=0\}}{\#\{i: O_i=1\}},
\]

**[待补: protocol]** Here, (O_i) is the benchmark's frozen outcome score and (R_i=0) means an independently adjudicated contract-level reliability violation. The proposed protocol keeps `unresolved` cases separate and reports sensitivity bounds; safe non-completion is not a false success. Denominators, intervals, and family-level units must be frozen before a confirmatory run.

### RQ2: Decision impact [待补：待验证]

**[待补]** Does replacing outcome-only scoring with state-and-trace scoring materially change a comparison between agents or agent systems under the same tool permissions and resource limits? A confirmatory protocol would report both orderings and cluster-level paired uncertainty; a score difference without a decision change or task-contract consequence is descriptive only.

### RQ3: Cross-task stability [待补：待验证]

**[待补]** Does a predeclared discrepancy recur in independent task families with separate data/task lineage, state machines, and outcome oracles? Stability must be assessed across families, not prompt paraphrases, seeds, fault variants, or sources within one application family.

**[推断 / 待补] Candidate hypothesis H1 (conditional):** outcome-only evaluation has a non-negligible false-success rate and/or changes at least one practically relevant agent comparison consistently across preregistered task families.

**[推断 / 待补] Null / stopping hypothesis H0:** observed disagreements are rare, task-local, explained by known grader/tool-contract defects, or disappear under a strong matched rule and independent adjudication. H0 is a valid result and triggers scope reduction; it is not an invitation to invent a new mechanism post hoc.

**[待补]** Before any confirmatory run, reviewers must set the smallest practically meaningful threshold for FSR and comparison reversal, agree on the harm taxonomy, and approve the cluster-level analysis. Those numerical thresholds remain **unfrozen**; selecting them after seeing outcomes would invalidate confirmation.

## 4. Related work and the novelty boundary

**[事实]** AgentBench, WebArena, and τ-bench evaluate interactive tasks; τ-bench studies tool-agent-user interaction and repeated-run reliability, and AgentDojo pairs task utility with prompt-injection security [1–4]. **[推断]** “Agents need interactive reliability evaluation” is not a novel claim.

**[事实]** The τ²-bench Issue #298 and its companion `llmcontract-tau2` report the same confirmation-before-mutation rule violation on 2,624 published trajectories across four model result groups and two domains; the reported passing-trajectory count is 11/1,755 [E10]. Our separate event-order implementation reproduced the reported 11/1,755 and 13/869 counts, but the within-domain ordering did not change after subtracting observed pass violations. **[推断]** This close prior result directly overlaps the proposed outcome-versus-procedure discrepancy. The reanalysis is a computational reproduction on the same archived trajectories, not independent data collection or independent human adjudication.

**[事实]** A targeted archived airline task-2 trajectory has `reward=1.0`, two stored unmet natural-language assertions, and `reward_basis=[DB, COMMUNICATE]`. The nearest recoverable v0.1.0 task definition expects a $50 certificate while including an assertion against offering compensation before the user asks; the later v1.0.1 definition changes task 2 to no compensation when the user will not change or cancel. Upstream Issue #384 lists the later airline T2 among reward-basis omissions [E11]. **[待补]** The archived run's exact task-source commit is unavailable, and its unmet assertions have not received independent adjudication. **[推断]** This is a version-sensitive, potentially unscored task-contract case; the broad reward-basis mechanism is already covered by Issue #384, so this episode does not establish an independent contribution.

**[事实]** A static comparison of τ²-bench task data in v0.1.0 and v1.0.1 found changed selected contract fields in 29/50 airline tasks and 114/114 retail tasks. The retail effective reward basis changed from `[DB, COMMUNICATE]` to `[DB, NL_ASSERTION]` for 112 tasks and `[DB]` for two, after normalizing the older schema's implicit default. No tasks were added or removed [E12]. **[推断]** This establishes task-definition drift between these releases, not a score or ranking change. The same retail reward-basis pattern and task fixes are documented in Issue #384; evaluator-version regrading and version pinning are also covered in prior leaderboard-audit work [E7].

**[事实]** AgentAudit describes lifecycle trace dimensions and failure attribution; runtime-monitoring work evaluates action-history properties; safety/security benchmarks report policy violations [5–7]. **[推断]** Adding trace labels, failure categories, or a safe-stop metric alone would be insufficient novelty.

**[事实]** The literature screen records executable-contract audits and recovery benchmarks as close work. Evidence-Supported Bounds compares native scores with evidence assessment and uncertainty; AgentRelBench separates task success from state-based damage; Tool-Veritas examines evaluator validity; AgentEval distinguishes behavior, evidence, and assessment qualification [6, 10–13]. **[推断]** These works directly constrain the current framing.

**[推断]** The proposed paired misclassification/decision-impact design is not currently a demonstrated distinction. More task families alone would not establish a novel mechanism or evaluation methodology. **[待补]** Any future proposal needs an exact benchmark task, full metric suite, contract-grounded consequential disagreement, and a specific gap relative to these works. The current engineering controls supply no such incremental evidence.

**[事实]** The literature review identifies AFT-Bench on operational interface interventions and uncertain effects, INTENT on hard-budget tool planning, and HyperAgent on schema-dependent planning and execution-state support [15–17]. **[推断]** The current implementation has no independently established algorithmic increment over these adjacent approaches. The comparison record is in [DIRECT_COMPARISON_160.md](DIRECT_COMPARISON_160.md).

**[事实]** Evidence-Supported Bounds audits artifact support for outcome claims across five benchmarks, including AppWorld, labels records Pass/Fail/Unknown, and reports uncertainty bounds. Its AppWorld sample is 100 cases across three models, with no native conflicts reported in that sample [E5]. **[推断]** That outcome-evidence estimand differs from this project's four-case replay reproducibility question.

**[事实]** Chen's oracle-integrity study uses known-answer and fault-injection controls, regrades archived benchmark trajectories, and evaluates comparison changes; it reports a portability limitation on an independently implemented benchmark [E6]. **[推断]** This overlaps with the general measurement claim, although the reported benchmark and root cause differ from the four archived AppWorld cases.

**[事实]** Liu's study audits public agent leaderboards for instrumentation errors, action provenance, and evaluator-version regrading, and reports score and ordering changes; it does not report this AppWorld archive [E7]. **[推断]** The four-case project result cannot claim the first study of silent regrading effects.

**[事实]** Ding et al. re-execute 1,929 archived SWE-bench evaluations, reproduce 5,999/6,006 archived verdicts, report 23 record/rerun disagreements, and find that the prespecified best-agent selection and system-arm ranking remain unchanged [23]. **[推断]** This directly covers the general “archived replay drift and decision impact” framing. The AppWorld census differs in domain and its specific missing-metadata condition, but has only one historical model/agent lineage, no ranking endpoint, and an upstream-reported zero-hash condition. The remaining result is a useful case-level replication, not an independent contribution.

**[事实]** AppWorld issue #218, opened 2026-08-24, reports a zero-hash short-circuit; PR #219 proposes changing the condition [E4]. **[推断]** The four-case adaptation exercises only the corresponding predicate in AppWorld 0.1.0; it is not the full PR and does not establish historical live behavior.

**[推断]** Together, these works leave no supported independent top-conference claim in the current project. The AppWorld census quantifies sensitivity within one historical agent lineage; the τ²-bench reanalysis adds a second public benchmark archive, but the exact procedure was already analyzed in prior work and no within-domain ranking change appeared under this re-scoring. Neither establishes an original live scoring failure for AppWorld, a matched strong-rule comparison, or a novel evaluation method.

| Work | What it already covers | Implication for this study |
|---|---|---|
| AgentBench / WebArena | Interactive tasks and task-completion evaluation | Do not claim interaction itself is new |
| τ-bench | Tool-agent-user interaction and multi-run reliability | Compare exact reliability estimand and task setup |
| τ²-bench / `llmcontract-tau2` | Confirmation-before-mutation monitoring on 2,624 published retail/airline trajectories; 11/1,755 native passes flagged | Direct overlap; our same-corpus rank reanalysis found no within-domain ordering change |
| τ²-bench task-contract / reward-basis audit | Later airline T2 is among the documented reward-basis omissions; an older archived task-2 trajectory stores unmet NL assertions outside its basis [E11] | Evidence is version-sensitive and overlaps the upstream audit; do not claim an independent finding |
| AgentDojo | Task utility paired with security violations | Security-only discrepancy is not sufficient novelty |
| AgentAudit and runtime monitors | Trace dimensions, policy properties, failure attribution | Adding trace labels alone is not enough |
| Executable-contract benchmark audit (2026) | Tool implementation/advertised contract and score provenance defects | Closest overlap; must be addressed directly before any GO |
| FaultDA-Bench 0.5.65 | State, tool, replay, and offline cost infrastructure; no held-out experiment | Infrastructure only; no cross-task conclusion |
| Evidence-Supported Bounds | Native/evidence views, Unknown cases and supported ranking | Dual scoring and missingness bounds are not standalone novelty |
| AgentRelBench | Success/damage separation using state differences | Collateral damage and single-run misses require direct comparison |
| Tool-Veritas | Evaluator validity, path rigidity and decomposed scoring | A false-negative pivot is not automatically novel |
| AgentEval | Contract-bound evidence/assessment semantics | Binding and assessment records are existing close work |
| Oracle-integrity study, v2 | Stateful-oracle checks and corrected comparison | Mutation checks or ranking changes alone do not distinguish this draft |
| Re-executing Coding-Agent Evaluations (2026) | 1,929 archived SWE-bench reruns; archived verdict disagreement and fixed-history decision stability | General replay/regrade methodology is directly covered; a single AppWorld/GPT-4o lineage without a decision change is not an independent increment |
| AFT-Bench | Controlled operability interventions, uncertain effects and policy-correct termination | Direct overlap with the current receipt/interface route; no first-operability claim |
| INTENT | Hard-budget inference-time tool planning | Budget salience or affordable-action filtering is not an original planning algorithm |
| HyperAgent | Schema dependencies and state-conditioned tool support | Explicit dependencies, dynamic tool contexts and completion support need a differentiated result |
| EpiSEM-Bench | Missing evidence, useful recovery, false abstention and costs | Combining these existing dimensions is not independently novel |
| AgentAbstain | Should-act/should-abstain pairs and calibrated restraint | A safe-stop pivot needs more than paired abstention metrics |
| TelemetrySuffBench | Observational ambiguity, evidence sufficiency and origin attribution | Evidence-gated diagnosis is already a direct neighboring problem |

## 5. Study design and evaluation questions

**[事实]** The completed diagnostic currently covers four cases. **[待补]** The questions below distinguish that evidence from work that has not passed the novelty gate; proposed measurements are not results.

| RQ | Estimand and metric | Baseline | Data / environment | Current status |
|---|---|---|---|---|
| RQ1 [事实]: Are saved check labels reproducible from archived states? | Per-case passed/failed check-label agreement and binary score transitions | Saved historical report vs released AppWorld 0.1.0 offline replay | Four score-stratified AppWorld development trajectories; fresh Windows/Python 3.12 processes | Completed descriptively: unmodified replay matched all check labels in 1/4; two saved passes changed to replay failures |
| RQ2 [事实]: Does the known zero-counter condition account for those four mismatches? | Per-case agreement after changing only the predicate in memory | Unmodified replay and the locally adapted predicate | Same four archived development states | Completed as a control: adapted predicate matched saved labels in 4/4; full PR and historical runtime were not tested |
| RQ3 [事实]: How often does replay sensitivity occur across the archived train/dev corpus? | Counts of task-level label changes, pass-to-fail transitions, and check-level changes, reported by split | Saved report vs released scorer | 147 official 0.1.0 train/dev outputs; single GPT-4o ReAct lineage; independent process per task | Completed descriptively: 51/76 saved passes changed to failures; exact check-label lists matched in 38/147 |
| RQ4 [事实 / 待补]: Does policy-adjusted scoring change observed result-group order in an external archive? | Native pass count vs native pass minus event-order violations; domain-wise ordering | Published result rewards vs the documented confirmation-order rule | 2,624 archived τ²-bench trajectories, four model result groups, retail and airline | Reanalysis completed: 11/1,755 passes flagged; within-domain observed order unchanged; original study already reported the discrepancy [E10] |
| RQ5 [待补]: Do native-score passes contain independently confirmed violations that change a practical system comparison beyond this known case? | Blind contract-based labels, paired ranking changes, uncertainty and cost | Original complete scorer plus same-permission strong rule | Independently sourced task family and matched rule/model runs not already covered by [E10] | Not identified; do not infer from replay transitions or the prior monitor's labels |

**[推断]** The selected four-case review does not estimate a native false-success rate. The 147-case AppWorld census remains one benchmark and one model/agent lineage; the τ²-bench archive provides an external published trajectory set, but its rule, corpus, and main discrepancy were already reported in prior work, and our re-scoring did not change within-domain ordering. **[待补]** RQ5 requires a differentiated task family or claim, a matched strong rule, a defensible sample-size and budget plan, and review of the design before new runs.

### 5.1 Unit and matched comparison (historical proposal; [待补])

**[待补: proposed protocol]** The inferential unit is a task instance nested in an independently sourced task family. Each evaluated system should receive the same task specification, observable state, tool interface, action cap, token/compute cap, and environment seed. Run-level data should include the original score, ordered tool trace, durable state before and after, external side effects, costs, and adjudication evidence.

**[待补: proposed baseline]** At least two systems should be compared: an agent and a strong public rule using the same observations and tools. A scripted expert oracle may validate solvability but is not a model baseline. With one system, ranking effects cannot be estimated.

### 5.2 Independent reliability adjudication (historical proposal; [待补])

**[待补: proposed label protocol]** Reliability is a task-contract judgment over observable evidence, not a second language-model opinion. An adjudicator should inspect:

1. **[待补：拟议标注项]** whether required terminal artifacts and values are correct;
2. **[待补：拟议标注项]** whether any irreversible, duplicate, unauthorized, or invalid intermediate effect occurred;
3. **[待补：拟议标注项]** whether writes/commits are supported by the actual environment state, rather than the agent's text or an unverified tool receipt;
4. **[待补：拟议标注项]** whether a stop or escalation was permitted by the public contract and available evidence; and
5. **[待补：拟议标注项]** whether an apparent failure was safe, recoverable, and correctly reported.

**[待补: proposed safeguards]** The outcome grader and reliability adjudicator must not share scoring code, reference data, or label paths. Preserve the original score. Keep ambiguous cases unresolved and adjudicate blind; do not drop them after outcomes are known.

### 5.3 Task-family independence and data lineage (historical proposal; [待补])

**[待补: candidate design]** A development pilot could span structurally different task families and freeze source lineage, generation scripts, licenses, inputs, and oracle definitions. Persistent data/report updates, transactional workflows, and repository/environment state are only candidates; none is an approved or acquired independent dataset.

**[推断 / 待补]** Three families may expose feasibility issues but are not enough for a broad stability claim. A confirmatory study needs a justified number of independent families and task clusters; paraphrases, seeds, and fault variants do not create new families. The current project has not met this design requirement.

### 5.4 Measures (historical proposal; [待补])

- **[待补：拟议指标] Outcome success:** the benchmark's frozen primary score.
- **[待补：拟议指标] Reliable success:** required terminal outcome achieved with no prohibited durable effect and correct termination/reporting.
- **[待补：拟议指标] False-success rate:** outcome-success runs that fail independent reliability adjudication.
- **[待补：拟议指标] Safe non-completion:** no success, but no prohibited effect and a justified stop/escalation.
- **[待补：拟议指标] Unsafe-effect rate:** runs with a prohibited or materially harmful persistent effect, whether or not the final state passes.
- **[待补：拟议指标] Decision impact:** paired change in agent ordering under outcome-only vs reliability-aware scoring, with task-family cluster intervals.
- **[待补：拟议指标] Cost:** model/token/compute, calls, tool reads/writes, elapsed time, and adjudication cost reported separately.

**[待补：拟议分析要求]** Do not collapse false success and safe non-completion into one score without preregistered utility weights. Report per-family confusion tables and missing/ambiguous cases.

### 5.5 Analysis and safeguards (historical proposal; [待补])

**[待补: proposed analysis]** Freeze systems, prompts, tasks, rules, thresholds, and the analysis plan before confirmatory evaluation. Keep development and held-out families separate. Analyze within-family pairs and treat family as the top-level uncertainty unit. Report raw counts, intervals, and contradictory results; call the analysis descriptive if the number of clusters is too small.

**[待补: proposed controls]** The design must test for evaluator tautology, label leakage, shared-code oracles, tool-contract divergence, unequal help, uncounted computation, and ambiguous action provenance. Preserve traces with secrets redacted and release a reproducible manifest and safe evidence. **[事实]** A local hash identifies an artifact but does not prove historical immutability or provider-response authenticity.

## 6. Implementation

**[事实]** The reusable [replay harness](replay_census.py) verifies the two local encrypted input archives by SHA-256, extracts only the official train/dev task data and saved output databases, and launches a fresh `appworld==0.1.0` evaluator process for each task. It records saved and replayed check counts, exact requirement-label agreement, assertion-failure counts, and split-level aggregates. The local dependency freeze and full per-task output remain in the private work directory.

**[事实]** The harness does not execute agents, mutate the installed scorer, apply the PR #219 condition, call a model API, or process test/challenge data [E9].

## 7. Evaluation: project-development and replay evidence

**[事实]** The evidence below consists of retrospective blind reviews and offline scorer controls. It contains no new independent held-out, cross-task study.

### 7.1 A metric can reverse its apparent interpretation (0.5.60)

**[事实]** In one scripted development cluster with 72 pre-existing states, the `complete_public_rule` arm obtained 72/72 on `supported_correct_termination`, while the rule and grader called the same public-evidence function. A one-sided `actual_safe_completion` metric yielded 36/72 for `always_stop` and 24/72 for the rule; under the resolved-state denominator, correct termination was 48/48 for the rule and 24/48 for `always_stop` [8]. **[推断]** These results show a metric-definition problem in one fixture, not an agent result, external benchmark audit, or cross-task effect.

### 7.2 Strong fixed rules constrain the old mechanism (0.5.65)

**[事实]** In the offline VeriCost study, a nine-cell fixed lookup reached normalized regret 0.031539 on the preregistered synthetic primary regime under the 0.05 threshold. Across 30 development profiles, the best registered fixed rule had regret 0.014189, while Thompson sampling had 0.024159; other learned policies were worse. A separate synthetic D1 pass had a 0.002296 margin and was overturned under a wider fixed-rule family. The registered live hypotheses, new sources, held-out split, and model runs were not executed [9]. **[推断]** These results count against continuing the prior mechanism claim; they do not support H1.

### 7.3 Historical blind review and offline regrading

**[事实]** From one official historical GPT-4o agent archive, four development tasks from different scenarios were selected by saved native outcomes: two passes and two failures. Two reviewers independently examined the cases without seeing those outcomes, according to their forms and coordinator confirmation; three AI opinions were auxiliary. Both reviewed conflicts were native failures; neither native-passing case had a confirmed violation within its reviewed scope [E1]. **[事实 / 推断]** This was not an exhaustive harm inspection, and because the raw review forms are private, the public bundle cannot independently authenticate the review process.

**[事实]** The same four saved states were regraded in fresh processes using the released 0.1.0 package and a current local environment. In the unmodified replay, two saved passes became failures and two saved failures remained failures; three of four cases had a changed requirement label [E2]. No agent was rerun and no model API was called. **[推断]** Because cases were selected by saved outcome, the transition counts are not a population rate.

**[事实]** A local control adapted only the zero-counter comparison condition from the upstream PR to the 0.1.0 method in memory. It reproduced the saved passed/failed requirement labels for all four cases without synthetic markers [E3]. Earlier synthetic-marker controls reached the same check-label agreement [E2]. **[推断]** This does not test the full upstream patch, recover the historical counter, or prove the original runtime identity.

### 7.4 Full historical train/dev replay census

**[事实]** The archived train/dev census completed all 147 scorer runs with no process errors. It found 51 saved-pass to replay-fail transitions, zero fail-to-pass transitions, and exact passed/failed requirement-list agreement in 38 cases. Each newly failing replay had one assertion failure. The archived task database directories contained no `model_hashes.json` [E9].

**[推断]** The four-case replay difference is not isolated within this archive. The directional pattern is consistent with the known missing-change-metadata / zero-counter path, but this census did not retain assertion traces to establish the per-task cause, nor run the adapted predicate across all tasks. It cannot establish that the original live scorer missed a violation.

| Split | Archived saved pass/fail | Offline replay pass/fail | Saved pass → replay fail | Saved fail → replay pass | Exact check-label match |
|---|---:|---:|---:|---:|---:|
| Train | 47 / 43 | 13 / 77 | 34 | 0 | 21 / 90 |
| Dev | 29 / 28 | 12 / 45 | 17 | 0 | 17 / 57 |
| **Total** | **76 / 71** | **25 / 122** | **51** | **0** | **38 / 147** |

**[事实]** This census covers 147 archived tasks but only one benchmark and one historical model/agent lineage. The report is [APPWORLD_CENSUS_2026_11_06.md](APPWORLD_CENSUS_2026_11_06.md); the reusable harness is [replay_census.py](replay_census.py).

### 7.5 Evidence ledger

| Evidence item | What it supports | What it does not support |
|---|---|---|
| 0.5.60 metric audit | A score/denominator can create a misleading within-fixture comparison | Agent unreliability, other benchmark defects, cross-task replication |
| 0.5.65 offline policy comparison | Cheap fixed rules constrain the old evidence-allocation mechanism | Behavior of an LLM agent or external tasks |
| Existing FaultDA tools | Feasibility of logging durable state, traces, costs, and independent checks | Independent validation of these tools or a new scientific contribution |
| Existing historical model runs | Development diagnostics under their recorded protocols | Reusable confirmatory data; they share task lineage and were used for iteration |
| Four blinded AppWorld development reviews [E1] | Two reviewed conflicts were detected by saved native failures; no reviewed-scope violation was confirmed for the two native passes | A benchmark-wide miss rate, independent verification of private forms, or an out-of-scope no-harm finding |
| Four-case archived-state regrading [E2, E3] | A selected 0.1.0 replay can disagree with saved check labels and binary outcomes; an adaptation of an existing proposed condition matches those labels here | Original live false success, a validated full upstream fix, or an effect on a leaderboard |
| Full 147-case train/dev replay census [E9] | Replay sensitivity across the preserved single-lineage archive; 51/76 saved passes changed to replay failures | Original live false success, per-task causal attribution for all transitions, independent task/model generalization, or ranking impact |
| τ²-bench confirmation-order reanalysis [E10] | Same-corpus computational reproduction: 11/1,755 native passes flagged; no within-domain observed result-group order reversal under this rule | Novel discovery, independently adjudicated labels, operation-bound confirmation, matched-rule comparison, controlled model ranking, or general reliability rates |
| Six-scenario model pilot [E8] | The documented setup produced no native full-score passes; some runs were resource-censored | Comparable model ranking, false-success rate, or cross-task evidence |

**[推断]** All existing results are development evidence. The historical studies must not be pooled into a synthetic cross-task sample.

### 7.6 Evidence locators

**[事实 / 待补]** The records below identify sources for the new claims. Links and counts were checked locally, but a human manuscript verifier has not yet signed off on the updated claims.

| ID | Source | Role |
|---|---|---|
| E1 | [Blind review and replay report](APPWORLD_REVIEW_2026_11_02.md) | Sampling, human-review scope, and limitations |
| E2 | [Original encrypted review/replay bundle](evidence/appworld-review-2026-11-02.bundle) | Saved and unmodified replay results, plus synthetic-marker control |
| E3 | [Encrypted upstream-condition control bundle](evidence/appworld-pr219-control-2026-11-05.bundle) | Local protocol, adapted-condition results, and replay script |
| E4 | [AppWorld issue #218](https://github.com/StonyBrookNLP/appworld/issues/218) and [PR #219](https://github.com/StonyBrookNLP/appworld/pull/219) | Prior public report and proposed zero-counter condition |
| E5 | [Gao and Zhou, 2026](https://arxiv.org/html/2605.10448v1) | Outcome-evidence labels and bounds across five benchmarks, including AppWorld |
| E6 | [Chen, 2026](https://arxiv.org/html/2610.16067v2) | Oracle-integrity controls, archived-trace regrading, and portability boundary |
| E7 | [Liu, 2026](https://arxiv.org/html/2611.04399v1) | Public leaderboard instrumentation and evaluator-version regrading |
| E8 | [Six-scenario pilot](APPWORLD_PILOT_115.md) | Model outcomes, unequal limits, and cost scope |
| E9 | [147-case census report](APPWORLD_CENSUS_2026_11_06.md) and [replay harness](replay_census.py) | Aggregate labels, environment, input hashes, and inference limits |
| E10 | [τ²-bench reanalysis](TAU2_RANKING_REANALYSIS_2026_11_06.md), [analysis script](tau2_ranking_reanalysis.py), [upstream issue #298](https://github.com/sierra-research/tau2-bench/issues/298), and [companion replay repository](https://github.com/chrisbartoloburlo/llmcontract-tau2) | Prior-reported violation counts, independent code reanalysis, unchanged within-domain rank, source-version and label limits |
| E11 | [Airline task-2 scoring-basis review](TAU2_TASK2_SCORING_BASIS_REVIEW_2026_11_06.md), τ²-bench [v0.1.0 task data](https://github.com/sierra-research/tau2-bench/blob/v0.1.0/data/tau2/domains/airline/tasks.json), [v1.0.1 task data](https://github.com/sierra-research/tau2-bench/blob/v1.0.1/data/tau2/domains/airline/tasks.json), and [Issue #384](https://github.com/sierra-research/tau2-bench/issues/384) | Embedded run-time policy/reward fields, task-version change, direct-neighbor overlap, and non-adjudication limit |
| E12 | [Airline task-2 scoring-basis review and version comparison](TAU2_TASK2_SCORING_BASIS_REVIEW_2026_11_06.md), τ²-bench [v0.1.0 task data](https://github.com/sierra-research/tau2-bench/tree/v0.1.0/data/tau2/domains), [v1.0.1 task data](https://github.com/sierra-research/tau2-bench/tree/v1.0.1/data/tau2/domains), and [Issue #384](https://github.com/sierra-research/tau2-bench/issues/384) | Static field-level changes after normalizing schema defaults; no re-scoring, no impact estimate, direct prior-work overlap |

## 8. Remaining research gates and venue fit

**[待补] The decisive research gaps are not closed by the 147-case replay census:**

1. **[待补] Independent confirmatory task lineage:** a public τ²-bench archive has now been reanalyzed, but the same rule and discrepancy were already covered by prior work; it does not provide an unclaimed task-level result. Any further family must target a predeclared gap not already covered by [E10] and have its contract, state/action structure, and oracle lineage documented before a run.
2. **[待补] Matched system comparison:** evaluate a real agent and a strong public rule with identical task inputs, visible evidence, tools, and budgets. The available train/dev archive has one GPT-4o ReAct lineage and no matched rule trajectory.
3. **[事实 / 待补] Cross-model evidence:** the AppWorld train/dev census contains only GPT-4o (2024-05-13); the external τ² archive contains four model result groups, but GPT‑4.1 mini uses a different `base` configuration and a different recorded runner commit. This archive is descriptive prior evidence, not a controlled cross-model extension of the AppWorld run. No new API/model call was made for this draft.
4. **[待补] Claim and source review:** independently verify every manuscript claim, bibliography entry, license condition, and any proposed public artifact. Coordinator-confirmed review records do not replace an independent review of this manuscript.
5. **[待补] Decision gate:** only reconsider a paper-level GO if a blinded, task-contract-grounded violation survives the native full scorer, same-permission strong rule, and direct close-work comparison on independent tasks. Otherwise retain the replication note as engineering evidence and stop expanding the scientific claim.

### Provisional venue recommendation (not a venue selection)

**[推断] NeurIPS Evaluations & Datasets is the closer future fit** if the work becomes a rigorous benchmark audit or a meaningful negative result: the [2026 track CFP](https://neurips.cc/Conferences/2026/CallForEvaluationsDatasets) explicitly includes evaluation audits, reproduction, stress-testing, and critical/negative analyses. Its 2026 rules use default double-blind review and the NeurIPS LaTeX format; the [reviewer guidance](https://neurips.cc/Conferences/2026/EvaluationsDatasetsReviewerGuidelines) describes a nine-page main-content limit. The 2027 CFP and exact template are not yet verified here, so these are 2026 precedent details only.

**[推断] KDD 2027 Datasets & Benchmarks is conditional** on developing an accessible, well-documented benchmark/tool or a dataset contribution with demonstrable value. The [2027 first-cycle CFP](https://kdd2027.kdd.org/datasets-and-benchmarks-track-call-for-papers/) emphasizes accessibility, quality/documentation, impact, and ethics; submissions use ACM double-column format, single-blind review, and eight content pages (with references and appendix combined limited to three pages for final papers). The first-cycle paper deadline, 26 July 2026, has passed; the second-cycle schedule needs checking. The current project lacks an independently sourced public dataset, so this route is weaker today.

**[待补] No conference has been selected.** NeurIPS 2027 requirements and the next KDD 2027 cycle must be checked against their official CFPs after the user confirms a target. This note is an author-facing recommendation and is not manuscript submission text.

## 9. Discussion & Limitations

**[推断]** The central claim is not established. The project has no new held-out model run, a history of changing metric definitions, and only historical development archives. The four AppWorld blind reviews do not establish an original-score false success. The 147-case census documents offline replay divergence; the shared comparison condition was already reported upstream. The τ²-bench reanalysis reproduces a published confirmation-order result but finds no within-domain ranking change under that rule. Existing 0.5.60 evidence is program-generated and single-cluster. Existing 0.5.65 evidence is offline and explicitly non-generalizing. **[待补]** Any further model/task experiment requires a differentiated, independently reviewed design before execution.

**[事实]** This manuscript is a venue-neutral retrospective replay draft, not a completed benchmark paper. **[推断]** The evidence does not currently support a NeurIPS, KDD, or other top-conference contribution claim. **[待补]** Human verification of updated claims, independent task families, matched system comparisons, and target-venue selection remain outstanding.

### Threats to validity

- **[事实 / 推断] Selection:** four cases were stratified by saved score, so their review counts do not estimate population frequencies; the 147-case replay covers one fixed archive, not other populations.
- **[推断] Construct:** score-label agreement after replay measures reproducibility, not whether the saved score correctly reflects every task-contract violation.
- **[事实] Historical execution:** the released 0.1.0 package and current dependencies do not identify the exact source and dependency state of the original historical run.
- **[事实] Review:** coordinator confirmation records two independently completed human reviews, but raw forms are private and the public bundle cannot authenticate reviewer process or relationships.
- **[事实 / 推断] External validity:** the reviewed cases and 147-case census belong to one AppWorld/GPT-4o ReAct lineage. A separate τ²-bench archive spans retail/airline and four model result groups, but is retrospective, directly covered by prior work, and not a matched new evaluation; these data do not establish contemporary cross-benchmark generalization.
- **[事实 / 推断] Comparison:** the adapted predicate restored labels in four selected cases; it was not run over all 147 and does not test the full upstream PR, establish historical live-scoring causality, or quantify leaderboard impact.

### Reproducibility checklist

| Item | Available evidence | Remaining gap |
|---|---|---|
| Code | Four-case replay/control and [147-case replay harness](replay_census.py) | Independently archived source version and full-corpus adapted-condition control [待补] |
| Data | Official AppWorld 0.1.0 development data and 0.1.3 output archives identified by SHA-256 | Publicly inspectable task-level artifacts are restricted; external reviewers need compliant access |
| Environment | Windows, Python 3.12, AppWorld 0.1.0 replay environment and current dependency list | Historical runtime/dependency manifest [待补] |
| Configuration | 147 train/dev tasks, fresh scorer process per task, original scorer untouched | Adapted-condition census and complete upstream PR integration test [待补] |
| Random seeds | No stochastic model or task generation was run in the replay | Not applicable to the completed replay; required for future model experiments |
| Human labels | Two reviewers' case labels are summarized in the encrypted evidence manifest | Raw review forms, relationship declarations, and independent public verification [待补] |

## 10. Conclusion

**[事实]** Replaying the saved AppWorld 0.1.0 train/dev databases with the released scorer changed 51 historical passes to failures across the 147-task archive; no historical failure changed to a pass. The task set belongs to one historical GPT-4o ReAct lineage.

**[事实]** A separate reanalysis of published τ²-bench retail/airline trajectories reproduced the reported 11/1,755 native-pass and 13/869 native-fail event-order flags. **[事实]** Subtracting the 11 flagged passes did not change the ordering of model pass counts within either domain. **[推断]** This is a computational reanalysis of an already published case, not a new independent discovery; it does not establish a change in leaderboard conclusions.

**[推断]** The result documents substantial sensitivity of archived scores to offline replay conditions. It does not demonstrate that the original live benchmark scorer missed a violation, nor that an agent or system ranking was misjudged. The shared zero-counter condition has direct upstream coverage, and the current project has not established a distinct scientific contribution.

**[待补]** A paper-level claim requires independent task lineage, a same-permission agent/strong-rule comparison, cross-model evidence, and independent manuscript and source verification. No target venue has been selected; the venue-neutral draft should not be treated as submission-ready.

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
22. Kassis, T., Agarwal, V., He, Y., Patel, D., and Brueckner, A. M. “Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents.” 2026. [arXiv:2609.00065](https://arxiv.org/abs/2609.00065). This writing workflow was used for the 2026-11-06 revision.
23. Ding, Tianyu, Yaocheng Tong, Muzhi Yang, Fei Jiang, Lei Yang, and Boya Yu. “Re-executing Coding-Agent Evaluations: Unchanged Decisions and Unresolved Policy Risk.” 2026 preprint, v1. [arXiv:2610.14460v1](https://arxiv.org/abs/2610.14460v1).

**[事实 / 待补] Citation check:** arXiv identifiers and titles for entries 1–7 and 10–23 were checked against their primary arXiv records on 2026-11-06; author names and preprint status for entry 23 were checked against its arXiv record. Entries 8–9 refer to the project's own reports. Duplicate entries were removed. Full author lists for multi-author papers are abbreviated with “et al.” Venue metadata for entries marked preprint has not been independently confirmed beyond the listed arXiv record; do not add publication status without checking an authoritative proceedings page.
