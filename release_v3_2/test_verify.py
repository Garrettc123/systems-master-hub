"""Regression tests: keep the v3.2 baseline structurally valid and fail closed."""
import copy
import json
import unittest
from pathlib import Path

from verify import evaluate, main

MANIFEST = Path(__file__).with_name("manifest.json")


class ReleaseEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_baseline_is_valid_with_exactly_23_explicit_slots(self):
        report = evaluate(self.payload)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["claims"], 23)

    def test_candidate_repository_inventory_is_not_production_proof(self):
        report = evaluate(self.payload)
        self.assertEqual(report["repository_candidates_located"], 15)
        self.assertEqual(report["repository_unmapped"], 8)
        self.assertEqual(report["independently_production_certified"], 0)
        self.assertFalse(report["release_ready"])

    def test_cannot_claim_production_using_a_manifest_flag(self):
        invalid = copy.deepcopy(self.payload)
        invalid["production_verified"] = True
        self.assertFalse(evaluate(invalid)["valid"])

    def test_cannot_promote_one_system_by_editing_json(self):
        invalid = copy.deepcopy(self.payload)
        invalid["systems"][0]["production_status"] = "production_verified"
        self.assertFalse(evaluate(invalid)["valid"])

    def test_duplicate_or_missing_claim_breaks_structure(self):
        invalid = copy.deepcopy(self.payload)
        invalid["systems"][1]["id"] = "GCE-001"
        self.assertFalse(evaluate(invalid)["valid"])
        invalid = copy.deepcopy(self.payload)
        invalid["systems"].pop()
        self.assertFalse(evaluate(invalid)["valid"])

    def test_unmapped_repository_cannot_be_silently_marked_located(self):
        invalid = copy.deepcopy(self.payload)
        invalid["systems"][5]["mapping_status"] = "repository_located"
        self.assertFalse(evaluate(invalid)["valid"])

    def test_reject_cross_owner_and_mismatched_repository_url(self):
        invalid = copy.deepcopy(self.payload)
        invalid["systems"][0]["candidate_repository"] = "other-owner/unrelated"
        self.assertFalse(evaluate(invalid)["valid"])
        invalid = copy.deepcopy(self.payload)
        invalid["systems"][0]["evidence"]["repository_url"] = "https://example.invalid/"
        self.assertFalse(evaluate(invalid)["valid"])

    def test_reject_non_string_id_without_exception(self):
        invalid = copy.deepcopy(self.payload)
        invalid["systems"][0]["id"] = {"oops": "unhashable"}
        self.assertFalse(evaluate(invalid)["valid"])

    def test_reject_missing_repository_url_without_exception(self):
        invalid = copy.deepcopy(self.payload)
        del invalid["systems"][0]["evidence"]["repository_url"]
        self.assertFalse(evaluate(invalid)["valid"])

    def test_candidate_source_paths_cannot_traverse_repository(self):
        invalid = copy.deepcopy(self.payload)
        invalid["systems"][2]["mapping_evidence"]["paths"] = ["../secrets.txt"]
        self.assertFalse(evaluate(invalid)["valid"])

    def test_candidate_source_evidence_cannot_self_certify(self):
        invalid = copy.deepcopy(self.payload)
        invalid["systems"][2]["mapping_evidence"]["level"] = "production_verified"
        self.assertFalse(evaluate(invalid)["valid"])

    def test_40_character_commit_sha_required(self):
        invalid = copy.deepcopy(self.payload)
        invalid["systems"][0]["evidence"]["source_commit"] = "main"
        self.assertFalse(evaluate(invalid)["valid"])

    def test_release_gate_fails_without_authenticated_verification(self):
        self.assertEqual(main(["--manifest", str(MANIFEST), "--release-gate"]), 3)

    def test_normal_inventory_validation_passes(self):
        self.assertEqual(main(["--manifest", str(MANIFEST)]), 0)


if __name__ == "__main__":
    unittest.main()
