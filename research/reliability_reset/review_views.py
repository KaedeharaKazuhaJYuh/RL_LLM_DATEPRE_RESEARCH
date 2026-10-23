"""Create a normalized first-pass view; retain original bytes for later review.

This removes explicit arm/condition identifiers and machine-derived labels.
It is not a certification of scientific blinding or evidence authenticity.
"""

import argparse
import csv
import json
import random
import shutil
from pathlib import Path

from .audit import artifact, audit, digest, require


def prepare(bundle, output, mapping_path):
    bundle, output, mapping_path = Path(bundle).resolve(), Path(output).resolve(), Path(mapping_path).resolve()
    audit(bundle)
    require(not output.exists() and not mapping_path.exists(), "review view and mapping must be new")
    require(not mapping_path.is_relative_to(output), "private mapping must stay outside reviewer view")
    manifest = json.loads(bundle.read_text(encoding="utf-8"))
    require(manifest.get("run_origin") == "programmatic_adapter_validation", "unsupported review-view adapter")
    runs = list(manifest["runs"])
    random.SystemRandom().shuffle(runs)
    origins, private, inventory = {}, {}, {}
    output.mkdir(parents=True)

    def normalized(value, key):
        if isinstance(value, list):
            return [normalized(x, key) for x in value]
        if not isinstance(value, dict):
            return value
        result = {}
        for field, item in value.items():
            if field == "run_id":
                result[field] = key
            elif field in ("origin", "driver_origin"):
                if item == "environment_initialization":
                    result[field] = item
                else:
                    origins.setdefault(item, f"program-{len(origins) + 1:03d}")
                    result[field] = origins[item]
            elif field not in ("reported_terminal", "capture_limitation"):
                result[field] = normalized(item, key)
        return result

    for index, run in enumerate(runs, 1):
        key = f"case-{index:04d}"
        directory = output / key
        directory.mkdir()
        sources = {"contract.json": artifact(bundle.parent, run["contract"]),
                   "public_input.json": artifact(bundle.parent, run["public_input"])}
        for reference in run.get("attachments", []):
            source = artifact(bundle.parent, reference)
            require(source.name in ("spec.json", "native_trace.json", "upstream.csv", "v1.csv", "v2.csv", "ledger.sqlite"), "unexpected raw review source")
            sources[source.name] = source
        require("native_trace.json" in sources and "ledger.sqlite" in sources, "raw capture/database required")
        private[key] = {"run_id": run["run_id"], "original_sources": {}}
        for name, source in sources.items():
            target = directory / name
            if source.suffix == ".json":
                data = normalized(json.loads(source.read_text(encoding="utf-8")), key)
                target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
            else:
                shutil.copyfile(source, target)
            inventory[f"{key}/{name}"] = digest(target)
            private[key]["original_sources"][name] = {"path": source.relative_to(bundle.parent).as_posix(), "sha256": digest(source)}
    with (output / "review.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=["review_key", "reviewer", "snapshot_correct", "terminal_correct", "confirmed_violation", "termination_supported", "evidence", "dissent"])
        writer.writeheader()
        writer.writerows({"review_key": key} for key in private)
    (output / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8", newline="\n")
    (output / "README.md").write_text(
        "# Normalized first-pass evidence view\n\n"
        "Contract, public input and raw CSV/SQLite/capture sources only. No derived state/reference labels or native grade is included. "
        "Case order is shuffled; run IDs and program origin names are replaced by opaque aliases. "
        "Runner-only reported terminal metadata and capture-control descriptions are omitted from this view. "
        "The original sources remain unchanged for phase-two verification; the analyst retains the mapping and source hashes separately. "
        "Review snapshot correctness separately from observed termination. Missing stop/escalate evidence must stay unknown. "
        "All subject actions are programmatic; these are engineered controls from one task family. "
        "This transformation has not been independently validated as a blinded-study protocol. "
        "Do not infer population accuracy or novelty from agreement on these controls.\n", encoding="utf-8", newline="\n")
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    mapping_path.write_text(json.dumps({"cases": private, "origin_aliases": origins,
        "transformations": ["shuffled case order", "opaque run IDs and program origins", "omitted runner-only terminal and capture-control description", "withheld derived state, facts and outcome"],
        "independent_validation": "pending"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return len(runs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(f"Prepared {prepare(args.bundle, args.output, args.mapping)} first-pass cases; independent review pending")
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
