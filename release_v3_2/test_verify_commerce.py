"""Evidence-bound regressions for the $497 intake-to-payment verification gate."""
import copy
import json
import unittest
from pathlib import Path

from verify_commerce import evaluate, main, valid_stripe_link

OBS = Path(__file__).with_name("commerce_observations_2026-11-13.json")


class CommerceTruthContracts(unittest.TestCase):
    def setUp(self):
        self.snapshot = json.loads(OBS.read_text(encoding="utf-8"))

    def test_actual_observations_configure_purchase_without_claiming_revenue(self):
        result = evaluate(self.snapshot)
        self.assertTrue(result["valid"], result["errors"])
        self.assertTrue(result["purchase_link_configuration_valid"])
        self.assertTrue(result["complete_charge_list_observed"])
        self.assertEqual(result["observed_paid_charge_count"], 0)
        self.assertFalse(result["revenue_collected_verified"])
        self.assertFalse(result["fulfilled_sale_verified"])
        self.assertFalse(result["release_ready"])

    def test_live_review_price_cannot_be_substituted(self):
        s = copy.deepcopy(self.snapshot)
        s["stripe"]["primary"]["unit_amount"] = 4700
        self.assertFalse(evaluate(s)["valid"])

    def test_live_install_price_cannot_be_substituted(self):
        s = copy.deepcopy(self.snapshot)
        s["stripe"]["secondary"]["unit_amount"] = 49700
        self.assertFalse(evaluate(s)["valid"])

    def test_site_link_cannot_differ_from_stripe_link(self):
        s = copy.deepcopy(self.snapshot)
        s["website"]["checkout_base_url"] = "https://buy.stripe.com/wrong"
        self.assertFalse(evaluate(s)["valid"])

    def test_lookalike_host_and_http_fail(self):
        self.assertFalse(valid_stripe_link("https://buy.stripe.com.evil.invalid/a"))
        self.assertFalse(valid_stripe_link("http://buy.stripe.com/a"))
        self.assertFalse(valid_stripe_link("https://buyer:pass@buy.stripe.com/a"))
        self.assertFalse(valid_stripe_link("https://buy.stripe.com/a?redirect=https://evil.invalid"))

    def test_inactive_checkout_fails(self):
        s = copy.deepcopy(self.snapshot)
        s["stripe"]["primary"]["active"] = False
        self.assertFalse(evaluate(s)["valid"])

    def test_testmode_checkout_fails(self):
        s = copy.deepcopy(self.snapshot)
        s["stripe"]["primary"]["livemode"] = False
        self.assertFalse(evaluate(s)["valid"])

    def test_malformed_or_inflated_charge_counts_fail(self):
        s = copy.deepcopy(self.snapshot)
        s["stripe"]["charges"]["failed_count"] = 5
        self.assertFalse(evaluate(s)["valid"])
        s["stripe"]["charges"]["failed_count"] = -1
        self.assertFalse(evaluate(s)["valid"])

    def test_incomplete_charge_page_cannot_be_called_complete(self):
        s = copy.deepcopy(self.snapshot)
        s["stripe"]["charges"]["has_more"] = True
        result = evaluate(s)
        self.assertTrue(result["valid"])
        self.assertFalse(result["complete_charge_list_observed"])

    def test_unsigned_fulfillment_evidence_cannot_self_certify(self):
        s = copy.deepcopy(self.snapshot)
        s["fulfillment"]["payment_to_ledger_reconciliation_verified"] = True
        self.assertFalse(evaluate(s)["valid"])

    def test_unsigned_deployment_evidence_cannot_self_certify(self):
        s = copy.deepcopy(self.snapshot)
        s["website"]["current_live_http_probe_verified"] = True
        self.assertFalse(evaluate(s)["valid"])

    def test_release_gate_stays_closed_even_with_valid_checkout(self):
        self.assertEqual(main(["--observations", str(OBS), "--release-gate"]), 3)

    def test_schema_is_valid(self):
        self.assertEqual(main(["--observations", str(OBS)]), 0)


if __name__ == "__main__":
    unittest.main()
