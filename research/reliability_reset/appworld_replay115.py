"""Replay selected native scores in fresh processes without publishing task data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from research.reliability_reset.appworld_ledger115 import read_jsonl


WORKER = """
import hashlib, json, sys
from pathlib import Path
import appworld
from appworld import update_root
from appworld.evaluator import evaluate_task
from research.reliability_reset.native_replay185 import scoring_sources

root = Path(sys.argv[1])
attempt, position = sys.argv[2], int(sys.argv[3])
source = Path(appworld.__file__).parent
checks = scoring_sources()
if not all(hashlib.sha256((source / path).read_bytes()).hexdigest() == digest
           for path, digest in checks.items()):
    raise ValueError("Native scorer source mismatch")
protocol = json.loads((root / "PILOT_PROTOCOL.json").read_text(encoding="utf8"))
update_root(str(root / "native-root"))
score = evaluate_task(protocol["task_ids"][position - 1], experiment_name=attempt, save_report=False)
print("REPLAY115=" + json.dumps({"attempt": attempt, "source_files_checked": len(checks),
      "success": score.success, "passed": score.pass_count, "failed": score.fail_count,
      "total": score.num_tests}))
"""


def replay(input_root: Path, native_python: Path, manifest: dict, attempts: list[str]) -> dict:
    specifications = {row["attempt"]: row for row in manifest["attempts"]}
    results = []
    for attempt in attempts:
        spec = specifications[attempt]
        events, malformed = read_jsonl(input_root / "journals" / attempt / "events.jsonl")
        finals = [row for row in events if row.get("kind") == "final"]
        if malformed or len(finals) != 1:
            raise ValueError(f"Expected one complete original journal for {attempt}")
        child = subprocess.run([str(native_python.resolve()), "-c", WORKER, str(input_root.resolve()),
                                attempt, str(spec["task"])], capture_output=True, text=True,
                               encoding="utf8", errors="replace", timeout=120)
        if child.returncode:
            raise RuntimeError(f"Native score process failed for {attempt}: exit {child.returncode}")
        lines = [line.removeprefix("REPLAY115=") for line in child.stdout.splitlines()
                 if line.startswith("REPLAY115=")]
        if len(lines) != 1:
            raise ValueError(f"Native score output is missing or ambiguous for {attempt}")
        score = json.loads(lines[0])
        if score["attempt"] != attempt:
            raise ValueError(f"Native score attempt mismatch for {attempt}")
        final = finals[0]
        score["matches_recorded"] = (score["success"], score["passed"], score["failed"], score["total"]) == (
            final["native_success"], final["native_tests_passed"], final["native_tests_failed"],
            final["native_tests_total"])
        results.append(score)
    return {"separate_process_per_attempt": True, "save_report": False, "results": results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_root", type=Path)
    parser.add_argument("native_python", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--attempt", action="append", required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf8"))
    result = replay(args.input_root, args.native_python, manifest, args.attempt)
    with args.output.open("x", encoding="utf8", newline="\n") as out:
        json.dump(result, out, indent=2)
        out.write("\n")
    print(f"Replayed {len(result['results'])} native scores in separate processes.")
    if not all(row["matches_recorded"] for row in result["results"]):
        raise SystemExit("At least one replay differs from its original native score.")


if __name__ == "__main__":
    main()
