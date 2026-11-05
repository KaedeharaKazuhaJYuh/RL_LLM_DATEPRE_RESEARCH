"""Check normalized evidence against original sources, without reusing the exporter.

This is a local consistency check, not proof of authenticity or scientific blinding.
"""

import csv
import json
import re
from pathlib import Path

from .audit import artifact, audit, digest, require


ATTACHMENTS = {"spec.json", "native_trace.json", "upstream.csv", "v1.csv", "v2.csv", "ledger.sqlite"}
REVIEW_FIELDS = ["review_key", "reviewer", "snapshot_correct", "terminal_correct", "confirmed_violation",
                 "termination_supported", "evidence", "dissent"]
REVIEW_README = (
    "# Normalized first-pass evidence view\n\n"
    "Contract, public input and raw CSV/SQLite/capture sources only. No derived state/reference labels or native grade is included. "
    "Case order is shuffled; only capture-envelope run IDs and program origins are aliased. "
    "Only top-level runner-reported terminal metadata and capture-control descriptions are omitted. "
    "Business payload fields are preserved even when their names resemble identity metadata. "
    "All other files retain original bytes. The analyst keeps the private source mapping separately. "
    "Review snapshot correctness separately from observed termination. Missing stop/escalate evidence must stay unknown. "
    "All subject actions are programmatic controls from one task family. "
    "Local fidelity verification is not independent approval of blinding, authenticity, accuracy or novelty.\n"
)


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key in review evidence")
            result[key] = value
        return result

    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique)


def source_runs(bundle):
    """Fail before export if an attachment is missing or has an ambiguous name."""
    audit(bundle)
    manifest = load_json(bundle)
    require(manifest.get("run_origin") == "programmatic_adapter_validation", "unsupported review-view adapter")
    result = {}
    for run in manifest["runs"]:
        sources = {"contract.json": artifact(bundle.parent, run["contract"]),
                   "public_input.json": artifact(bundle.parent, run["public_input"])}
        for reference in run.get("attachments", []):
            source = artifact(bundle.parent, reference)
            require(source.name in ATTACHMENTS, "unexpected raw review source")
            require(source.name not in sources, "duplicate raw review basename")
            sources[source.name] = source
        require(set(sources) == ATTACHMENTS | {"contract.json", "public_input.json"}, "missing required raw review source")
        native = load_json(sources["native_trace.json"])
        require(native["run_id"] == run["run_id"], "native review run binding mismatch")
        require(isinstance(native["steps"], list), "invalid native review steps")
        for origin in [native["driver_origin"], *(s["origin"] for s in native["steps"])]:
            require(isinstance(origin, str) and bool(origin), "invalid native review origin")
        result[run["run_id"]] = sources
    return result


def verify(bundle, output, mapping_path):
    """Reverse allowed substitutions and compare all other payload fields exactly.

    Review annotations may be filled. Columns, keys and evidence coverage must be
    unchanged. A regenerated inventory alone cannot bypass source comparison.
    """
    bundle, output, mapping_path = Path(bundle).resolve(), Path(output).resolve(), Path(mapping_path).resolve()
    require(not mapping_path.is_relative_to(output), "private mapping must stay outside reviewer view")
    runs = source_runs(bundle)
    mapping = load_json(mapping_path)
    require(mapping["schema_version"] == 2 and mapping["bundle_sha256"] == digest(bundle), "private mapping bundle binding mismatch")
    cases, aliases = mapping["cases"], mapping["origin_aliases"]
    require(len(cases) == len(runs) and {v["run_id"] for v in cases.values()} == set(runs), "private mapping case coverage mismatch")
    require(all(re.fullmatch(r"case-\d{4}", key) for key in cases), "invalid private case key")
    require(isinstance(aliases, dict) and all(isinstance(k, str) and k != "environment_initialization"
            and isinstance(v, str) and re.fullmatch(r"program-\d{3}", v) for k, v in aliases.items())
            and len(set(aliases.values())) == len(aliases), "invalid origin alias mapping")
    inventory = load_json(output / "inventory.json")
    require(mapping["inventory_sha256"] == digest(output / "inventory.json"), "private mapping inventory binding mismatch")
    expected_files = {"README.md", "review.csv", "inventory.json"}
    expected_evidence, used_origins = set(), set()

    def check_alias(observed, original):
        if original == "environment_initialization":
            require(observed == original, "environment identity changed")
        else:
            used_origins.add(original)
            require(original in aliases and observed == aliases[original], "origin alias/source mismatch")

    for key, record in cases.items():
        sources = runs[record["run_id"]]
        require(set(record["original_sources"]) == set(sources), "private mapping source coverage mismatch")
        for name, source in sources.items():
            relative = f"{key}/{name}"
            expected_evidence.add(relative)
            reference = record["original_sources"][name]
            require(reference == {"path": source.relative_to(bundle.parent).as_posix(), "sha256": digest(source)},
                    "private mapping source binding mismatch")
            target = output / relative
            require(target.is_file() and not target.is_symlink() and target.resolve().is_relative_to(output), "missing/escaped review evidence")
            require(inventory.get(relative) == digest(target), "review inventory hash mismatch")
            if name != "native_trace.json":
                require(target.read_bytes() == source.read_bytes(), "review source bytes changed")
                continue
            original, observed = load_json(source), load_json(target)
            require(observed["run_id"] == key, "review case identity mismatch")
            check_alias(observed["driver_origin"], original["driver_origin"])
            observed["run_id"], observed["driver_origin"] = original["run_id"], original["driver_origin"]
            require(len(observed["steps"]) == len(original["steps"]), "review step coverage mismatch")
            for view_step, source_step in zip(observed["steps"], original["steps"]):
                check_alias(view_step["origin"], source_step["origin"])
                view_step["origin"] = source_step["origin"]
            for field in ("reported_terminal", "capture_limitation"):
                require(field not in observed, "runner-only metadata leaked")
                if field in original:
                    observed[field] = original[field]
            # JSON's Python equality conflates true with 1. Compare typed values.
            require(json.dumps(observed, sort_keys=True, allow_nan=False) == json.dumps(original, sort_keys=True, allow_nan=False),
                    "review capture payload changed")
    require(used_origins == set(aliases), "unused private origin mapping")
    require(set(inventory) == expected_evidence, "review inventory file coverage mismatch")
    expected_files |= expected_evidence
    files = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}
    require(files == expected_files and not any(p.is_symlink() for p in output.rglob("*")), "unexpected/missing review files")
    require((output / "README.md").read_text(encoding="utf-8") == REVIEW_README, "review instructions changed")
    with (output / "review.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        require(reader.fieldnames == REVIEW_FIELDS and len(rows) == len(cases)
                and {r["review_key"] for r in rows} == set(cases)
                and all(None not in r and all(v is not None for v in r.values()) for r in rows),
                "review form case/column coverage mismatch")
    return {"cases": len(cases), "evidence_files": len(expected_evidence),
            "bundle_sha256": digest(bundle), "inventory_sha256": digest(output / "inventory.json"),
            "fidelity": "passed", "independent_blinding_validation": "pending",
            "scope": "local consistency with supplied originals; no authenticity or independent scientific certification"}
