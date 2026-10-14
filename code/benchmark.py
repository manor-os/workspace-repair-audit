#!/usr/bin/env python3
"""Finite, deterministic selective-repair prototype. Python standard library only.

This is an idealized executable-claim benchmark, NOT an LLM benchmark or Manor
production integration. The exact hypergeometric audit is known statistical
machinery. Its assumptions, cost, fallback and failures are recorded explicitly.

Selectors receive PublicWorkspace and a charged ValidationInterface, never
ClaimSpec expressions, hidden true dependencies or value-delta labels. Python
encapsulation is a research API discipline, not an adversarial security sandbox.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path
import random
import sys
from typing import Any, Iterable


PROTOCOL = {
    "study": "Frozen executable-claim workspace repair, version 1",
    "claims_per_workspace": 64,
    "families": ["budget", "capacity", "pricing"],
    "missing_edge_rates": [0.0, 0.1, 0.3, 0.5],
    "wrong_edge_probability_per_claim": 0.05,
    "development_seed": 14001,
    "held_out_seed": 14002,
    "development_base_cases_per_family": 6,
    "held_out_base_cases_per_family": 120,
    "independent_held_out_base_workspaces": 360,
    "held_out_base_case_rate_instances": 1440,
    "fixed_validation_budget": 36,
    "ranked_discovery_budget": 12,
    "uniform_certificate_sample": 24,
    "certificate_delta_numerator": 1,
    "certificate_delta_denominator": 20,
    "residual_tolerance_numerator": 1,
    "residual_tolerance_denominator": 10,
    "certificate_interpretation": "Per frozen instance; <=floor(.10*64)=6 remaining stale claims. Not simultaneous corpus coverage, affected-claim recall or zero-error certification.",
    "validator": "Perfect deterministic value-delta labels and reference patch; all calls charged. No language models, embeddings, humans or production services.",
    "human_preservation": "Opaque protected note blocks preserved structurally by every method; no semantic conflict-resolution claim.",
    "method_components": "Known graph reachability, lexical/public-only ranking and known exact finite-population auditing; no new statistical theorem asserted.",
    "cluster_unit": "base_id; four missing-rate variants share all underlying source facts and expressions",
    "snapshot_policy": "Source state and target semantics frozen. Each artifact patch changes only its own generated block. Any source-snapshot mismatch rejects validation.",
}

FAMILY_FACTS = {
    "budget": ["campaign_budget", "service_cost", "research_cost", "reserve_amount", "channel_limit", "client_count", "report_count", "fixed_allowance"],
    "capacity": ["available_hours", "support_hours", "training_hours", "reserve_hours", "team_limit", "client_count", "report_count", "fixed_allowance"],
    "pricing": ["unit_price", "service_cost", "delivery_cost", "reserve_amount", "order_limit", "client_count", "report_count", "fixed_allowance"],
}
METHODS = (
    "observed_closure", "closure_priority_36", "lexical_36", "uniform_36",
    "risk_36", "hybrid_36", "ranked_audit_gate", "full_scan",
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def seed_for(*parts: Any) -> int:
    return int.from_bytes(hashlib.sha256(canonical(parts)).digest()[:16], "big")


def fraction_text(x: Fraction) -> str:
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


@dataclass(frozen=True)
class PublicClaim:
    claim_id: str
    title: str
    generated_block: str
    protected_block: str
    visible_citations: tuple[str, ...]
    version: str


@dataclass(frozen=True)
class PublicWorkspace:
    case_id: str
    snapshot: str
    changed_fact_id: str
    changed_fact_text: str
    before_fact: str
    after_fact: str
    claims: tuple[PublicClaim, ...]


@dataclass(frozen=True)
class ClaimSpec:
    claim_id: str
    title: str
    expression: tuple[Any, ...]
    protected_block: str
    version: str


def expression_dependencies(expression: tuple[Any, ...]) -> tuple[str, ...]:
    op = expression[0]
    if op == "source":
        return (expression[1],)
    if op == "constant":
        return ()
    if op in ("scale", "round"):
        return (expression[1],)
    return tuple(dict.fromkeys((expression[1], expression[2])))


def render_values(specs: tuple[ClaimSpec, ...], facts: dict[str, int]) -> dict[str, Fraction]:
    """Pure topological reference semantics, separate from public selectors."""
    values: dict[str, Fraction] = {}
    for s in specs:
        e, op = s.expression, s.expression[0]
        if op == "source":
            v = Fraction(facts[e[1]])
        elif op == "constant":
            v = Fraction(e[1])
        elif op == "scale":
            v = values[e[1]] * Fraction(e[2], e[3])
        elif op == "add":
            v = values[e[1]] + values[e[2]]
        elif op == "subtract":
            v = values[e[1]] - values[e[2]]
        elif op == "min":
            v = min(values[e[1]], values[e[2]])
        elif op == "max":
            v = max(values[e[1]], values[e[2]])
        elif op == "round":
            quantum = Fraction(e[2])
            v = (values[e[1]] // quantum) * quantum
        else:
            raise ValueError(f"Unknown expression operator {op!r}")
        values[s.claim_id] = Fraction(v)
    return values


def generated_text(spec: ClaimSpec | PublicClaim, value: Fraction) -> str:
    return f"{spec.title}: {fraction_text(value)}"


@dataclass(frozen=True)
class FrozenCase:
    case_id: str
    base_id: str
    split: str
    family: str
    missing_rate: float
    before_facts: dict[str, int]
    after_facts: dict[str, int]
    specs: tuple[ClaimSpec, ...]
    visible_citations: dict[str, tuple[str, ...]]
    public_order: tuple[str, ...]

    @property
    def snapshot(self) -> str:
        return digest({"after_facts": self.after_facts, "versions": [(s.claim_id, s.version) for s in self.specs]})

    def view(self) -> PublicWorkspace:
        old = render_values(self.specs, self.before_facts)
        spec_map = {s.claim_id: s for s in self.specs}
        changed = [k for k in self.before_facts if self.before_facts[k] != self.after_facts[k]]
        if len(changed) != 1:
            raise AssertionError("The protocol changes exactly one scalar source fact")
        public = []
        for cid in self.public_order:
            s = spec_map[cid]
            public.append(PublicClaim(cid, s.title, generated_text(s, old[cid]), s.protected_block,
                                      self.visible_citations[cid], s.version))
        return PublicWorkspace(self.case_id, self.snapshot, changed[0], changed[0].replace("_", " "),
                               str(self.before_facts[changed[0]]), str(self.after_facts[changed[0]]), tuple(public))

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "FrozenCase":
        x = dict(d)
        x["specs"] = tuple(ClaimSpec(s["claim_id"], s["title"], tuple(s["expression"]), s["protected_block"], s["version"]) for s in x["specs"])
        x["visible_citations"] = {k: tuple(v) for k, v in x["visible_citations"].items()}
        x["public_order"] = tuple(x["public_order"])
        return cls(**x)


def generate_base(family: str, index: int, split: str, study_seed: int) -> list[FrozenCase]:
    """Generate one base and four paired observation-error variants.

    Opaque IDs/order carry no topological positions. Titles follow expression
    topics but are not computed from impact labels. This synthetic lexical
    coupling is part of the generator, not evidence of real semantic retrieval.
    """
    rng = random.Random(seed_for(study_seed, family, index, "base"))
    base_id = f"{split}:{family}:{index:03d}"
    keys = FAMILY_FACTS[family]
    primary = keys[0]
    start = ({"budget": 100000, "capacity": 800, "pricing": 120}[family]
             + rng.randrange(1, 40) * {"budget": 100, "capacity": 2, "pricing": 1}[family])
    before = {primary: start}
    for j, key in enumerate(keys[1:], 1):
        before[key] = max(1, start // (j + 2) + rng.randrange(1, 31))
    after = dict(before)
    after[primary] = max(1, start * rng.choice([6, 8, 12, 15]) // 10)
    ids = [f"c_{rng.getrandbits(80):020x}" for _ in range(64)]
    specs: list[ClaimSpec] = []
    primary_chain: list[str] = []
    topics: dict[str, str] = {}
    for i, cid in enumerate(ids):
        if i < 8:
            e = ("source", keys[i])
            topic = keys[i].replace("_", " ")
            if i == 0:
                primary_chain.append(cid)
        elif i < 12:
            e = ("constant", rng.randrange(5, 50))
            topic = rng.choice(["client notes", "review schedule", "service assumptions", "delivery reserve"])
        else:
            kind = (i - 12) % 8
            parent = rng.choice(primary_chain) if rng.random() < .65 else rng.choice(ids[:i])
            other = rng.choice(ids[:i])
            topic = topics[parent]
            if kind == 0:
                e = ("scale", parent, rng.choice([1, 2, 3, 5]), rng.choice([2, 4, 10]))
                primary_chain.append(cid)
            elif kind == 1:
                e = ("add", parent, other)
                primary_chain.append(cid)
            elif kind == 2:
                e = ("subtract", parent, parent)  # Value cancellation despite true provenance.
            elif kind == 3:
                e = ("min", parent, ids[rng.randrange(8, 12)])  # Independent support/bound can dominate.
            elif kind == 4:
                e = ("max", parent, ids[rng.randrange(8, 12)])
            elif kind == 5:
                e = ("scale", ids[rng.randrange(1, 8)], 1, rng.choice([2, 4]))
                topic = topics[e[1]]
            elif kind == 6:
                e = ("round", parent, max(1, start // rng.choice([2, 5, 10])))
                primary_chain.append(cid)
            else:
                e = ("subtract", parent, other)
                primary_chain.append(cid)
            # Mask some lexical cues without looking at any before/new label.
            if rng.random() < .30:
                topic = rng.choice(["delivery estimate", "review summary", "client schedule", "service allowance"])
        topics[cid] = topic
        title = f"{topic.title()} {rng.choice(['summary', 'allocation', 'estimate', 'check'])}"
        human = ""
        if rng.random() < .30:
            human = f"Human note {rng.getrandbits(32):08x}: retain the agreed review wording and client-specific preference."
        specs.append(ClaimSpec(cid, title, e, human, f"v_{rng.getrandbits(64):016x}"))
    order = list(ids)
    rng.shuffle(order)
    # Coupled edge deletion uniforms across rates; incorrect edges fixed across rates.
    obs_rng = random.Random(seed_for(study_seed, family, index, "observation"))
    edge_u = {(s.claim_id, dep): obs_rng.random() for s in specs for dep in expression_dependencies(s.expression)}
    wrong: dict[str, str] = {}
    for s in specs:
        if obs_rng.random() < PROTOCOL["wrong_edge_probability_per_claim"]:
            valid_wrong = [x for x in ids if x != s.claim_id and x not in expression_dependencies(s.expression)]
            wrong[s.claim_id] = obs_rng.choice(valid_wrong)
    cases = []
    for rate in PROTOCOL["missing_edge_rates"]:
        visible = {}
        for s in specs:
            deps = [d for d in expression_dependencies(s.expression) if edge_u[(s.claim_id, d)] >= rate]
            if s.claim_id in wrong:
                deps.append(wrong[s.claim_id])
            visible[s.claim_id] = tuple(sorted(set(deps)))
        cases.append(FrozenCase(f"{base_id}:missing={rate:.1f}", base_id, split, family, rate, before, after,
                                tuple(specs), visible, tuple(order)))
    return cases


class SnapshotChanged(RuntimeError):
    pass


@dataclass(frozen=True)
class ValidationResult:
    claim_id: str
    stale: bool
    patched: bool


class ValidationInterface:
    """Idealized perfect validator + isolated generated-block patch.

    The ONLY method interface that reveals a value-delta label. A call is charged
    even when repeated; policies below never repeat. Targets are pure functions
    of frozen source facts; patching one block cannot change another label.
    """
    __slots__ = ("__snapshot", "__targets", "__initial", "__current", "__human", "__calls", "__trace")

    def __init__(self, case: FrozenCase):
        old = render_values(case.specs, case.before_facts)
        new = render_values(case.specs, case.after_facts)
        self.__snapshot = case.snapshot
        self.__targets = {s.claim_id: generated_text(s, new[s.claim_id]) for s in case.specs}
        self.__initial = {s.claim_id: generated_text(s, old[s.claim_id]) for s in case.specs}
        self.__current = dict(self.__initial)
        self.__human = {s.claim_id: s.protected_block for s in case.specs}
        self.__calls = 0
        self.__trace: list[dict[str, Any]] = []

    def validate_and_patch(self, claim_id: str, snapshot: str) -> ValidationResult:
        if snapshot != self.__snapshot:
            raise SnapshotChanged("Source/artifact snapshot differs from the frozen validation scope")
        if claim_id not in self.__targets:
            raise KeyError(claim_id)
        self.__calls += 1
        before = self.__current[claim_id]
        stale = before != self.__targets[claim_id]
        human_hash = hashlib.sha256(self.__human[claim_id].encode()).hexdigest()
        if stale:
            self.__current[claim_id] = self.__targets[claim_id]
        self.__trace.append({"call": self.__calls, "claim_id": claim_id, "stale": stale, "patched": stale,
                              "old_generated": before, "new_generated": self.__current[claim_id],
                              "protected_sha256_before": human_hash, "protected_sha256_after": human_hash})
        return ValidationResult(claim_id, stale, stale)

    def evaluator_report(self) -> dict[str, Any]:
        """Evaluation ONLY. Never passed or invoked by selector policies."""
        initial_stale = {k for k in self.__targets if self.__initial[k] != self.__targets[k]}
        residual = {k for k in self.__targets if self.__current[k] != self.__targets[k]}
        patched = sum(t["patched"] for t in self.__trace)
        return {"validator_calls": self.__calls, "initial_stale_count": len(initial_stale),
                "residual_stale_count": len(residual), "initial_stale_ids": sorted(initial_stale),
                "residual_stale_ids": sorted(residual), "patched_count": patched,
                "protected_blocks": sum(bool(x) for x in self.__human.values()),
                "protected_blocks_altered": 0, "trace": list(self.__trace),
                "final_generated": dict(self.__current), "protected_blocks_text": dict(self.__human)}


def closure_ids(view: PublicWorkspace) -> set[str]:
    children: dict[str, set[str]] = {}
    for c in view.claims:
        for dep in c.visible_citations:
            children.setdefault(dep, set()).add(c.claim_id)
    seen: set[str] = set()
    pending = [view.changed_fact_id]
    while pending:
        cur = pending.pop()
        for child in children.get(cur, ()):
            if child not in seen:
                seen.add(child)
                pending.append(child)
    return seen


def lexical_score(view: PublicWorkspace, claim: PublicClaim) -> int:
    changed_tokens = set(view.changed_fact_text.lower().split())
    title_tokens = set(claim.title.lower().split())
    return len(changed_tokens & title_tokens)


def rank_ids(view: PublicWorkspace, ranking: str) -> list[str]:
    """Untrained public-only signals. No gold dependencies or impact labels."""
    closure = closure_ids(view)
    inbound = {c.claim_id: 0 for c in view.claims}
    for c in view.claims:
        for dep in c.visible_citations:
            if dep in inbound:
                inbound[dep] += 1
    def score(c: PublicClaim) -> tuple[Any, ...]:
        if ranking == "lexical":
            return (lexical_score(view, c),)
        if ranking == "closure":
            return (int(c.claim_id in closure),)
        if ranking == "risk":
            risk = (8 * int(c.claim_id in closure) + 4 * int(view.changed_fact_id in c.visible_citations)
                    + 2 * lexical_score(view, c) + int(not c.visible_citations)
                    + Fraction(min(4, inbound[c.claim_id]), 4))
            return (risk,)
        raise ValueError(ranking)
    return [c.claim_id for c in sorted(view.claims, key=lambda c: (score(c), c.claim_id), reverse=True)]


@lru_cache(maxsize=None)
def hypergeom_lower_numerator(N: int, K: int, n: int, k: int) -> int:
    return sum(math.comb(K, x) * math.comb(N - K, n - x)
               for x in range(max(0, n - (N - K)), min(k, n, K) + 1))


@lru_cache(maxsize=None)
def exact_upper_total(N: int, n: int, k: int, delta: Fraction = Fraction(1, 20)) -> int:
    """Known one-sided exact hypergeometric inversion; integer arithmetic.

    U=max{K in[k,N-n+k]: P_K(X<=k)>delta}. Strict > avoids an
    anticonservative boundary. k is the number of positive audit labels.
    Labels belong to a fixed pool. With k=0, obtaining U=0 requires
    n/N >=1-delta: under K=1 the no-detection probability is (N-n)/N.
    """
    if not (0 <= k <= n <= N) or not (0 < delta < 1):
        raise ValueError("Invalid finite-population audit parameters")
    denominator = math.comb(N, n)
    lo, hi = k, N - n + k
    while lo < hi:
        mid = (lo + hi + 1) // 2
        tail_numer = hypergeom_lower_numerator(N, mid, n, k)
        if tail_numer * delta.denominator > denominator * delta.numerator:
            lo = mid
        else:
            hi = mid - 1
    return lo


def inspect_ids(view: PublicWorkspace, validator: ValidationInterface, ids: Iterable[str]) -> list[ValidationResult]:
    return [validator.validate_and_patch(cid, view.snapshot) for cid in ids]


def select_and_repair(view: PublicWorkspace, validator: ValidationInterface, method: str, policy_seed: int) -> dict[str, Any]:
    """Policy boundary: inputs have no executable/gold claims or reference labels."""
    n_all = len(view.claims)
    budget = min(PROTOCOL["fixed_validation_budget"], n_all)
    certificate = None
    if method == "full_scan":
        inspected = [c.claim_id for c in view.claims]
        inspect_ids(view, validator, inspected)
    elif method == "observed_closure":
        inspected = sorted(closure_ids(view))
        inspect_ids(view, validator, inspected)
    elif method in ("closure_priority_36", "lexical_36", "risk_36"):
        ranking = {"closure_priority_36": "closure", "lexical_36": "lexical", "risk_36": "risk"}[method]
        inspected = rank_ids(view, ranking)[:budget]
        inspect_ids(view, validator, inspected)
    elif method == "uniform_36":
        inspected = random.Random(policy_seed).sample(sorted(c.claim_id for c in view.claims), budget)
        inspect_ids(view, validator, inspected)
    elif method in ("hybrid_36", "ranked_audit_gate"):
        discovery = rank_ids(view, "risk")[:min(PROTOCOL["ranked_discovery_budget"], n_all)]
        inspect_ids(view, validator, discovery)
        frozen_pool = sorted(set(c.claim_id for c in view.claims) - set(discovery))
        # Exactly one prespecified look; no label-adaptive certification retries.
        sample_n = min(PROTOCOL["uniform_certificate_sample"], len(frozen_pool))
        audit = random.Random(policy_seed).sample(frozen_pool, sample_n)
        results = inspect_ids(view, validator, audit)
        inspected = discovery + audit
        if method == "ranked_audit_gate":
            k = sum(r.stale for r in results)
            delta = Fraction(PROTOCOL["certificate_delta_numerator"], PROTOCOL["certificate_delta_denominator"])
            epsilon = Fraction(PROTOCOL["residual_tolerance_numerator"], PROTOCOL["residual_tolerance_denominator"])
            upper_total = exact_upper_total(len(frozen_pool), sample_n, k, delta)
            upper_uninspected = upper_total - k
            threshold = math.floor(epsilon * n_all)
            passed = upper_uninspected <= threshold
            certificate = {"pool_size": len(frozen_pool), "sample_size": sample_n, "sample_positives": k,
                           "delta": fraction_text(delta), "epsilon": fraction_text(epsilon),
                           "upper_total_in_frozen_pool": upper_total,
                           "upper_uninspected_stale": upper_uninspected, "allowed_residual_count": threshold,
                           "passed": passed, "fallback_full_scan": not passed,
                           "frozen_pool_ids": frozen_pool, "audit_ids": audit,
                           "scope": "single-instance count; idealized perfect labels and immutable reference targets"}
            if not passed:
                remaining = sorted(set(frozen_pool) - set(audit))
                inspect_ids(view, validator, remaining)
                inspected += remaining
    else:
        raise ValueError(method)
    if len(inspected) != len(set(inspected)):
        raise AssertionError("Policy repeated a claim inspection")
    return {"inspected_ids": inspected, "certificate": certificate}


def evaluate(case: FrozenCase, method: str) -> dict[str, Any]:
    view = case.view()
    validator = ValidationInterface(case)
    # Matched random order for hybrid/certified policy; deterministic per case.
    policy_seed = seed_for(case.case_id, "audit-order", PROTOCOL["held_out_seed"] if case.split == "test" else PROTOCOL["development_seed"])
    chosen = select_and_repair(view, validator, method, policy_seed)
    result = validator.evaluator_report()
    result.update({"case_id": case.case_id, "base_id": case.base_id, "split": case.split,
                   "family": case.family, "missing_edge_rate": case.missing_rate,
                   "method": method, "scope_claim_count": len(view.claims),
                   "snapshot": view.snapshot, "inspected_ids": chosen["inspected_ids"],
                   "certificate": chosen["certificate"], "all_claims_current": result["residual_stale_count"] == 0,
                   "validation_fraction": result["validator_calls"] / len(view.claims),
                   "residual_fraction_all_claims": result["residual_stale_count"] / len(view.claims),
                   "impact_recall": None if result["initial_stale_count"] == 0 else 1 - result["residual_stale_count"] / result["initial_stale_count"],
                   "unnecessary_validations": result["validator_calls"] - result["patched_count"],
                   "semantic_human_conflicts_evaluated": False,
                   "model_calls": 0, "production_integration": False})
    if chosen["certificate"] is not None:
        cert = result["certificate"]
        initial_stale = set(result["initial_stale_ids"])
        true_pool_K = len(initial_stale & set(cert["frozen_pool_ids"]))
        true_remaining = true_pool_K - cert["sample_positives"]
        cert.update({"evaluator_true_pool_stale": true_pool_K,
                     "evaluator_true_uninspected_stale": true_remaining,
                     "coverage_failure": true_remaining > cert["upper_uninspected_stale"],
                     "unsafe_gate_release": cert["passed"] and true_remaining > cert["allowed_residual_count"]})
    return result


def exhaustive_coverage_sanity(max_N: int = 12) -> dict[str, Any]:
    """Enumerate ALL possible binary totals, sample sizes and observed counts.

    Exact probabilities over sample-count outcomes, not Monte Carlo samples.
    This checks a known bound implementation, not a new theorem or model.
    """
    delta = Fraction(1, 20)
    combinations, outcomes = 0, 0
    maximum = Fraction(0)
    for N in range(max_N + 1):
        for n in range(N + 1):
            for K in range(N + 1):
                failure = Fraction(0)
                for k in range(max(0, n - (N - K)), min(n, K) + 1):
                    outcomes += 1
                    if exact_upper_total(N, n, k, delta) < K:
                        failure += Fraction(math.comb(K, k) * math.comb(N - K, n - k), math.comb(N, n))
                combinations += 1
                maximum = max(maximum, failure)
                if failure > delta:
                    raise AssertionError((N, n, K, fraction_text(failure)))
    return {"passed": True, "max_population_size": max_N, "all_N_n_K_combinations": combinations,
            "all_feasible_count_outcomes": outcomes, "max_exact_undercoverage_probability": fraction_text(maximum),
            "nominal_delta": fraction_text(delta), "monte_carlo_used": False}


def freeze_dataset(data_dir: Path) -> dict[str, Any]:
    if data_dir.exists() and any(data_dir.iterdir()):
        raise FileExistsError("Freeze destination must be empty; existing study artifacts are immutable")
    data_dir.mkdir(parents=True, exist_ok=True)
    protocol_bytes = canonical(PROTOCOL) + b"\n"
    (data_dir / "protocol.json").write_bytes(protocol_bytes)
    counts = {"dev": 0, "test": 0}
    base_counts = {"dev": 0, "test": 0}
    with (data_dir / "cases.jsonl").open("wb") as f:
        for split, seed_key, count_key in (("dev", "development_seed", "development_base_cases_per_family"),
                                            ("test", "held_out_seed", "held_out_base_cases_per_family")):
            for family in PROTOCOL["families"]:
                for index in range(PROTOCOL[count_key]):
                    cases = generate_base(family, index, split, PROTOCOL[seed_key])
                    base_counts[split] += 1
                    for case in cases:
                        f.write(canonical(case.to_dict()) + b"\n")
                        counts[split] += 1
    manifest = {"protocol_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
                "cases_sha256": hashlib.sha256((data_dir / "cases.jsonl").read_bytes()).hexdigest(),
                "benchmark_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "instance_counts": counts, "independent_base_workspace_counts": base_counts,
                "frozen_before_any_outcomes": True, "no_clock_dependent_content": True}
    (data_dir / "freeze_manifest.json").write_bytes(canonical(manifest) + b"\n")
    return manifest


def load_frozen(data_dir: Path, split: str) -> list[FrozenCase]:
    manifest = json.loads((data_dir / "freeze_manifest.json").read_text())
    current_protocol = (data_dir / "protocol.json").read_bytes()
    if hashlib.sha256(current_protocol).hexdigest() != manifest["protocol_sha256"] or json.loads(current_protocol) != PROTOCOL:
        raise AssertionError("Frozen protocol mismatch")
    cases_bytes = (data_dir / "cases.jsonl").read_bytes()
    if hashlib.sha256(cases_bytes).hexdigest() != manifest["cases_sha256"]:
        raise AssertionError("Frozen case hash mismatch")
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != manifest["benchmark_code_sha256"]:
        raise AssertionError("Code changed after freeze; freeze a new explicitly versioned study")
    cases = [FrozenCase.from_dict(json.loads(line)) for line in cases_bytes.splitlines() if line]
    selected = [c for c in cases if c.split == split]
    if len(selected) != manifest["instance_counts"][split]:
        raise AssertionError("Frozen instance count mismatch")
    return selected


CSV_FIELDS = ["case_id", "base_id", "split", "family", "missing_edge_rate", "method", "scope_claim_count",
              "initial_stale_count", "residual_stale_count", "validator_calls", "patched_count", "unnecessary_validations",
              "validation_fraction", "residual_fraction_all_claims", "impact_recall", "all_claims_current",
              "protected_blocks", "protected_blocks_altered", "certificate_passed", "fallback_full_scan",
              "certificate_upper_uninspected", "certificate_actual_uninspected", "certificate_coverage_failure", "unsafe_gate_release"]


def flatten_result(result: dict[str, Any]) -> dict[str, Any]:
    d = {k: result[k] for k in CSV_FIELDS if k in result}
    cert = result["certificate"]
    for target, source in (("certificate_passed", "passed"), ("fallback_full_scan", "fallback_full_scan"),
                           ("certificate_upper_uninspected", "upper_uninspected_stale"),
                           ("certificate_actual_uninspected", "evaluator_true_uninspected_stale"),
                           ("certificate_coverage_failure", "coverage_failure"), ("unsafe_gate_release", "unsafe_gate_release")):
        d[target] = None if cert is None else cert[source]
    return d


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {}
    for method in METHODS:
        subset = [r for r in rows if r["method"] == method]
        if not subset:
            continue
        n = len(subset)
        impacted = sum(r["initial_stale_count"] for r in subset)
        residual = sum(r["residual_stale_count"] for r in subset)
        certs = [r["certificate"] for r in subset if r["certificate"] is not None]
        summary[method] = {
            "instances": n, "independent_base_workspaces": len({r["base_id"] for r in subset}),
            "mean_validations": sum(r["validator_calls"] for r in subset) / n,
            "mean_residual_stale": residual / n,
            "micro_impact_recall": None if not impacted else 1 - residual / impacted,
            "all_current_instances": sum(r["all_claims_current"] for r in subset),
            "all_current_instance_fraction": sum(r["all_claims_current"] for r in subset) / n,
            "protected_blocks_altered": sum(r["protected_blocks_altered"] for r in subset),
            "certificate_passes": sum(c["passed"] for c in certs),
            "fallbacks": sum(c["fallback_full_scan"] for c in certs),
            "certificate_coverage_failures": sum(c["coverage_failure"] for c in certs),
            "unsafe_gate_releases": sum(c["unsafe_gate_release"] for c in certs),
        }
    return {"methods": summary, "distinct_instance_count": len({r["case_id"] for r in rows}),
            "independent_base_workspace_count": len({r["base_id"] for r in rows}),
            "method_case_executions": len(rows), "independence_warning": PROTOCOL["cluster_unit"],
            "scope": PROTOCOL["validator"], "total_model_calls": 0}


def run_dataset(data_dir: Path, out_dir: Path, split: str) -> dict[str, Any]:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError("Results destination must be empty; use a fresh replay directory")
    cases = load_frozen(data_dir, split)
    out_dir.mkdir(parents=True, exist_ok=True)
    sanity = exhaustive_coverage_sanity()
    (out_dir / "exact_coverage_sanity.json").write_bytes(canonical(sanity) + b"\n")
    rows = []
    with (out_dir / "detailed_results.jsonl.gz").open("wb") as raw, \
            gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as jf, \
            (out_dir / "results.csv").open("w", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for i, case in enumerate(cases):
            for method in METHODS:
                r = evaluate(case, method)
                jf.write(canonical(r) + b"\n")
                writer.writerow(flatten_result(r))
                # Keep summary rows small; detailed trace is persisted above.
                rows.append({k: v for k, v in r.items() if k not in {"trace", "final_generated", "protected_blocks_text", "initial_stale_ids", "residual_stale_ids", "inspected_ids"}})
            if (i + 1) % 120 == 0:
                print(f"Completed {i + 1}/{len(cases)} {split} instances", file=sys.stderr, flush=True)
    summary = summarize(rows)
    summary["freeze_manifest"] = json.loads((data_dir / "freeze_manifest.json").read_text())
    (out_dir / "summary.json").write_bytes(canonical(summary) + b"\n")
    result_manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out_dir.iterdir()) if p.is_file()}
    (out_dir / "result_manifest.json").write_bytes(canonical(result_manifest) + b"\n")
    return summary


def export_example(data_dir: Path, out_dir: Path, case_id: str | None = None) -> dict[str, Any]:
    cases = load_frozen(data_dir, "test")
    case = next(c for c in cases if c.case_id == case_id) if case_id else cases[2]
    out_dir.mkdir(parents=True, exist_ok=True)
    view = case.view()
    result = evaluate(case, "ranked_audit_gate")
    for label, current in (("before", {c.claim_id: c.generated_block for c in view.claims}),
                            ("after", result["final_generated"])):
        lines = [f"# {case.case_id}", "", f"Source update: {view.changed_fact_text}, {view.before_fact} -> {view.after_fact}",
                 f"Frozen snapshot: {view.snapshot}", "", "Protected notes are structurally retained. Labels/targets are idealized executable claims.", ""]
        for c in view.claims:
            lines += [f"## {c.claim_id}", "", current[c.claim_id], "", f"Visible citations: {', '.join(c.visible_citations) or '(none)'}", ""]
            if c.protected_block:
                lines += ["<!-- HUMAN-PROTECTED-BEGIN -->", c.protected_block, "<!-- HUMAN-PROTECTED-END -->", ""]
        (out_dir / f"workspace_{label}.md").write_text("\n".join(lines))
    (out_dir / "case.json").write_bytes(canonical(case.to_dict()) + b"\n")
    (out_dir / "repair_trace.json").write_bytes(canonical(result) + b"\n")
    return {"case_id": case.case_id, "method": result["method"], "validator_calls": result["validator_calls"],
            "residual_stale_count": result["residual_stale_count"]}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    freeze = sub.add_parser("freeze", help="Freeze protocol and all cases before any method outcomes")
    freeze.add_argument("--data-dir", type=Path, required=True)
    run = sub.add_parser("run", help="Run exactly the frozen cases; no parameter tuning")
    run.add_argument("--data-dir", type=Path, required=True)
    run.add_argument("--out-dir", type=Path, required=True)
    run.add_argument("--split", choices=["dev", "test"], required=True)
    sanity = sub.add_parser("sanity", help="Exhaustive exact-coverage implementation check through N=12")
    example = sub.add_parser("example", help="Export one rendered synthetic workspace and trace")
    example.add_argument("--data-dir", type=Path, required=True)
    example.add_argument("--out-dir", type=Path, required=True)
    example.add_argument("--case-id")
    args = p.parse_args()
    if args.command == "freeze":
        result = freeze_dataset(args.data_dir)
    elif args.command == "run":
        result = run_dataset(args.data_dir, args.out_dir, args.split)
    elif args.command == "sanity":
        result = exhaustive_coverage_sanity()
    else:
        result = export_example(args.data_dir, args.out_dir, args.case_id)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
