"""Meaningful semantic/API/statistical checks; no external services required."""
from __future__ import annotations

import ast
import dataclasses
from fractions import Fraction
import gzip
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import benchmark as b


class RepairBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Development seed only; held-out outcomes are not examined by tests.
        cls.cases = b.generate_base("budget", 0, "dev", 14001)

    def test_reference_cancel_and_independent_support(self):
        specs = (
            b.ClaimSpec("a", "Budget", ("source", "budget"), "human wording", "v0"),
            b.ClaimSpec("b", "Fixed support", ("constant", 10), "", "v1"),
            b.ClaimSpec("c", "Cancellation", ("subtract", "a", "a"), "", "v2"),
            b.ClaimSpec("d", "Bounded support", ("min", "a", "b"), "", "v3"),
            b.ClaimSpec("e", "Indirect", ("scale", "a", 1, 2), "", "v4"),
        )
        old = b.render_values(specs, {"budget": 100})
        new = b.render_values(specs, {"budget": 200})
        self.assertEqual({k for k in old if old[k] != new[k]}, {"a", "e"})
        self.assertEqual(b.expression_dependencies(specs[2].expression), ("a",))

    def test_public_view_has_no_gold_program_or_labels(self):
        view = self.cases[0].view()
        names = {f.name for f in dataclasses.fields(b.PublicWorkspace)} | {f.name for f in dataclasses.fields(b.PublicClaim)}
        self.assertFalse(names & {"expression", "specs", "target", "after_values", "stale", "true_dependencies"})
        self.assertEqual(len(view.claims), 64)
        self.assertEqual(len({c.claim_id for c in view.claims}), 64)
        self.assertNotEqual([c.claim_id for c in view.claims], [s.claim_id for s in self.cases[0].specs])

    def test_policy_source_cannot_call_evaluator_or_reference(self):
        # An AST guard against accidental use of the local gold API in policies.
        for f in [b.select_and_repair, b.rank_ids, b.closure_ids, b.lexical_score, b.inspect_ids]:
            tree = ast.parse(inspect.getsource(f))
            identifiers = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            attrs = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            self.assertFalse(identifiers & {"render_values", "FrozenCase", "ClaimSpec"})
            self.assertFalse(attrs & {"evaluator_report", "specs", "expression", "after_facts", "before_facts"})

    def test_all_methods_and_charged_budget(self):
        for case in self.cases:
            for method in b.METHODS:
                r = b.evaluate(case, method)
                self.assertEqual(r["validator_calls"], len(r["trace"]))
                self.assertEqual(r["validator_calls"], len(set(r["inspected_ids"])))
                self.assertEqual(r["protected_blocks_altered"], 0)
                self.assertLessEqual(r["residual_stale_count"], r["initial_stale_count"])
                self.assertEqual(r["initial_stale_count"] - r["residual_stale_count"], r["patched_count"])
                if method.endswith("_36"):
                    self.assertEqual(r["validator_calls"], 36)
                if method == "full_scan":
                    self.assertEqual(r["validator_calls"], 64)
                    self.assertEqual(r["residual_stale_count"], 0)
                if method == "ranked_audit_gate" and r["certificate"]["fallback_full_scan"]:
                    self.assertEqual(r["validator_calls"], 64)
                    self.assertEqual(r["residual_stale_count"], 0)

    def test_human_protection_and_repeat_call_charge(self):
        case = self.cases[0]
        validator = b.ValidationInterface(case)
        cid = case.specs[0].claim_id
        first = validator.validate_and_patch(cid, case.snapshot)
        second = validator.validate_and_patch(cid, case.snapshot)
        r = validator.evaluator_report()
        self.assertTrue(first.stale)
        self.assertFalse(second.stale)
        self.assertEqual(r["validator_calls"], 2)
        self.assertEqual(r["protected_blocks_text"], {s.claim_id: s.protected_block for s in case.specs})

    def test_snapshot_mismatch_rejects_without_charging_or_patch(self):
        case = self.cases[0]
        validator = b.ValidationInterface(case)
        with self.assertRaises(b.SnapshotChanged):
            validator.validate_and_patch(case.specs[0].claim_id, "changed_snapshot")
        self.assertEqual(validator.evaluator_report()["validator_calls"], 0)

    def test_patches_do_not_change_other_labels(self):
        case = self.cases[0]
        validator = b.ValidationInterface(case)
        initial = set(validator.evaluator_report()["initial_stale_ids"])
        cid = next(iter(initial))
        validator.validate_and_patch(cid, case.snapshot)
        self.assertEqual(set(validator.evaluator_report()["residual_stale_ids"]), initial - {cid})

    def test_coupled_rate_variants_are_one_base(self):
        self.assertEqual(len({c.base_id for c in self.cases}), 1)
        self.assertEqual(len({b.digest([dataclasses.asdict(s) for s in c.specs]) for c in self.cases}), 1)
        self.assertEqual(len({c.snapshot for c in self.cases}), 1)
        for earlier, later in zip(self.cases, self.cases[1:]):
            for cid in earlier.visible_citations:
                self.assertTrue(set(later.visible_citations[cid]) <= set(earlier.visible_citations[cid]))

    def test_closure_handles_incorrect_cyclic_edges(self):
        view = b.PublicWorkspace("fixture", "s", "source", "source", "1", "2", (
            b.PublicClaim("a", "A", "1", "", ("source", "b"), "v0"),
            b.PublicClaim("b", "B", "1", "", ("a",), "v1"),
        ))
        self.assertEqual(b.closure_ids(view), {"a", "b"})

    def test_hypergeometric_zero_miss_and_full_census_boundaries(self):
        self.assertEqual(b.exact_upper_total(100, 94, 0), 1)
        self.assertEqual(b.exact_upper_total(100, 95, 0), 0)
        self.assertEqual(b.exact_upper_total(0, 0, 0), 0)
        for k in range(13):
            self.assertEqual(b.exact_upper_total(12, 12, k), k)
        with self.assertRaises(ValueError):
            b.exact_upper_total(10, 3, 4)

    def test_exhaustive_finite_population_coverage(self):
        result = b.exhaustive_coverage_sanity(12)
        self.assertTrue(result["passed"])
        self.assertLessEqual(Fraction(result["max_exact_undercoverage_probability"]), Fraction(1, 20))
        self.assertFalse(result["monte_carlo_used"])

    def test_replay_has_no_clock_or_iteration_order_variation(self):
        for method in b.METHODS:
            self.assertEqual(b.canonical(b.evaluate(self.cases[2], method)), b.canonical(b.evaluate(self.cases[2], method)))

    def test_result_writer_is_reproducible_and_keeps_full_trace(self):
        # An explicit one-case development fixture tests serialization only.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            data.mkdir()
            (data / "freeze_manifest.json").write_text('{"unit_test_fixture":true}')
            with patch.object(b, "load_frozen", return_value=[self.cases[0]]):
                b.run_dataset(data, root / "first", "dev")
                b.run_dataset(data, root / "second", "dev")
            first = root / "first" / "detailed_results.jsonl.gz"
            second = root / "second" / "detailed_results.jsonl.gz"
            self.assertEqual(first.read_bytes(), second.read_bytes())
            rows = [json.loads(line) for line in gzip.decompress(first.read_bytes()).splitlines()]
            self.assertEqual(len(rows), len(b.METHODS))
            self.assertTrue(all(len(r["trace"]) == r["validator_calls"] for r in rows))


if __name__ == "__main__":
    unittest.main(verbosity=2)
