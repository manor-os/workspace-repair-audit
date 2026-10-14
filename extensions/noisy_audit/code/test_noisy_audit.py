"""Analytic and exhaustive small-population implementation checks, not study rows."""
from fractions import Fraction
import math
import unittest

import noisy_audit as a


class NoisyAuditTests(unittest.TestCase):
    def test_exact_probability_normalization_and_expectation(self):
        for N in range(8):
            for K in range(N + 1):
                for n in range(N + 1):
                    for q in (Fraction(0), Fraction(1, 2), Fraction(7, 10), Fraction(1)):
                        p = a.independent_pmf(N, K, n, q)
                        self.assertEqual(sum(p), 1)
                        self.assertTrue(all(x >= 0 for x in p))
                        expected_y = Fraction(n * K, N) * q if N else 0
                        self.assertEqual(sum(y * prob for y, prob in enumerate(p)), expected_y)

    def test_q1_reduces_to_plain_hypergeometric(self):
        for N in range(10):
            for K in range(N + 1):
                for n in range(N + 1):
                    p = a.independent_pmf(N, K, n, Fraction(1))
                    for y, prob in enumerate(p):
                        wanted = (Fraction(math.comb(K, y) * math.comb(N - K, n - y), math.comb(N, n))
                                  if y <= K and 0 <= n - y <= N - K else Fraction(0))
                        self.assertEqual(prob, wanted)

    def test_zero_sensitivity_bound_is_vacuous(self):
        for N in range(8):
            for n in range(N + 1):
                for y in range(n + 1):
                    self.assertEqual(a.upper_total(N, n, y, Fraction(0)), N)
            for K in range(N + 1):
                p = a.independent_pmf(N, K, N, Fraction(0))
                self.assertEqual(p[0], 1)
                self.assertTrue(all(x == 0 for x in p[1:]))

    def test_small_population_exact_coverage(self):
        delta = Fraction(1, 20)
        for N in range(9):
            for K in range(N + 1):
                for n in range(N + 1):
                    for q0 in (Fraction(0), Fraction(1, 2), Fraction(7, 10), Fraction(1)):
                        # A known LOWER sensitivity also covers more accurate independent detectors.
                        for q in {q0, Fraction(1)}:
                            p = a.independent_pmf(N, K, n, q)
                            failure = sum(prob for y, prob in enumerate(p) if a.upper_total(N, n, y, q0, delta) < K)
                            self.assertLessEqual(failure, delta, (N, K, n, q, q0))

    def test_search_can_exceed_hypergeometric_noiseless_support(self):
        # Even a full sample can hide arbitrary defects when detection is imperfect.
        self.assertGreater(a.upper_total(8, 8, 1, Fraction(1, 2)), 1)
        self.assertEqual(a.upper_total(8, 8, 1, Fraction(1)), 1)

    def test_naive_full_census_always_claims_zero_bound(self):
        for y in range(65):
            self.assertEqual(a.upper_total(64, 64, y, Fraction(1)), y)
        row, outcomes = a.scenario_metrics(64, 64, 64, Fraction(9, 10), Fraction(1))
        self.assertEqual(Fraction(row["pass_probability_exact"]), 1)
        self.assertTrue(all(o["residual_bound"] == 0 for o in outcomes))
        self.assertGreater(Fraction(row["coverage_failure_probability_exact"]), Fraction(99, 100))
        self.assertGreater(Fraction(row["unsafe_pass_probability_exact"]), Fraction(1, 20))

    def test_correlated_all_or_none_violation_anchor(self):
        p = a.correlated_all_or_none_pmf(64, 64, 64, Fraction(9, 10))
        self.assertEqual(p[0], Fraction(1, 10))
        self.assertEqual(p[64], Fraction(9, 10))
        self.assertEqual(sum(p), 1)
        self.assertEqual(a.upper_total(64, 64, 0, Fraction(9, 10)), 1)
        row, _ = a.scenario_metrics(64, 64, 64, Fraction(9, 10), Fraction(9, 10), "all_or_none")
        self.assertEqual(Fraction(row["pass_probability_exact"]), 1)
        self.assertEqual(Fraction(row["unsafe_pass_probability_exact"]), Fraction(1, 10))
        self.assertEqual(Fraction(row["coverage_failure_probability_exact"]), Fraction(1, 10))

    def test_gate_is_not_assumed_monotone_in_observed_y(self):
        self.assertLessEqual(a.upper_total(64, 64, 0, Fraction(9, 10)), 6)
        self.assertEqual(a.upper_total(64, 64, 30, Fraction(9, 10)), 37)
        self.assertGreater(a.upper_total(64, 64, 30, Fraction(9, 10)) - 30, 6)
        self.assertEqual(a.upper_total(64, 64, 58, Fraction(9, 10)), 64)
        self.assertLessEqual(a.upper_total(64, 64, 58, Fraction(9, 10)) - 58, 6)

    def test_protocol_scenario_count_without_evaluating_main_grid(self):
        scenarios = a.enumerate_scenarios()
        self.assertEqual(len(scenarios), 3250)
        self.assertEqual(sum(s["policy"] == "calibrated_independent" for s in scenarios), 1300)
        self.assertEqual(sum(s["policy"] == "naive_perfect_detector" for s in scenarios), 1300)
        self.assertEqual(sum(s["policy"] == "misspecified_sensitivity" for s in scenarios), 325)
        self.assertEqual(sum(s["policy"] == "correlation_violation" for s in scenarios), 325)

    def test_invalid_parameters_rejected(self):
        with self.assertRaises(ValueError):
            a.independent_pmf(10, 11, 2, Fraction(1))
        with self.assertRaises(ValueError):
            a.upper_total(10, 2, 3, Fraction(1))
        with self.assertRaises(ValueError):
            a.upper_total(10, 2, 1, Fraction(11, 10))


if __name__ == "__main__":
    unittest.main(verbosity=2)
