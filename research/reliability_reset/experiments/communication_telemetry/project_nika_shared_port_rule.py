"""Project the frozen NIKA counter rule over ServDeg-derived load strata.

This is an algebraic scenario calculation, not a packet or Agent experiment.
It asks how one representative background flow changes determinate coverage
when the target and background share the measured egress counter.
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
                ("terminal_target_packet_loss", background_packets),
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
        "protocol": "nika-shared-port-rule-projection-v1",
        "profile_source": profile["dataset"]["record"],
        "rule": "I>0 and E=0 => terminal loss; I>0 and E=I => report loss; otherwise underdetermined",
        "assumptions": [
            "One representative ServDeg flow is placed on the same egress counter as the NIKA target burst.",
            "The background packets pass without loss in both conditions.",
            "Counters expose only the summed ingress and egress deltas shown in each scenario.",
            "No tool call, active probe, Agent, packet replay, or independent episode is run by this calculation.",
        ],
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
            "This calculation characterizes the current rule's algebraic coverage under an explicit shared-counter model; live NIKA behavior remains unmeasured.",
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
