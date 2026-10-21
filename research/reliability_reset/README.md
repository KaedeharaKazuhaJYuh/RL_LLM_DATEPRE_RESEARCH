# Outcome-based Agent Evaluation Reliability Reset

This branch starts from the `0.5.65-dev` infrastructure checkpoint and pauses the previous VeriCost/mechanism line. It tests a single question: whether outcome-only agent evaluation makes consequential, independently verifiable mistakes about real operational reliability, and whether any such mistakes recur across independent task families.

Current work is design-only. No new model runs, API calls, downloads, fine-tuning, or held-out task construction have occurred.

- [Research draft](PAPER_DRAFT.md): proposed measurement question and carefully bounded retrospective development audit.
- [Reset protocol](RESET_PROTOCOL.md): operational definitions, independence gates, controls, three-week decision rule, and resource limits.

The scientific status remains **HOLD**. A positive development pilot would only justify designing a separate held-out study; a negative or non-distinct result means keeping FaultDA-Bench as engineering infrastructure and stopping expansion of the current research claim.
