"""Project the frozen counter rule under realizable NIKA port-wide loss.

This supersedes v1, whose target-only loss with passing same-port background
packets contradicted the pinned NIKA injector's egress-port match key.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--target-packets", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.target_packets <= 0:
        parser.error("--target-packets must be positive")

    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    scenarios = []
    for day in profile["days"]:
        for quantile in ("p50", "p90", "p99"):
            raw_background_packets = day["flow_quantiles"]["bidirectional_packets"][quantile]
            background_packets = round(raw_background_packets)
            ingress = args.target_packets + background_packets
            for condition, egress in (
                ("report_only_receipt_loss", ingress),
                ("port_wide_packet_loss_10000bp", 0),
            ):
                if ingress <= 0 or egress < 0 or egress > ingress:
                    prediction = "underdetermined"
                elif egress == 0:
                    prediction = "terminal_data_plane_loss"
                elif egress == ingress:
                    prediction = "packet_reached_egress_report_loss"
                else:
                    prediction = "underdetermined"
                truth = (
                    "packet_reached_egress_report_loss"
                    if condition == "report_only_receipt_loss"
                    else "terminal_data_plane_loss"
                )
                scenarios.append(
                    {
                        "day_file": day["file"],
                        "background_packet_quantile": quantile,
                        "source_background_packet_quantile": raw_background_packets,
                        "background_packets_rounded": background_packets,
                        "target_packets": args.target_packets,
                        "counter_input": {
                            "ingress_delta": ingress,
                            "egress_delta": egress,
                        },
                        "condition": condition,
                        "prediction": prediction,
                        "scenario_label": truth,
                        "correct_if_determinate": prediction == truth,
                    }
                )

    determinate = [item for item in scenarios if item["prediction"] != "underdetermined"]
    correct_determinate = sum(item["correct_if_determinate"] for item in determinate)
    output = {
        "protocol": "nika-shared-port-rule-projection-v2",
        "profile_source": profile["dataset"]["record"],
        "implementation_sources": [
            "https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/gateway.p4#L87-L96",
            "https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/gateway.p4#L170-L179",
            "https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/gateway.p4#L233-L263",
            "https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/problems/link_interface/p4_gateway.py#L14-L60",
            "https://p4.org/wp-content/uploads/sites/53/p4-spec/docs/PSA-v1.2.html#hash-function",
        ],
        "rule": "I>0 and E=0 => terminal loss; I>0 and E=I => report loss; otherwise underdetermined",
        "assumptions": [
            "One representative ServDeg flow is placed on the same egress counter as the NIKA target burst and counted in the same window.",
            "The report-only condition forwards all target and background packets at the measured egress port.",
            "The data-plane condition uses pinned NIKA loss at 10000 basis points: threshold round(65535*10000/10000)=65535; the P4 hash extern returns h modulo 65535 (0..65534), so every packet on the configured egress port satisfies hash < threshold and is dropped.",
            "Counters expose only the summed ingress and egress deltas shown in each scenario.",
            "No tool call, active probe, Agent, packet replay, or independent episode is run by this calculation.",
        ],
        "invalidated_prior_projection": {
            "protocol": "nika-shared-port-rule-projection-v1",
            "reason": "It modeled target packets as dropped while same-egress-port background packets passed, incompatible with the pinned NIKA loss table keyed only by egress port.",
            "prior_claims_to_discard": ["15/30 determinate coverage", "15/30 underdetermined scenarios", "shared-port background alone causes rule abstention in this injected-fault pair"],
        },
        "scenario_count": len(scenarios),
        "scenario_pairs": len(scenarios) // 2,
        "determinate_count": len(determinate),
        "underdetermined_count": len(scenarios) - len(determinate),
        "correct_determinate_count": correct_determinate,
        "false_determinate_count": len(determinate) - correct_determinate,
        "determinate_coverage": len(determinate) / len(scenarios),
        "accuracy_conditional_on_determinate": correct_determinate / len(determinate)
        if determinate
        else None,
        "scenarios": scenarios,
        "interpretation_limits": [
            "The five weekdays are one network and one acquisition week, not five independent deployment clusters.",
            "ServDeg provides aggregate TCP flow packet counts; the projection does not model packet-level timing or NIKA's UDP workload.",
            "This calculation covers pinned 10000-basis-point port-wide loss versus report-only loss; it does not test partial-loss subsets, unrelated concurrent faults, live runtime behavior, or an Agent.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "scenarios": output["scenario_count"],
                "determinate": output["determinate_count"],
                "underdetermined": output["underdetermined_count"],
                "false_determinate": output["false_determinate_count"],
                "coverage": output["determinate_coverage"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
