"""Create a normalized first-pass view; retain original bytes for later review.

This aliases capture-envelope identities and withholds machine-derived labels.
Business payloads are preserved; complete identity masking is not promised.
It is not a certification of scientific blinding or evidence authenticity.
"""

import argparse
import copy
import csv
import json
import random
import shutil
import tempfile
from pathlib import Path

from .audit import digest, require
from .review_fidelity import REVIEW_FIELDS, REVIEW_README, load_json, source_runs, verify


def prepare(bundle, output, mapping_path):
    bundle, output, mapping_path = Path(bundle).resolve(), Path(output).resolve(), Path(mapping_path).resolve()
    require(not output.exists() and not mapping_path.exists(), "review view and mapping must be new")
    require(not mapping_path.is_relative_to(output), "private mapping must stay outside reviewer view")
    runs = list(source_runs(bundle).items())
    random.SystemRandom().shuffle(runs)
    output.parent.mkdir(parents=True, exist_ok=True)
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".first-pass-", dir=output.parent) as temporary:
        staging = Path(temporary) / "view"
        staged_map = Path(temporary) / "mapping.json"
        write_view(bundle, staging, staged_map, runs)
        verify(bundle, staging, staged_map)
        # Create exclusively; never overwrite an existing private map or view.
        with mapping_path.open("xb") as stream:
            stream.write(staged_map.read_bytes())
        try:
            staging.rename(output)
        except OSError:
            mapping_path.unlink()
            raise
    return len(runs)


def write_view(bundle, output, mapping_path, runs):
    origins, private, inventory = {}, {}, {}
    output.mkdir(parents=True)

    def alias(origin):
        if origin == "environment_initialization":
            return origin
        origins.setdefault(origin, f"program-{len(origins) + 1:03d}")
        return origins[origin]

    for index, (run_id, sources) in enumerate(runs, 1):
        key = f"case-{index:04d}"
        directory = output / key
        directory.mkdir()
        private[key] = {"run_id": run_id, "original_sources": {}}
        for name, source in sources.items():
            target = directory / name
            if name == "native_trace.json":
                # Only capture-envelope metadata is transformed. Nested business
                # keys such as origin/run_id/reported_terminal are left intact.
                data = copy.deepcopy(load_json(source))
                data["run_id"] = key
                data["driver_origin"] = alias(data["driver_origin"])
                for step in data["steps"]:
                    step["origin"] = alias(step["origin"])
                for field in ("reported_terminal", "capture_limitation"):
                    data.pop(field, None)
                target.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
            else:
                shutil.copyfile(source, target)
            inventory[f"{key}/{name}"] = digest(target)
            private[key]["original_sources"][name] = {"path": source.relative_to(bundle.parent).as_posix(), "sha256": digest(source)}
    with (output / "review.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows({"review_key": key} for key in private)
    (output / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8", newline="\n")
    (output / "README.md").write_text(REVIEW_README, encoding="utf-8", newline="\n")
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    mapping_path.write_text(json.dumps({"schema_version": 2, "bundle_sha256": digest(bundle),
        "inventory_sha256": digest(output / "inventory.json"), "cases": private, "origin_aliases": origins,
        "transformations": ["shuffled case order", "aliased native run_id, driver_origin and steps[*].origin only",
                            "omitted top-level reported_terminal and capture_limitation only",
                            "withheld derived state, facts and outcome; all other source bytes unchanged"],
        "independent_validation": "pending"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--verify", action="store_true", help="check an existing view against its bound originals")
    args = parser.parse_args()
    try:
        if args.verify:
            print(json.dumps(verify(args.bundle, args.output, args.mapping), indent=2))
        else:
            print(f"Prepared {prepare(args.bundle, args.output, args.mapping)} first-pass cases; independent review pending")
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
