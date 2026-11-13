"""Regression tests for source-to-deployment reconciliation.

These tests validate matching logic and fail-closed behavior. The recorded
provider snapshot is not a signed attestation or a production certificate.
"""
import copy
import json
import unittest
from pathlib import Path
from reconcile import reconcile

HERE = Path(__file__).parent


class ReconciliationContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
        cls.obs = json.loads((HERE / "provider_observations_2026-11-13.json").read_text(encoding="utf-8"))

    def test_observed_snapshot_is_not_production_certification(self):
        r = reconcile(self.manifest, self.obs)
        self.assertEqual(r["candidate_repositories"], 14)
        self.assertEqual(r["candidate_repositories_observed_on_railway"], 2)
        self.assertEqual(r["candidate_repositories_matching_deployed_commit"], 0)
        self.assertEqual(r["candidate_repositories_matching_production_commit"], 0)
        self.assertFalse(r["release_ready"])

    def test_repo_match_is_not_sha_match(self):
        r = reconcile(self.manifest, self.obs)
        for x in r["matches"]:
            if x["repository_observed_on_railway"]:
                self.assertEqual(x["same_commit_deployments"], 0)

    def test_matching_sha_does_not_imply_certification(self):
        x = copy.deepcopy(self.obs)
        x["candidate_deployments"][0]["source_commit"] = next(
            s["evidence"]["source_commit"] for s in self.manifest["systems"]
            if s["candidate_repository"] == "Garrettc123/garcar-data-room"
        )
        r = reconcile(self.manifest, x)
        self.assertEqual(r["candidate_repositories_matching_deployed_commit"], 1)
        self.assertFalse(r["release_ready"])

    def test_reject_unknown_environment(self):
        x = copy.deepcopy(self.obs)
        x["candidate_deployments"][0]["environment"] = "unverified"
        with self.assertRaises(ValueError):
            reconcile(self.manifest, x)

    def test_reject_malformed_sha(self):
        x = copy.deepcopy(self.obs)
        x["candidate_deployments"][0]["source_commit"] = "main"
        with self.assertRaises(ValueError):
            reconcile(self.manifest, x)

    def test_reject_duplicate_source_evidence(self):
        x = copy.deepcopy(self.obs)
        x["candidate_deployments"].append(x["candidate_deployments"][0])
        with self.assertRaises(ValueError):
            reconcile(self.manifest, x)

    def test_unmapped_component_is_not_invented(self):
        r = reconcile(self.manifest, self.obs)
        self.assertEqual(len(r["matches"]), 14)


if __name__ == "__main__":
    unittest.main()
