import unittest

from scripts.detect_upgrade_targets import current_tier


class UpgradeTierEvidenceTests(unittest.TestCase):
    def test_proposal_does_not_advance_applied_tier(self):
        system = {
            "upgrade_history": [
                {
                    "status": "proposal_generated",
                    "proposed_tier": "connected",
                }
            ]
        }
        self.assertEqual(current_tier(system), "scaffolded")

    def test_merged_upgrade_advances_applied_tier(self):
        system = {
            "upgrade_history": [
                {
                    "status": "merged",
                    "tier": "connected",
                }
            ]
        }
        self.assertEqual(current_tier(system), "connected")

    def test_unverified_legacy_proposal_does_not_advance_tier(self):
        system = {
            "upgrade_history": [
                {
                    "status": "proposed",
                    "tier": "autonomous",
                }
            ]
        }
        self.assertEqual(current_tier(system), "scaffolded")


if __name__ == "__main__":
    unittest.main()
