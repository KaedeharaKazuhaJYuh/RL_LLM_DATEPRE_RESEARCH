# NetOpsBench skill-conditioned diagnosis: one-page research gate

Date: 2026-11-08
Status: **HOLD; no Agent/API experiment authorized or run.** This candidate remains within AI-assisted communication-network diagnosis and does not replace that research direction.

## Falsifiable question

> On network-diagnosis tasks with identical live telemetry, tool access, and budget, does a skill that names canonical fault labels and prescribes diagnosis steps change an Agent's verdict, fault-type, or localization performance relative to a label-neutral skill—and does any change persist on held-out fault families and topologies against a deterministic rule using the same observations?

This is a skill-conditioning and attribution question, not a claim that the native scorer is defective. NetOpsBench scores the evaluated system, including its supplied skill. If the intended estimand is the complete skill-equipped agent, the skill is part of the treatment, not contamination by definition.

## Confirmed materials and source facts

- The analyzed public snapshot is NetOpsBench v0.2, dataset revision `f7ef8e5ecde5eba030c9b4cd9ec4cda7703edc42`, with 319 scored cases and 319 ATIF traces. Per-case prior audit: [case audit CSV](experiments/communication_telemetry/NETOPSBENCH_V02_CASE_AUDIT_2026_11_07.csv).
- The fixed `network-diagnosis` skill contains the literal canonical label `bgp_neighbor_misconfig`, BGP peer-check instructions, and an owner-device rule for remote-AS disagreement. It also contains `blackhole_route` guidance. The observed skill content had one SHA-256 across traces that read it: `00f22aa5e29b4a9b839a076a69011a882afa219fca391fd4336539e9c3e25d35`.
- All 26 BGP-neighbor-misconfiguration traces read that skill; the archived Agent binary-verdict was correct in 26/26. The simple initial-`anomalies_detected` rule was correct in 2/26. That rule uses only one field, so it is not a same-information strong baseline and does not establish an Agent advantage.
- Twenty-four of 26 blackhole-route traces read the same skill, which also contains `blackhole_route` guidance; the Agent verdict was correct in 18/26 while the same one-bit rule was correct in 26/26. Thus label presence alone is not sufficient to explain outcomes. The seven traces without a recorded skill read and the six partial families are retained in the audit output; no missing trace was silently dropped.
- Reproducible per-case extraction: [skill-conditioning audit CSV](experiments/communication_telemetry/NETOPSBENCH_V02_SKILL_CONDITIONING_2026_11_08.csv), [summary JSON](experiments/communication_telemetry/NETOPSBENCH_V02_SKILL_CONDITIONING_2026_11_08.summary.json), and [audit script](experiments/communication_telemetry/audit_netopsbench_skill_conditioning.py). These summarize visible tool calls and skill text; they do not create a causal ablation.
- **Same-information BGP cue check:** searched only saved Agent tool observations for the literal `Bad Peer AS`. The trigger is present in 26/26 BGP-neighbor-misconfiguration cases, absent in all other 293 cases, and gives 26/26 BGP-slice binary verdicts. Across all 319 cases it gives TP=26, FP=0, FN=268, TN=25: this is a narrow high-precision class cue, not a general fault detector. It exactly matches the Agent's BGP binary verdict on this slice, so the existing BGP results provide no evidence of incremental Agent value for binary fault detection. The cue and rule counts are reproduced in the audit CSV and summary JSON; this is a retrospective rule fit to the observed cue and is not a preregistered baseline.

## Closest related work and remaining boundary

- [RoutingBench](https://arxiv.org/abs/2609.22848) directly compares in-context, iterative-reasoning, and Agent-Skills approaches for network routing-path analysis at increasing scale. Therefore, “skills help network Agents” is not a new claim. Its stated target is route-path analysis, whereas this candidate concerns whether label-bearing diagnosis guidance changes fault verdict/type/localization attribution under fixed network evidence.
- [NIKA](https://arxiv.org/abs/2512.16381) evaluates live network troubleshooting Agents and exposes routing, probes, and telemetry tools. [FaulT-Bench](https://arxiv.org/abs/2608.27021) studies diagnosis under inaccurate tickets and evaluates outcome, repair, and reasoning. Broad network diagnosis, tool use, and noisy-ticket robustness are already covered.
- General Agent-Skill evaluation also exists (for example, [SkillsBench](https://www.skillsbench.ai/skillsbench.pdf)). The candidate cannot claim novelty from an ordinary skill/no-skill comparison. Any remaining contribution would need to show a network-specific, reproducible interaction between label-bearing procedural guidance, evidence-supported diagnosis, and generalization to unseen fault/topology clusters.

## Native-scorer boundary

No native-scoring miss is predicted. A scorer that credits a diagnosis from the full evaluated Agent system is behaving according to that system-level contract, even when a skill helped. This candidate can only support a paper claim if the paper explicitly distinguishes (a) integrated system performance from (b) model inference from live network evidence. It must not reframe expected skill-conditioned performance as an evaluation defect.

## Minimum discriminating design, if separately authorized

1. Freeze paired arms on identical task states, tool schemas, tool-call/time/token budgets, and model version: original label-bearing skill; label-neutral skill preserving procedures; and no-skill only if that arm still has equivalent tool documentation. Keep a distinct validation split by fault family and topology; repeated seeds/episodes within a generated task family are not independent task clusters.
2. Save full skill bytes, prompts, tool calls/results, final verdict/type/device/interface, and cost. Record what information each arm actually received.
3. Compare against (i) a deterministic same-information network rule, including a BGP remote-AS/peer-AS consistency check and corroborating session state, and (ii) the original scorer. Report verdict, fault type, localization, false-positive/abstention behavior, and cost separately.
4. Use paired task-cluster analysis. Do not count scale variants or retries as independent tasks. No API call is included in this gate; model access and budget remain unapproved.

## Falsifiers and decision

Close this candidate as **NO-GO for an independent contribution** if any of these holds: the original scorer is explicitly intended to measure the complete skill-equipped system and no separate reasoning estimand is justified; label-neutral versus label-bearing skill has no stable held-out effect; the same-information deterministic rule matches the Agent; any effect is confined to seen BGP templates/topologies; or the result is already adequately explained by RoutingBench/SkillsBench and the network-specific papers.

**Current decision: NO-GO for an independent claim from the existing BGP verdict slice; HOLD for any new controlled skill-generalization study.** A same-information `Bad Peer AS` trigger matches the Agent's 26/26 binary verdicts in the BGP slice, and the broader skill-value literature is direct. The source audit establishes that label-bearing procedural guidance was available and used, but not that it caused the outcome. There is no causal skill ablation, held-out task-cluster result, independent task family, or second model. The existing traces do not justify a paper novelty claim or a paid model run. A future experiment would need a network-specific prediction beyond ordinary Agent-Skill ablation and show an effect on evidence-supported fault type/localization or generalization that the same-information rule does not match.
