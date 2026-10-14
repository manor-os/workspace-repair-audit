#!/usr/bin/env python3
"""Frozen synthetic workspace extraction/repair pilot. No provider calls.

The public task contract is natural English; expression DAGs and labels live
only in evaluator/gold.json. This measures a small synthetic subsystem, not
production agents, a novel theorem, or natural business-workspace performance.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any

SEED = 20261014
CLAIM_IDS = tuple(f"C{i:02}" for i in range(1, 13))
SOURCE_IDS = ("F1", "F2", "F3", "F4")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def expression(op: str, *args: Any) -> dict[str, Any]:
    return {"op": op, "args": list(args)}


def refs(node: Any) -> set[str]:
    if isinstance(node, str):
        return {node}
    if isinstance(node, dict):
        return set().union(*(refs(arg) for arg in node["args"]))
    return set()


def evaluate(node: Any, values: dict[str, Fraction]) -> Fraction:
    if isinstance(node, str):
        return values[node]
    if not isinstance(node, dict):
        return Fraction(node)
    args = [evaluate(arg, values) for arg in node["args"]]
    op = node["op"]
    if op == "add":
        return sum(args, Fraction(0))
    if op == "sub":
        return args[0] - args[1]
    if op == "mul":
        product = Fraction(1)
        for arg in args:
            product *= arg
        return product
    if op == "div":
        return args[0] / args[1]
    if op == "floor":
        return Fraction(args[0].numerator // args[0].denominator)
    if op == "min":
        return min(args)
    if op == "max":
        return max(args)
    if op == "gt":
        return Fraction(int(args[0] > args[1]))
    if op == "ge":
        return Fraction(int(args[0] >= args[1]))
    raise ValueError(f"Unknown operator: {op}")


def calculate(sources: dict[str, int], dag: dict[str, Any]) -> dict[str, Fraction]:
    values = {key: Fraction(value) for key, value in sources.items()}
    for key, node in dag.items():
        values[key] = evaluate(node, values)
    return {key: values[key] for key in CLAIM_IDS}


def number(value: Fraction) -> str:
    with localcontext() as ctx:
        ctx.prec = 40
        text = format(Decimal(value.numerator) / Decimal(value.denominator), ".8f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def domain_spec(domain: str) -> tuple[list[str], list[str], dict[str, Any]]:
    e = expression
    if domain == "budget":
        facts = ["campaign budget in USD", "cost per lead in USD", "lead-to-customer conversion percent", "revenue per customer in USD"]
        titles = ["Allocated budget", "Expected leads", "Expected customers", "Gross revenue", "Contribution", "Revenue multiple", "Reserve fund", "Working budget", "Conservative customers", "Conservative revenue", "Conservative profit", "Viable flag"]
        rules = [
            "Allocated budget [C01] repeats the campaign budget [F1].",
            "Expected leads [C02] divides campaign budget [F1] by cost per lead [F2].",
            "Expected customers [C03] multiplies expected leads [C02] by conversion percent [F3] and divides by 100.",
            "Gross revenue [C04] multiplies expected customers [C03] by revenue per customer [F4].",
            "Contribution [C05] subtracts allocated budget [C01] from gross revenue [C04].",
            "Revenue multiple [C06] divides gross revenue [C04] by allocated budget [C01].",
            "Reserve fund [C07] is one tenth of allocated budget [C01].",
            "Working budget [C08] subtracts reserve fund [C07] from allocated budget [C01].",
            "Conservative customers [C09] is working budget [C08] divided by cost per lead [F2], multiplied by conversion percent [F3], divided by 100, then rounded down to a whole number.",
            "Conservative revenue [C10] multiplies conservative customers [C09] by revenue per customer [F4].",
            "Conservative profit [C11] subtracts working budget [C08] from conservative revenue [C10].",
            "Viable flag [C12] is 1 when conservative profit [C11] is positive and 0 otherwise.",
        ]
        nodes = ["F1", e("div", "F1", "F2"), e("div", e("mul", "C02", "F3"), 100), e("mul", "C03", "F4"), e("sub", "C04", "C01"), e("div", "C04", "C01"), e("div", "C01", 10), e("sub", "C01", "C07"), e("floor", e("div", e("mul", e("div", "C08", "F2"), "F3"), 100)), e("mul", "C09", "F4"), e("sub", "C10", "C08"), e("gt", "C11", 0)]
    elif domain == "capacity":
        facts = ["available service hours", "hours per engagement", "requested client engagements", "fee per engagement in USD"]
        titles = ["Raw capacity", "Accepted engagements", "Used hours", "Idle hours", "Booked revenue", "Waitlist", "Reserve hours", "Productive hours", "Conservative capacity", "Conservative bookings", "Conservative revenue", "Demand covered flag"]
        rules = [
            "Raw capacity [C01] divides available hours [F1] by hours per engagement [F2] and rounds down.",
            "Accepted engagements [C02] is the smaller of raw capacity [C01] and requested engagements [F3].",
            "Used hours [C03] multiplies accepted engagements [C02] by hours per engagement [F2].",
            "Idle hours [C04] subtracts used hours [C03] from available hours [F1].",
            "Booked revenue [C05] multiplies accepted engagements [C02] by fee per engagement [F4].",
            "Waitlist [C06] subtracts accepted engagements [C02] from requested engagements [F3], with a minimum of zero.",
            "Reserve hours [C07] divides available hours [F1] by ten and rounds down.",
            "Productive hours [C08] subtracts reserve hours [C07] from available hours [F1].",
            "Conservative capacity [C09] divides productive hours [C08] by hours per engagement [F2] and rounds down.",
            "Conservative bookings [C10] is the smaller of conservative capacity [C09] and requested engagements [F3].",
            "Conservative revenue [C11] multiplies conservative bookings [C10] by fee per engagement [F4].",
            "Demand covered flag [C12] is 1 when conservative bookings [C10] is at least requested engagements [F3], and 0 otherwise.",
        ]
        nodes = [e("floor", e("div", "F1", "F2")), e("min", "C01", "F3"), e("mul", "C02", "F2"), e("sub", "F1", "C03"), e("mul", "C02", "F4"), e("max", e("sub", "F3", "C02"), 0), e("floor", e("div", "F1", 10)), e("sub", "F1", "C07"), e("floor", e("div", "C08", "F2")), e("min", "C09", "F3"), e("mul", "C10", "F4"), e("ge", "C10", "F3")]
    elif domain == "pricing":
        facts = ["list unit price in USD", "unit delivery cost in USD", "ordered units", "discount percent"]
        titles = ["List revenue", "Discount amount", "Net revenue", "Delivery cost", "Profit", "Margin percent", "Effective unit price", "Unit margin", "Break-even list price", "List headroom", "Maximum discount percent", "Profitable flag"]
        rules = [
            "List revenue [C01] multiplies list unit price [F1] by ordered units [F3].",
            "Discount amount [C02] multiplies list revenue [C01] by discount percent [F4] and divides by 100.",
            "Net revenue [C03] subtracts discount amount [C02] from list revenue [C01].",
            "Delivery cost [C04] multiplies unit delivery cost [F2] by ordered units [F3].",
            "Profit [C05] subtracts delivery cost [C04] from net revenue [C03].",
            "Margin percent [C06] divides profit [C05] by net revenue [C03] and multiplies by 100.",
            "Effective unit price [C07] divides net revenue [C03] by ordered units [F3].",
            "Unit margin [C08] subtracts unit delivery cost [F2] from effective unit price [C07].",
            "Break-even list price [C09] divides unit delivery cost [F2] by one minus discount percent [F4] divided by 100.",
            "List headroom [C10] subtracts delivery cost [C04] from list revenue [C01].",
            "Maximum discount percent [C11] divides list headroom [C10] by list revenue [C01] and multiplies by 100.",
            "Profitable flag [C12] is 1 when profit [C05] is positive and 0 otherwise.",
        ]
        nodes = [e("mul", "F1", "F3"), e("div", e("mul", "C01", "F4"), 100), e("sub", "C01", "C02"), e("mul", "F2", "F3"), e("sub", "C03", "C04"), e("mul", e("div", "C05", "C03"), 100), e("div", "C03", "F3"), e("sub", "C07", "F2"), e("div", "F2", e("sub", 1, e("div", "F4", 100))), e("sub", "C01", "C04"), e("mul", e("div", "C10", "C01"), 100), e("gt", "C05", 0)]
    else:
        raise ValueError(domain)
    dag = dict(zip(CLAIM_IDS, nodes, strict=True))
    return facts, titles, {"rules": rules, "dag": dag}


def render_claim(claim_id: str, title: str, value: Fraction, index: int) -> dict[str, str]:
    value_text = number(value)
    fmt = ("markdown", "csv", "json")[index % 3]
    if fmt == "markdown":
        content = f"### {title}\nThe current {title.lower()} is **{value_text}**."
    elif fmt == "csv":
        content = f"metric,value\n{title},{value_text}\n"
    else:
        content = json.dumps({"metric": title, "value": value_text}, sort_keys=True)
    return {"id": claim_id, "format": fmt, "content": content}


def extraction_messages(case: dict[str, Any]) -> list[dict[str, str]]:
    payload = {key: case[key] for key in ("case_id", "domain", "before_sources", "task_contract", "artifacts", "human_notes")}
    return [
        {"role": "system", "content": "Extract immediate numerical derivation dependencies from the given workspace task contract and its before-update artifacts. Return JSON only: {\"dependencies\":{\"C01\":[\"F1\"],...}}. Include all twelve claim IDs. A dependency is a source fact or another claim whose value the stated computation directly reads. Include direct operands, not their transitive ancestors. Constants and editorial human notes are not dependencies. Never infer a dependency solely because two displayed values happen to match. Allowed IDs are F1-F4 and C01-C12. Do not output calculations or hidden reasoning."},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]


def build_repair_messages(case: dict[str, Any], selected_ids: list[str]) -> list[dict[str, str]]:
    if len(set(selected_ids)) != len(selected_ids) or any(key not in CLAIM_IDS for key in selected_ids):
        raise ValueError("Repair selection must contain unique known claim IDs")
    payload = {key: case[key] for key in ("case_id", "domain", "after_sources", "task_contract", "artifacts", "human_notes")}
    payload["selected_ids"] = selected_ids
    return [
        {"role": "system", "content": "Update only the selected numerical claim blocks after the source update, following the stated task contract. Return JSON only: {\"updates\":{\"C01\":123.45,...}}. Emit exactly selected_ids. Compute using current source facts and unrounded intermediate values, even if other stored artifacts are stale; numeric answers should have at least six decimal places when nonintegral. Preserve human notes and all unselected stored artifacts. Do not output hidden reasoning."},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]


def generate() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cases, gold = [], {}
    for domain in ("budget", "capacity", "pricing"):
        fact_titles, titles, spec = domain_spec(domain)
        for index in range(6):
            case_id = f"{domain}_{index+1:02}"
            if domain == "budget":
                base = [8000 + index * 1400, 16 + index * 2, 4 + index, 350 + index * 75]
            elif domain == "capacity":
                base = [120 + index * 24, 8 + index, (6 if index % 2 == 0 else 24) + index, 650 + index * 100]
            else:
                base = [95 + index * 15, 55 + index * 8, 25 + index * 7, 5 + index * 3]
            before = dict(zip(SOURCE_IDS, base, strict=True))
            after = dict(before)
            changed = ("F1", "F2", "F3", "F4", "F1", "F2")[index]
            after[changed] += max(1, before[changed] // (3 if index % 2 else 2))
            if changed == "F4" and domain in ("budget", "pricing"):
                after[changed] = min(after[changed], 80) if domain == "pricing" else after[changed]
            old = calculate(before, spec["dag"])
            new = calculate(after, spec["dag"])
            case = {"case_id": case_id, "domain": domain,
                    "before_sources": [{"id": key, "name": title, "value": before[key]} for key, title in zip(SOURCE_IDS, fact_titles, strict=True)],
                    "after_sources": [{"id": key, "name": title, "value": after[key]} for key, title in zip(SOURCE_IDS, fact_titles, strict=True)],
                    "task_contract": {"instructions": "Maintain these twelve numeric claims across the workspace. Keep exact intermediate values; displayed decimals are rounded views. F1-F4 are authoritative source facts. A flag is numeric 0 or1. Preserve both human notes unchanged.", "rules": spec["rules"]},
                    "artifacts": [render_claim(key, title, old[key], position) for position, (key, title) in enumerate(zip(CLAIM_IDS, titles, strict=True))],
                    "human_notes": [{"id": "H01", "text": f"Client {index+1}: retain the signed service-terms wording."}, {"id": "H02", "text": "Editorial decision: use a plain-language executive summary; keep the disclaimer intact."}]}
            case["extraction_messages"] = extraction_messages(case)
            cases.append(case)
            gold[case_id] = {"expression_dag": spec["dag"], "dependencies": {key: sorted(refs(node)) for key, node in spec["dag"].items()}, "changed_sources": [changed], "before_values": {key: number(value) for key, value in old.items()}, "after_values": {key: number(value) for key, value in new.items()}, "exact_affected_ids": [key for key in CLAIM_IDS if old[key] != new[key]], "before_rationals": {key: [value.numerator, value.denominator] for key, value in old.items()}, "after_rationals": {key: [value.numerator, value.denominator] for key, value in new.items()}}
    return cases, gold


def prepare(out: Path) -> None:
    if out.exists() and any(out.iterdir()):
        raise ValueError("Refusing to replace a nonempty prepared directory")
    cases, gold = generate()
    write_json(out / "public/inputs.json", {"schema_version": 1, "cases": cases})
    write_json(out / "evaluator/gold.json", {"schema_version": 1, "cases": gold})
    protocol = {"schema_version": 1, "seed": SEED, "case_count": 18, "domains": ["budget", "capacity", "pricing"], "cases_per_domain": 6, "claims_per_case": 12, "source_facts_per_case": 4, "mixed_formats": ["markdown", "csv", "json"], "freeze_before_model_calls": True, "gold_visible_to_extractor": False, "extraction_calls_planned": 18, "repair_calls_optional": 18, "maximum_response_tokens_requested": 2500, "numeric_tolerance": {"absolute": 0.0001, "relative": 0.000001}, "primary_scope": "Natural model dependency extraction errors on authored synthetic task contracts; not real-world business cases or full-agent evaluation.", "impact_truth": "Exact rational before/after numeric value change, not dependency reachability.", "routing_metric_limit": "Reachability can conservatively overselect mathematically unchanged claims, including ratios and bottleneck branches.", "no_new_statistical_theorem_claim": True, "implementation_sha256": digest(Path(__file__)), "files": {"public/inputs.json": digest(out / "public/inputs.json"), "evaluator/gold.json": digest(out / "evaluator/gold.json")}}
    write_json(out / "protocol.json", protocol)


def load_prepared(directory: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol = json.loads((directory / "protocol.json").read_text())
    for filename, expected in protocol["files"].items():
        if digest(directory / filename) != expected:
            raise ValueError(f"Frozen file changed: {filename}")
    public = json.loads((directory / "public/inputs.json").read_text())
    gold = json.loads((directory / "evaluator/gold.json").read_text())
    return public, gold, protocol


def normalize_response(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise ValueError("Model response must be a JSON object")
    return value


def routed_claims(dependencies: dict[str, list[str]], changed_sources: list[str]) -> set[str]:
    reached = set(changed_sources)
    while True:
        extra = {key for key, operands in dependencies.items() if any(operand in reached for operand in operands)} - reached
        if not extra:
            return reached & set(CLAIM_IDS)
        reached.update(extra)


def prf(predicted: set[Any], expected: set[Any]) -> dict[str, Any]:
    tp, fp, fn = len(predicted & expected), len(predicted - expected), len(expected - predicted)
    precision = tp / (tp + fp) if tp + fp else (1.0 if not expected else 0.0)
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0, "exact": predicted == expected}


def close_numeric(value: Any, expected: str) -> bool:
    if isinstance(value, bool):
        return False
    try:
        actual, wanted = Decimal(str(value)), Decimal(expected)
        return actual.is_finite() and abs(actual - wanted) <= max(Decimal("0.0001"), abs(wanted) * Decimal("0.000001"))
    except Exception:
        return False


def score_repair(record: dict[str, Any], label: dict[str, Any]) -> dict[str, Any]:
    selected = record.get("selected_ids")
    if not isinstance(selected, list) or len(set(selected)) != len(selected) or any(key not in CLAIM_IDS for key in selected):
        raise ValueError("Repair response requires selected_ids with unique known claims")
    response = normalize_response(record["repair_response"])
    updates = response.get("updates")
    if not isinstance(updates, dict):
        raise ValueError("Repair response needs an updates object")
    exact_keys = set(updates) == set(selected)
    final = dict(label["before_values"])
    for key in selected:
        if key in updates:
            final[key] = updates[key]
    correct = [key for key in CLAIM_IDS if close_numeric(final[key], label["after_values"][key])]
    return {"selected_ids": selected, "exact_update_keys": exact_keys, "correct_final_claim_count": len(correct), "final_correct_ids": correct, "all_final_claims_correct": len(correct) == 12 and exact_keys, "selected_repair_accuracy": sum(close_numeric(updates.get(key), label["after_values"][key]) for key in selected) / len(selected) if selected else None, "human_notes_preservation": "Structurally preserved by numeric-only patch application; not an open-ended editing result."}


def score(prepared: Path, responses_file: Path, out: Path) -> None:
    public, evaluator, protocol = load_prepared(prepared)
    raw = json.loads(responses_file.read_text())
    if isinstance(raw, dict) and "cases" in raw:
        raw = raw["cases"]
    if isinstance(raw, list):
        responses = {item["case_id"]: item for item in raw}
        if len(responses) != len(raw):
            raise ValueError("Duplicate case response")
    elif isinstance(raw, dict):
        responses = raw
    else:
        raise ValueError("Responses must be case-keyed object or list")
    known = {case["case_id"] for case in public["cases"]}
    if set(responses) - known:
        raise ValueError("Unknown case responses")
    rows = []
    all_pred, all_gold = set(), set()
    for case in public["cases"]:
        key, label = case["case_id"], evaluator["cases"][case["case_id"]]
        record = responses.get(key)
        row = {"case_id": key, "domain": case["domain"], "status": "invalid_or_missing", "schema_errors": []}
        dependencies: dict[str, list[str]] = {claim: [] for claim in CLAIM_IDS}
        if record is None:
            row["schema_errors"].append("missing model response")
        else:
            try:
                record = normalize_response(record)
                result = normalize_response(record.get("response", record))
                supplied = result.get("dependencies")
                if not isinstance(supplied, dict):
                    raise ValueError("Missing dependencies object")
                if set(supplied) != set(CLAIM_IDS):
                    row["schema_errors"].append("Claim keys differ from C01-C12")
                for claim in CLAIM_IDS:
                    operands = supplied.get(claim, [])
                    if not isinstance(operands, list) or any(not isinstance(item, str) for item in operands):
                        row["schema_errors"].append(f"Invalid dependency list:{claim}")
                        continue
                    dependencies[claim] = sorted(set(operands))
                    if len(set(operands)) != len(operands) or any(item not in (*SOURCE_IDS, *CLAIM_IDS) or item == claim for item in operands):
                        row["schema_errors"].append(f"Unknown, self or duplicate dependencies:{claim}")
                if not row["schema_errors"]:
                    row["status"] = "valid"
                if "repair_response" in record:
                    row["repair"] = score_repair(record, label)
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                row["schema_errors"].append(str(exc))
        predicted = {(claim, operand) for claim, operands in dependencies.items() for operand in operands}
        expected = {(claim, operand) for claim, operands in label["dependencies"].items() for operand in operands}
        all_pred.update((key, *edge) for edge in predicted)
        all_gold.update((key, *edge) for edge in expected)
        selected = routed_claims(dependencies, label["changed_sources"])
        row.update({"dependencies": dependencies, "edges": prf(predicted, expected), "wrong_edges": sorted([list(edge) for edge in predicted - expected]), "missing_edges": sorted([list(edge) for edge in expected - predicted]), "routed_ids": sorted(selected), "exact_affected_ids": label["exact_affected_ids"], "changed_value_routing": prf(selected, set(label["exact_affected_ids"]))})
        rows.append(row)
    result = {"schema_version": 1, "prepared_protocol_sha256": digest(prepared / "protocol.json"), "responses_sha256": digest(responses_file), "case_count": len(rows), "valid_response_count": sum(row["status"] == "valid" for row in rows), "immediate_edges_micro": prf(all_pred, all_gold), "exact_graph_case_count": sum(row["edges"]["exact"] and row["status"] == "valid" for row in rows), "exact_changed_value_routing_case_count": sum(row["changed_value_routing"]["exact"] and row["status"] == "valid" for row in rows), "cases": rows, "limitations": [protocol["primary_scope"], protocol["routing_metric_limit"], "No provider or model success is implied by this scorer. Missing and invalid responses remain in the denominator. Numeric-only patching structurally preserves human notes; it does not test open-ended preservation."]}
    write_json(out, result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--out", type=Path, required=True)
    scoring = commands.add_parser("score")
    scoring.add_argument("--prepared", type=Path, required=True)
    scoring.add_argument("--responses", type=Path, required=True)
    scoring.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.out)
        print(json.dumps({"prepared": str(args.out), "cases": 18, "protocol_sha256": digest(args.out / "protocol.json")}))
    else:
        score(args.prepared, args.responses, args.out)
        print(json.dumps({"report": str(args.out), "sha256": digest(args.out)}))


if __name__ == "__main__":
    main()
