#!/usr/bin/env python3
"""Exact one-look finite-population audit with imperfect sensitivity.

Known finite-population statistical machinery, evaluated as a component study.
No language models, production systems, random simulation or new theorem claim.
The pool is frozen AFTER any earlier repair; all residual K defects are fixed.
Only correctly detected positives are repaired. Audited false negatives remain.
"""
from __future__ import annotations

import argparse
import csv
from fractions import Fraction
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any


STUDY_ROOT = Path(__file__).resolve().parent.parent
PROTOCOL = {
    "component_study": "One-look audit with imperfect sensitivity, version1",
    "population_size": 64,
    "sample_sizes": [16, 24, 36, 48, 64],
    "independent_actual_sensitivities": ["1", "9/10", "7/10", "1/2"],
    "fixed_true_defect_totals": list(range(65)),
    "delta": "1/20",
    "allowed_residual_defects": 6,
    "main_policies": ["calibrated_independent", "naive_perfect_detector"],
    "misspecified": {"actual_q": "7/10", "assumed_lower_q0": "9/10"},
    "correlated": {"actual_marginal_q": "9/10", "assumed_independent_lower_q0": "9/10",
                   "distribution": "q*Hypergeom(N,K,n)+(1-q)*pointmass(Y=0)"},
    "planned_parameter_policy_rows": 3250,
    "inference": "Exact integer PMF sums and rational arithmetic over every feasible observed-positive count Y; no Monte Carlo.",
    "analysis_freeze": "Protocol and source are frozen before the full parameter sweep. Small-population tests and selected analytic N64 anchors were examined during design. This is not external preregistration or evaluation on unseen held-out data.",
    "defect_total_interpretation": "K is the fixed number of stale claims before this final audit, in the64-claim post-repair pool. No12-inspection discovery phase is modeled.",
    "independent_noise_assumptions": ["Simple random sample without replacement", "Fixed labels and immutable pool", "No false positives", "Independent Bernoulli detection on each sampled true defect", "Known lower sensitivity q0 with actualq>=q0", "One predeclared look", "Detected positives are correctly repaired locally; no other labels change"],
    "residual": "K-Y includes false negatives inside the audited sample and missed defects outside it.",
    "upper_bound": "U(y)=max{K in[y,N]: P_q0(Y<=y)>delta}; residual bound U(y)-y. K upper search limit isN, notN-n+y.",
    "claims": "Per frozen instance unconditional coverage over sampling/detection randomness. Not conditional coverage among passed audits or simultaneous corpus coverage.",
    "pass_probability": "Sum ALL feasibleY states satisfyingU(Y)-Y<=6; pass need not be monotone inY.",
    "limitations": ["No estimated sensitivity, specificity error or semantic model accuracy", "No dependency drift, correlated noise guarantee or global business-loss guarantee", "Misspecified/correlated scenarios deliberately violate calibrated independent assumptions", "Known hypergeometric/binomial inversion; no statistical novelty claimed"],
}


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, obj: Any) -> None:
    if not path.resolve().is_relative_to(STUDY_ROOT):
        raise ValueError("Study artifacts may be written only within this new study directory")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(canonical(obj) + b"\n")


@lru_cache(maxsize=None)
def pmf_numerators(N: int, K: int, n: int, q: Fraction) -> tuple[tuple[int, ...], int]:
    """Exact noisy-hypergeometric PMF with common integer denominator.

    sum_h C(K,h)C(N-K,n-h)C(h,y)a^y(b-a)^(h-y)b^(n-h)
    divided by C(N,n)b^n, for q=a/b. Impossible h,y terms excluded.
    Python defines0**0=1, exactly the degenerate q=0 and q=1 convention.
    """
    if not (0 <= K <= N and 0 <= n <= N and 0 <= q <= 1):
        raise ValueError("Invalid finite-population or sensitivity parameters")
    a, b = q.numerator, q.denominator
    denominator = math.comb(N, n) * b ** n
    numerators = []
    for y in range(n + 1):
        total = 0
        for h in range(max(y, n - (N - K)), min(K, n) + 1):
            total += (math.comb(K, h) * math.comb(N - K, n - h) * math.comb(h, y)
                      * a ** y * (b - a) ** (h - y) * b ** (n - h))
        numerators.append(total)
    if sum(numerators) != denominator:
        raise AssertionError("Exact PMF normalization failed")
    return tuple(numerators), denominator


@lru_cache(maxsize=None)
def independent_pmf(N: int, K: int, n: int, q: Fraction) -> tuple[Fraction, ...]:
    numerators, denominator = pmf_numerators(N, K, n, q)
    return tuple(Fraction(v, denominator) for v in numerators)


