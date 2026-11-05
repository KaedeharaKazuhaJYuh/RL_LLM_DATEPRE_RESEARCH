"""Source/view fidelity, leakage and attribution mutation controls; no model runs."""

import copy
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from research.reliability_reset.audit import digest
from research.reliability_reset.review_fidelity import verify
from research.reliability_reset.review_views import prepare
from research.reliability_reset.semantic_adapter import build


class ReviewFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.bundle = build(cls.root / "development")
        cls.view, cls.mapping = cls.root / "view", cls.root / "private.json"
        prepare(cls.bundle, cls.view, cls.mapping)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def view_copy(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        view, mapping = root / "view", root / "private.json"
        shutil.copytree(self.view, view)
        shutil.copyfile(self.mapping, mapping)
        return view, mapping

    def bundle_copy(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        shutil.copytree(self.bundle.parent, root / "development")
        return root, root / "development" / "bundle.json"

    def write(self, path, value):
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def read(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def rebind_inventory(self, view, mapping):
        inventory = self.read(view / "inventory.json")
        for relative in inventory:
            inventory[relative] = digest(view / relative)
        self.write(view / "inventory.json", inventory)
        private = self.read(mapping)
        private["inventory_sha256"] = digest(view / "inventory.json")
        self.write(mapping, private)

    def test_complete_source_coverage_verified(self):
        result = verify(self.bundle, self.view, self.mapping)
        self.assertEqual(result["cases"], 24)
        self.assertEqual(result["evidence_files"], 192)
        self.assertEqual(result["fidelity"], "passed")
        self.assertEqual(result["independent_blinding_validation"], "pending")

    def test_business_metadata_is_preserved_in_json_payloads_and_original_bytes(self):
        root, bundle = self.bundle_copy()
        manifest = self.read(bundle)
        run = manifest["runs"][0]
        business = {"origin": "supplier", "driver_origin": "analyst", "run_id": "invoice-12",
                    "reported_terminal": "business status", "capture_limitation": "domain note"}
        for reference in run["attachments"]:
            source = bundle.parent / reference["path"]
            if source.name == "native_trace.json":
                content = self.read(source)
                content["steps"][0]["response"]["business_metadata"] = copy.deepcopy(business)
                self.write(source, content)
            elif source.name == "spec.json":
                content = self.read(source)
                content["business_metadata"] = copy.deepcopy(business)
                self.write(source, content)
            reference["sha256"] = digest(source)
        # Rebind the supplied engineering artifacts; this is not authenticity.
        trace_path = bundle.parent / run["trace"]["path"]
        trace = self.read(trace_path)
        trace["native_trace_sha256"] = next(a["sha256"] for a in run["attachments"] if a["path"].endswith("native_trace.json"))
        self.write(trace_path, trace)
        run["trace"]["sha256"] = digest(trace_path)
        fact_path = bundle.parent / run["facts"]["path"]
        facts = self.read(fact_path)
        facts["trace_sha256"] = digest(trace_path)
        facts["attachments_sha256"] = {a["path"]: a["sha256"] for a in run["attachments"]}
        self.write(fact_path, facts)
        run["facts"]["sha256"] = digest(fact_path)
        self.write(bundle, manifest)
        view, mapping = root / "view", root / "private.json"
        prepare(bundle, view, mapping)
        private = self.read(mapping)
        key = next(k for k, v in private["cases"].items() if v["run_id"] == run["run_id"])
        self.assertEqual(self.read(view / key / "native_trace.json")["steps"][0]["response"]["business_metadata"], business)
        self.assertEqual(self.read(view / key / "spec.json")["business_metadata"], business)
        self.assertEqual(verify(bundle, view, mapping)["fidelity"], "passed")

    def test_changed_capture_payload_rejected_despite_rehashed_inventory(self):
        view, mapping = self.view_copy()
        native = view / "case-0001" / "native_trace.json"
        capture = self.read(native)
        capture["steps"][0]["response"]["ok"] = "changed"
        self.write(native, capture)
        self.rebind_inventory(view, mapping)
        with self.assertRaisesRegex(ValueError, "capture payload changed"):
            verify(self.bundle, view, mapping)

    def test_boolean_to_number_substitution_is_not_accepted_as_equal(self):
        view, mapping = self.view_copy()
        native = view / "case-0001" / "native_trace.json"
        capture = self.read(native)
        capture["capture_complete"] = int(capture["capture_complete"])
        self.write(native, capture)
        self.rebind_inventory(view, mapping)
        with self.assertRaisesRegex(ValueError, "capture payload changed"):
            verify(self.bundle, view, mapping)

    def test_changed_csv_rejected_despite_rehashed_inventory(self):
        view, mapping = self.view_copy()
        path = view / "case-0001" / "v1.csv"
        path.write_bytes(path.read_bytes() + b"\n")
        self.rebind_inventory(view, mapping)
        with self.assertRaisesRegex(ValueError, "source bytes changed"):
            verify(self.bundle, view, mapping)

    def test_swapped_case_mapping_cannot_redirect_original_sources(self):
        view, mapping = self.view_copy()
        private = self.read(mapping)
        keys = [next(k for k, v in private["cases"].items() if v["run_id"] == name)
                for name in ("healthy--public_rule", "incorrect_final_intervention--scripted_stress")]
        private["cases"][keys[0]], private["cases"][keys[1]] = private["cases"][keys[1]], private["cases"][keys[0]]
        self.write(mapping, private)
        with self.assertRaisesRegex(ValueError, "(source bytes changed|capture payload changed|alias/source mismatch)"):
            verify(self.bundle, view, mapping)

    def test_duplicate_or_missing_case_mapping_rejected(self):
        view, mapping = self.view_copy()
        private = self.read(mapping)
        keys = list(private["cases"])
        private["cases"][keys[0]] = copy.deepcopy(private["cases"][keys[1]])
        self.write(mapping, private)
        with self.assertRaisesRegex(ValueError, "case coverage"):
            verify(self.bundle, view, mapping)

    def test_added_answer_file_is_rejected(self):
        view, mapping = self.view_copy()
        (view / "answers.json").write_text('{}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unexpected/missing review files"):
            verify(self.bundle, view, mapping)

    def test_review_annotations_allowed_but_case_removal_rejected(self):
        view, mapping = self.view_copy()
        path = view / "review.csv"
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        rows[0]["reviewer"] = "test-only annotation; not an actual review"
        rows[0]["dissent"] = "test fixture"
        def save():
            with path.open("w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
        save()
        self.assertEqual(verify(self.bundle, view, mapping)["fidelity"], "passed")
        rows.pop()
        save()
        with self.assertRaisesRegex(ValueError, "form case/column coverage"):
            verify(self.bundle, view, mapping)

    def test_missing_or_duplicate_source_basename_rejected_before_publication(self):
        for mode in ("missing", "duplicate"):
            with self.subTest(mode=mode):
                root, bundle = self.bundle_copy()
                manifest = self.read(bundle)
                run = manifest["runs"][0]
                if mode == "missing":
                    run["attachments"].pop()
                else:
                    source = bundle.parent / run["attachments"][0]["path"]
                    extra = bundle.parent / "extra" / source.name
                    extra.parent.mkdir()
                    shutil.copyfile(source, extra)
                    run["attachments"].append({"path": extra.relative_to(bundle.parent).as_posix(), "sha256": digest(extra)})
                fact_path = bundle.parent / run["facts"]["path"]
                facts = self.read(fact_path)
                facts["attachments_sha256"] = {a["path"]: a["sha256"] for a in run["attachments"]}
                self.write(fact_path, facts)
                run["facts"]["sha256"] = digest(fact_path)
                self.write(bundle, manifest)
                with self.assertRaisesRegex(ValueError, "(missing required|duplicate raw review basename)"):
                    prepare(bundle, root / "view", root / "private.json")
                self.assertFalse((root / "view").exists())
                self.assertFalse((root / "private.json").exists())


if __name__ == "__main__":
    unittest.main()
