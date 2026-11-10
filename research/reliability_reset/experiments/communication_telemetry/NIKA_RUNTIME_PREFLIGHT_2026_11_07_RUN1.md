# NIKA Runtime Preflight — 2026-11-07, Run 1

**Status: failed at the baseline probe; no fault arm or relay arm ran. Research gate remains HOLD.**

## Experiment scope

A bounded local Docker/Kathara run used NIKA commit `ac4422d8a4a03be2b905e28edf72993d467e1b81`, scenario `p4_dc_gateway`, small topology, and target `leaf_1` / `service_1_1`. It was intended to validate the direct watched-service path before testing the pinned report relay and leaf egress loss. It did not invoke an Agent or a paid API.

## Observed runtime evidence

- Direct HTTP to `http://10.0.1.11/` was reported false twice by NIKA's `http_ok` helper.
- The VIP HTTP path `http://20.0.0.1:80/` was true twice.
- During the direct probe window, leaf egress counter deltas were 15 packets on BMv2 port 3 and 6 on port 4; the counter window is aggregate and does not attribute individual packets.
- The run stopped in `baseline_service_probe`, before collector relay setup, controlled UDP burst, leaf loss insertion, or post-injection checks.
- The saved machine-readable result is [NIKA_LEAF_SERVICE_LOSS_PREFLIGHT_2026_11_07_RUN1.json](NIKA_LEAF_SERVICE_LOSS_PREFLIGHT_2026_11_07_RUN1.json).

## Root cause of the failed gate

This was an invalid probe criterion in the project preflight, not evidence that NIKA's supported baseline is broken. At the pinned source, `p4_dc_gateway/verify.py` explicitly describes a non-VIP TCP probe to a service address as an observation packet; normal service health is checked through the VIP. The project's preflight incorrectly required an HTTP 200 response from the direct service IP. Its own VIP health control passed, and the counter window showed traffic, but the direct HTTP criterion was unsupported by the NIKA scenario contract.

The preflight is being corrected to emit NIKA's direct TCP observation probe, require packets on the target service egress counter, and retain VIP HTTP as the service-health control. It does not treat a completed TCP connection as required. This correction changes only the diagnostic probe; it does not modify NIKA, its scorer, or the research task contract.

## Cleanup issue

NIKA's teardown reached host TAP cleanup and raised `FileNotFoundError: 'ip'` because the temporary runner container lacked `iproute2`. The raw result was written before teardown and says `lab_closed: false`. A post-run Docker inventory showed no containers with this run's Kathara lab prefix; this does not prove every non-container host resource was cleaned. The next temporary runner must include `iproute2`, and cleanup status must be checked after exit.

## Decision and next gate

This run provides no evidence that leaf service-port loss injection works, that the report-only arm is valid, or that the two causes are distinguishable. It only identifies and corrects an invalid baseline probe and a missing runner dependency. Keep the candidate on HOLD. Rerun the same bounded preflight with the corrected TCP observation probe; proceed to interpreting packet/report ledgers only if the baseline passes and teardown is clean.