@lru_cache(maxsize=None)
def correlated_all_or_none_pmf(N: int, K: int, n: int, marginal_q: Fraction) -> tuple[Fraction, ...]:
    if not 0 <= marginal_q <= 1:
        raise ValueError("Invalid marginal sensitivity")
    hypergeom = independent_pmf(N, K, n, Fraction(1))
    result = [marginal_q * p for p in hypergeom]
    result[0] += 1 - marginal_q
    return tuple(result)


@lru_cache(maxsize=None)
def upper_total(N: int, n: int, y: int, q0: Fraction, delta: Fraction = Fraction(1, 20)) -> int:
    """Known exact inversion under a lower independent sensitivity q0.

    Search all physically possible true totals K=y..N. For q0=0 the
    bound is U=N, even for y>0 (actual sensitivity may exceed its lower bound).
    U is monotone in y; U-y, and consequently pass, need not be monotone.
    """
    if not (0 <= y <= n <= N and 0 <= q0 <= 1 and 0 < delta < 1):
        raise ValueError("Invalid audit inversion parameters")
    lo, hi = y, N
    while lo < hi:
        candidate = (lo + hi + 1) // 2
        nums, denominator = pmf_numerators(N, candidate, n, q0)
        lower_numerator = sum(nums[:y + 1])
        if lower_numerator * delta.denominator > denominator * delta.numerator:
            lo = candidate
        else:
            hi = candidate - 1
    return lo


def scenario_metrics(N: int, K: int, n: int, actual_q: Fraction, assumed_q0: Fraction,
                     noise_model: str = "independent", tau: int = 6,
                     delta: Fraction = Fraction(1, 20)) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    actual = (independent_pmf(N, K, n, actual_q) if noise_model == "independent"
              else correlated_all_or_none_pmf(N, K, n, actual_q) if noise_model == "all_or_none"
              else None)
    if actual is None:
        raise ValueError("Unknown actual noise model")
    fail = passed = unsafe = expected_residual = pass_residual_numerator = Fraction(0)
    outcomes = []
    for y, p in enumerate(actual):
        if p == 0:
            continue
        upper = upper_total(N, n, y, assumed_q0, delta)
        residual, bound = K - y, upper - y
        coverfail = K > upper
        gatepass = bound <= tau
        unsafepass = gatepass and residual > tau
        fail += p * coverfail
        passed += p * gatepass
        unsafe += p * unsafepass
        expected_residual += p * residual
        pass_residual_numerator += p * residual * gatepass
        outcomes.append({"observed_positives_y": y, "probability_exact": str(p),
                         "upper_total": upper, "residual_bound": bound,
                         "true_residual": residual, "coverage_failure": coverfail,
                         "certificate_pass": gatepass, "unsafe_pass": unsafepass})
    row = {"N": N, "K": K, "n": n, "actual_q": str(actual_q), "assumed_q0": str(assumed_q0),
           "actual_noise_model": noise_model, "delta": str(delta), "allowed_residual_defects": tau,
           "coverage_failure_probability_exact": str(fail), "coverage_failure_probability": float(fail),
           "pass_probability_exact": str(passed), "pass_probability": float(passed),
           "unsafe_pass_probability_exact": str(unsafe), "unsafe_pass_probability": float(unsafe),
           "expected_residual_exact": str(expected_residual), "expected_residual": float(expected_residual),
           "expected_residual_given_pass_exact": str(pass_residual_numerator / passed) if passed else None,
           "expected_residual_given_pass": float(pass_residual_numerator / passed) if passed else None,
           "feasible_y_states": len(outcomes), "monte_carlo": False}
    if N:
        expected_theory = Fraction(K) - Fraction(n * K, N) * actual_q
        if expected_residual != expected_theory:
            raise AssertionError("Expected remaining defects disagree with analytic expectation")
    return row, outcomes


def enumerate_scenarios() -> list[dict[str, Any]]:
    scenarios = []
    for n in PROTOCOL["sample_sizes"]:
        for actual_q_text in PROTOCOL["independent_actual_sensitivities"]:
            actual_q = Fraction(actual_q_text)
            for K in PROTOCOL["fixed_true_defect_totals"]:
                for policy, q0 in (("calibrated_independent", actual_q), ("naive_perfect_detector", Fraction(1))):
                    scenarios.append({"policy": policy, "N": PROTOCOL["population_size"], "K": K, "n": n,
                                      "actual_q": actual_q, "assumed_q0": q0, "noise_model": "independent"})
        for K in PROTOCOL["fixed_true_defect_totals"]:
            scenarios.append({"policy": "misspecified_sensitivity", "N": PROTOCOL["population_size"], "K": K, "n": n,
                              "actual_q": Fraction(PROTOCOL["misspecified"]["actual_q"]),
                              "assumed_q0": Fraction(PROTOCOL["misspecified"]["assumed_lower_q0"]), "noise_model": "independent"})
            scenarios.append({"policy": "correlation_violation", "N": PROTOCOL["population_size"], "K": K, "n": n,
                              "actual_q": Fraction(PROTOCOL["correlated"]["actual_marginal_q"]),
                              "assumed_q0": Fraction(PROTOCOL["correlated"]["assumed_independent_lower_q0"]), "noise_model": "all_or_none"})
    if len(scenarios) != PROTOCOL["planned_parameter_policy_rows"]:
        raise AssertionError("Protocol scenario count mismatch")
    return scenarios


