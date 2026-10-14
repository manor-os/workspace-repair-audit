"""Offline independent checks; these are not model experiment outcomes."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("natural_pilot", Path(__file__).with_name("natural_pilot.py"))
PILOT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PILOT)


class NaturalPilotTests(unittest.TestCase):
    def test_frozen_cases_and_public_separation(self):
        cases, gold = PILOT.generate()
        self.assertEqual(len(cases), 18)
        self.assertEqual(len({case["case_id"] for case in cases}), 18)
        for case in cases:
            self.assertEqual(len(case["artifacts"]), 12)
            self.assertEqual({item["format"] for item in case["artifacts"]}, {"markdown", "csv", "json"})
            payload = json.loads(case["extraction_messages"][1]["content"])
            self.assertNotIn("after_sources", payload)
            self.assertNotIn("expression_dag", payload)
            self.assertNotIn("exact_affected_ids", payload)
            self.assertGreater(len(gold[case["case_id"]]["exact_affected_ids"]), 0)

    def test_independently_calculated_budget_case(self):
        _, gold = PILOT.generate()
        case = gold["budget_01"]
        # USD8,000 / USD16 =500 leads;4%=20 customers;USD350 each.
        self.assertEqual(case["before_values"]["C02"], "500")
        self.assertEqual(case["before_values"]["C03"], "20")
        self.assertEqual(case["before_values"]["C04"], "7000")
        self.assertEqual(case["before_values"]["C11"], "-900")
        # Budget rises to12,000: the revenue ratio and negative-profit flag stay.
        self.assertNotIn("C06", case["exact_affected_ids"])
        self.assertNotIn("C12", case["exact_affected_ids"])
        self.assertIn("C06", PILOT.routed_claims(case["dependencies"], ["F1"]))

    def test_capacity_bottleneck_and_price_invariance(self):
        _, gold = PILOT.generate()
        capacity = gold["capacity_01"]
        #120hours/8=15 capacity; demand6 ->6 bookings,USD3,900 revenue.
        self.assertEqual(capacity["before_values"]["C01"], "15")
        self.assertEqual(capacity["before_values"]["C05"], "3900")
        self.assertNotIn("C05", capacity["exact_affected_ids"])
        pricing = gold["pricing_03"]
        # An order-quantity change alters totals, not effective unit price.
        self.assertNotIn("C07", pricing["exact_affected_ids"])
        self.assertIn("C03", pricing["exact_affected_ids"])

    def test_manifest_tamper_and_missing_response_denominator(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            prepared = base / "prepared"
            PILOT.prepare(prepared)
            empty = base / "responses.json"
            empty.write_text("{}")
            PILOT.score(prepared, empty, base / "report.json")
            report = json.loads((base / "report.json").read_text())
            self.assertEqual(report["case_count"], 18)
            self.assertEqual(report["valid_response_count"], 0)
            self.assertGreater(report["immediate_edges_micro"]["fn"], 0)
            with self.assertRaises(ValueError):
                PILOT.prepare(prepared)
            public = prepared / "public/inputs.json"
            public.write_text(public.read_text() + " ")
            with self.assertRaises(ValueError):
                PILOT.load_prepared(prepared)

    def test_oracle_response_only_validates_scorer(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            PILOT.prepare(base / "prepared")
            _, gold, _ = PILOT.load_prepared(base / "prepared")
            responses = {key: {"response": {"dependencies": label["dependencies"]}} for key, label in gold["cases"].items()}
            path = base / "responses.json"
            path.write_text(json.dumps(responses))
            PILOT.score(base / "prepared", path, base / "report.json")
            report = json.loads((base / "report.json").read_text())
            self.assertEqual(report["exact_graph_case_count"], 18)
            self.assertEqual(report["immediate_edges_micro"]["recall"], 1)
            # Correct graph does not imply exact numeric-change routing.
            self.assertLess(report["exact_changed_value_routing_case_count"], 18)

    def test_repair_uses_current_facts_and_numeric_patch_boundary(self):
        cases, gold = PILOT.generate()
        case = cases[0]
        selected = gold[case["case_id"]]["exact_affected_ids"]
        request = PILOT.build_repair_messages(case, selected)
        payload = json.loads(request[1]["content"])
        self.assertNotIn("expression_dag", payload)
        self.assertNotIn("before_sources", payload)
        self.assertIn("after_sources", payload)
        label = gold[case["case_id"]]
        record = {"selected_ids": selected, "repair_response": {"updates": {key: label["after_values"][key] for key in selected}}}
        self.assertTrue(PILOT.score_repair(record, label)["all_final_claims_correct"])
        record["repair_response"]["updates"][selected[0]] = True
        self.assertFalse(PILOT.score_repair(record, label)["all_final_claims_correct"])


if __name__ == "__main__":
    unittest.main()
