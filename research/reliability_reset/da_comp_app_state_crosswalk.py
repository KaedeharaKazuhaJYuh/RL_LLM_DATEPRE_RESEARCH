"""Build an all-task application/state crosswalk without persisting databases."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import da_comp_state_lineage as lineage


ROOT = Path(__file__).parent
MANIFEST = ROOT / "DAComp_START_STATE_SHA256_2026_11_06.json"
OUTPUT = ROOT / "DAComp_APP_STATE_CROSSWALK_2026_11_06.csv"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest["dataset_revision"] != lineage.REVISION:
        raise ValueError("state-hash manifest and archive revision differ")

    sha_by_path = {
        member["path"]: member["sha256"]
        for group in manifest["groups"]
        for member in group["members"]
    }
    entries = lineage.archive_entries()
    signature_groups: dict[tuple[int, int], list[dict[str, int | str]]] = defaultdict(list)
    for entry in entries:
        signature_groups[(int(entry["crc32"]), int(entry["uncompressed_size"]))].append(entry)
    repeated_paths = {
        str(entry["name"])
        for group in signature_groups.values()
        if len(group) > 1
        for entry in group
    }
    if set(sha_by_path) != repeated_paths:
        raise ValueError("SHA-256 manifest does not cover exactly the repeated archive members")

    rows = []
    app_states: dict[str, set[str]] = defaultdict(set)
    app_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for entry in entries:
        path = str(entry["name"])
        match = re.fullmatch(r"dacomp-de-(impl|evol)-(\d{3})/(.+)_start\.duckdb", path)
        if not match:
            raise ValueError(f"unexpected task database path: {path}")
        task_type, task_number, app = match.groups()
        signature = (int(entry["crc32"]), int(entry["uncompressed_size"]))
        repeated = len(signature_groups[signature]) > 1
        raw_sha256 = sha_by_path.get(path)
        if repeated and raw_sha256 is None:
            raise ValueError(f"missing byte hash for repeated state member: {path}")
        if not repeated and raw_sha256 is not None:
            raise ValueError(f"unexpected repeated-state hash for singleton: {path}")

        if repeated:
            state_cluster = f"sha256:{raw_sha256}"
            identity_evidence = "byte SHA-256 verified within repeated CRC32+size group"
        else:
            state_cluster = f"unique-signature:{signature[0]:08x}:{signature[1]}"
            identity_evidence = (
                "CRC32+uncompressed-size signature occurs once in the pinned archive; "
                "an identical duplicate would have the same signature"
            )

        row = {
            "task_id": f"dacomp-de-{task_type}-{task_number}",
            "task_type": task_type,
            "application_family": app,
            "start_db_crc32": f"{signature[0]:08x}",
            "start_db_uncompressed_bytes": str(signature[1]),
            "state_cluster": state_cluster,
            "identity_evidence": identity_evidence,
        }
        rows.append(row)
        app_states[app].add(state_cluster)
        app_rows[app].append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    multiple_states = {
        app: len(states) for app, states in app_states.items() if len(states) > 1
    }
    summary = {
        "archive_revision": lineage.REVISION,
        "task_rows": len(rows),
        "distinct_state_clusters": len({row["state_cluster"] for row in rows}),
        "application_families": len(app_states),
        "families_with_multiple_states": multiple_states,
        "output": str(args.output),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