def freeze_protocol(out: Path) -> dict[str, Any]:
    frozen = {"protocol": PROTOCOL,
              "code_sha256": {"noisy_audit.py": sha(Path(__file__)), "test_noisy_audit.py": sha(Path(__file__).with_name("test_noisy_audit.py"))},
              "frozen_before_main_exact_study": True, "clock_free": True}
    write(out, frozen)
    return {"protocol_path": str(out), "protocol_sha256": sha(out), "planned_parameter_policy_rows": PROTOCOL["planned_parameter_policy_rows"]}


CSV_FIELDS = ["policy", "N", "K", "n", "actual_q", "assumed_q0", "actual_noise_model", "delta",
              "allowed_residual_defects", "coverage_failure_probability_exact", "coverage_failure_probability",
              "pass_probability_exact", "pass_probability", "unsafe_pass_probability_exact", "unsafe_pass_probability",
              "expected_residual_exact", "expected_residual", "expected_residual_given_pass_exact", "expected_residual_given_pass", "feasible_y_states", "monte_carlo"]


def run_study(protocol_file: Path, out_dir: Path) -> dict[str, Any]:
    if not out_dir.resolve().is_relative_to(STUDY_ROOT):
        raise ValueError("Results must stay within the new study directory")
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError("Results are immutable; replay to a fresh directory")
    frozen = json.loads(protocol_file.read_text())
    if frozen["protocol"] != PROTOCOL:
        raise AssertionError("Frozen protocol mismatch")
    for filename, expected in frozen["code_sha256"].items():
        if sha(Path(__file__).with_name(filename)) != expected:
            raise AssertionError(f"Code changed after freeze: {filename}")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    total_outcomes = 0
    with (out_dir / "results.csv").open("x", newline="") as stream, \
            (out_dir / "outcomes.jsonl.gz").open("xb") as raw, \
            gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as detail:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for s in enumerate_scenarios():
            row, outcomes = scenario_metrics(s["N"], s["K"], s["n"], s["actual_q"], s["assumed_q0"],
                                             s["noise_model"], PROTOCOL["allowed_residual_defects"], Fraction(PROTOCOL["delta"]))
            row["policy"] = s["policy"]
            rows.append(row)
            total_outcomes += len(outcomes)
            writer.writerow(row)
            detail.write(canonical({"scenario": row, "outcomes": outcomes}) + b"\n")
    by_policy = {}
    for policy in sorted({r["policy"] for r in rows}):
        subset = [r for r in rows if r["policy"] == policy]
        worst_coverage = max(subset, key=lambda r: Fraction(r["coverage_failure_probability_exact"]))
        worst_unsafe = max(subset, key=lambda r: Fraction(r["unsafe_pass_probability_exact"]))
        by_policy[policy] = {"parameter_rows": len(subset),
                             "worst_coverage_failure_scenario": worst_coverage,
                             "worst_unsafe_pass_scenario": worst_unsafe,
                             "rows_exceeding_delta_coverage_failure": sum(Fraction(r["coverage_failure_probability_exact"]) > Fraction(PROTOCOL["delta"]) for r in subset),
                             "rows_exceeding_delta_unsafe_pass": sum(Fraction(r["unsafe_pass_probability_exact"]) > Fraction(PROTOCOL["delta"]) for r in subset)}
    summary = {"protocol_sha256": sha(protocol_file), "parameter_policy_rows": len(rows),
               "exact_feasible_y_outcomes_summed": total_outcomes, "monte_carlo": False,
               "known_statistical_machinery_not_new_theorem": True,
               "policy_summary": by_policy,
               "no_population_frequency_claim": "EveryK is a separate fixed-parameter scenario. No averaging overK is interpreted as a real workload failure rate.",
               "coverage_interpretation": PROTOCOL["claims"]}
    write(out_dir / "summary.json", summary)
    manifest = {p.name: sha(p) for p in sorted(out_dir.iterdir()) if p.is_file()}
    write(out_dir / "manifest.json", manifest)
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze")
    freeze.add_argument("--out", type=Path, required=True)
    run = sub.add_parser("run")
    run.add_argument("--protocol", type=Path, required=True)
    run.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    result = freeze_protocol(args.out) if args.command == "freeze" else run_study(args.protocol, args.out_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
