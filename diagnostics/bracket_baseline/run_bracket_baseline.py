#!/usr/bin/env python3
"""Public bracket-ID baseline diagnostic for the immutable prepared 18-case pilot.

Extraction runs in a separate process with only public/inputs.json as data input.
Predictions are persisted before the unchanged frozen scorer sees any gold.
This is explicit schema extraction, not implicit semantic provenance inference.
No models, provider calls, formula inference or repair calls are used.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent
BRACKET_ID = re.compile(r"\[([FC][0-9]{1,2})\]")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError("This diagnostic may write only within its own new work directory")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with resolved.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def extract(public_file: Path, out: Path, parse_out: Path) -> None:
    """Public-only schema extraction. No evaluator path or data parameter."""
    def reject_gold_open(event: str, args: tuple[Any, ...]) -> None:
        if event == "open" and args and isinstance(args[0], (str, bytes)):
            filename = args[0].decode() if isinstance(args[0], bytes) else args[0]
            if Path(filename).name == "gold.json":
                raise PermissionError("Gold access is forbidden in extraction process")
    sys.addaudithook(reject_gold_open)
    public = json.loads(public_file.read_text())
    predictions, parses = [], []
    for case in public["cases"]:
        claim_ids = {artifact["id"] for artifact in case["artifacts"]}
        source_ids = {source["id"] for source in case["before_sources"]}
        allowed = claim_ids | source_ids
        dependencies: dict[str, list[str]] = {}
        rule_parses = []
        for rule in case["task_contract"]["rules"]:
            mentions = BRACKET_ID.findall(rule)
            if not mentions or mentions[0] not in claim_ids:
                raise ValueError(f"Rule lacks an explicit target claim ID first: {case['case_id']}")
            target = mentions[0]
            if target in dependencies:
                raise ValueError(f"Duplicate target rule: {case['case_id']} {target}")
            if any(operand not in allowed for operand in mentions):
                raise ValueError("Unknown bracket-ID token")
            operands = sorted(set(mentions[1:]) - {target})
            dependencies[target] = operands
            rule_parses.append({"target": target, "mentioned_ids_in_order": mentions,
                                "deduplicated_immediate_operands": operands})
        if set(dependencies) != claim_ids:
            raise ValueError("Explicit rule targets do not cover the public artifact IDs")
        predictions.append({"case_id": case["case_id"], "method": "public_bracket_id_extraction",
                            "response": {"dependencies": dependencies}, "model_calls": 0})
        parses.append({"case_id": case["case_id"], "domain": case["domain"],
                       "rules": rule_parses, "rules_sha256": hashlib.sha256(json.dumps(case["task_contract"]["rules"], sort_keys=True).encode()).hexdigest()})
    write_json(out, {"cases": predictions, "method": "public_bracket_id_extraction", "model_calls": 0,
                     "input_scope": "public/inputs.json only; target ID first and direct operand IDs explicitly bracketed"})
    write_json(parse_out, {"public_input_sha256": sha(public_file), "cases": parses,
                           "unique_rule_contracts": len({p["rules_sha256"] for p in parses}),
                           "extractor_gold_open_guard": "Python audit hook rejects any file named gold.json in extraction process",
                           "formula_operators_parsed": False, "model_calls": 0})


def rational(pair: list[int]) -> Fraction:
    return Fraction(pair[0], pair[1])


def ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def diagnose(prepared: Path, predictions: Path, parse_report: Path, score: Path, out: Path) -> None:
    """Post-hoc evaluation only, after public predictions were written."""
    public = json.loads((prepared / "public/inputs.json").read_text())
    gold = json.loads((prepared / "evaluator/gold.json").read_text())
    scored = json.loads(score.read_text())
    parsed = json.loads(parse_report.read_text())
    scores_by_id = {row["case_id"]: row for row in scored["cases"]}
    rows = []
    for case in public["cases"]:
        label = gold["cases"][case["case_id"]]
        row = scores_by_id[case["case_id"]]
        before = {key: rational(pair) for key, pair in label["before_rationals"].items()}
        after = {key: rational(pair) for key, pair in label["after_rationals"].items()}
        affected = {key for key in before if before[key] != after[key]}
        if affected != set(label["exact_affected_ids"]):
            raise AssertionError("Published affected IDs disagree with exact rational value delta")
        before_sources = {x["id"]: x["value"] for x in case["before_sources"]}
        after_sources = {x["id"]: x["value"] for x in case["after_sources"]}
        changed_sources = sorted(key for key in before_sources if before_sources[key] != after_sources[key])
        if changed_sources != sorted(label["changed_sources"]):
            raise AssertionError("Public source updates and scorer labels disagree")
        routed = set(row["routed_ids"])
        unneeded = sorted(routed - affected)
        omitted = sorted(affected - routed)
        rows.append({"case_id": case["case_id"], "domain": case["domain"],
                     "changed_sources_from_public_values": changed_sources,
                     "immediate_edges_exact": row["edges"]["exact"],
                     "routed_ids": sorted(routed), "routed_count": len(routed),
                     "exact_rational_changed_target_ids": sorted(affected), "changed_target_count": len(affected),
                     "over_selected_ids": unneeded, "over_selected_count": len(unneeded),
                     "omitted_changed_ids": omitted, "omitted_changed_count": len(omitted),
                     "routing_precision": ratio(len(routed & affected), len(routed)),
                     "routing_recall": ratio(len(routed & affected), len(affected)),
                     "over_selection_fraction_of_routed": ratio(len(unneeded), len(routed)),
                     "unchanged_routed_values_exact": {key: {"before": str(before[key]), "after": str(after[key])} for key in unneeded}})
    routed_n = sum(row["routed_count"] for row in rows)
    changed_n = sum(row["changed_target_count"] for row in rows)
    over_n = sum(row["over_selected_count"] for row in rows)
    omit_n = sum(row["omitted_changed_count"] for row in rows)
    domain_rows = {}
    for domain in sorted({row["domain"] for row in rows}):
        subset = [row for row in rows if row["domain"] == domain]
        nr = sum(row["routed_count"] for row in subset)
        na = sum(row["changed_target_count"] for row in subset)
        no = sum(row["over_selected_count"] for row in subset)
        nm = sum(row["omitted_changed_count"] for row in subset)
        domain_rows[domain] = {"cases": len(subset), "routed_claim_instances": nr,
                               "rational_changed_claim_instances": na, "over_selected_claim_instances": no,
                               "omitted_changed_claim_instances": nm,
                               "routing_precision": ratio(nr - no, nr), "routing_recall": ratio(na - nm, na),
                               "exact_routing_cases": sum(not r["over_selected_ids"] and not r["omitted_changed_ids"] for r in subset)}
    result = {
        "diagnostic": "Explicit public bracket-ID schema extraction on the existing prepared pilot",
        "input_public_sha256": sha(prepared / "public/inputs.json"),
        "input_gold_sha256_used_post_prediction_only": sha(prepared / "evaluator/gold.json"),
        "predictions_sha256": sha(predictions), "scorer_report_sha256": sha(score),
        "case_count": len(rows), "unique_rule_contracts": parsed["unique_rule_contracts"],
        "claim_instances": sum(len(case["artifacts"]) for case in public["cases"]),
        "valid_schema_cases": scored["valid_response_count"], "exact_immediate_graph_cases": scored["exact_graph_case_count"],
        "immediate_edges_micro": scored["immediate_edges_micro"],
        "exact_value_delta_routing_cases": scored["exact_changed_value_routing_case_count"],
        "routed_claim_instances": routed_n, "exact_rational_changed_claim_instances": changed_n,
        "over_selected_claim_instances": over_n, "omitted_changed_claim_instances": omit_n,
        "routing_micro_precision": ratio(routed_n - over_n, routed_n),
        "routing_micro_recall": ratio(changed_n - omit_n, changed_n),
        "over_selection_fraction_of_routed": ratio(over_n, routed_n),
        "cases_with_over_selection": sum(bool(row["over_selected_ids"]) for row in rows),
        "domain_summary": domain_rows, "cases": rows, "model_calls": 0,
        "limitations": [
            "Existing prepared 18 cases reused; only three distinct rule contracts. This adds no independent benchmark or model evidence.",
            "Each public rule names its target claim first and directly brackets every operand ID. Extraction reduces to schema tokenization.",
            "No implicit, omitted, ambiguous or conflicting natural-language provenance is tested by this baseline.",
            "The baseline does not parse arithmetic, compute repaired numeric values or make provider calls.",
            "Immediate-edge exactness does not imply exact change routing: algebraic cancellation, unchanged threshold flags and dominated bottleneck branches can be reached without changing value.",
            "Exact rational before/after targets are read only in the post-hoc diagnostic, after separate-process public predictions are persisted.",
            "Frozen v0.1 artifacts and the existing scorer are read only; no published file is modified.",
        ],
    }
    write_json(out, result)


def run_stage(args: list[str]) -> None:
    subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), *args], check=True)


def run(prepared: Path, scorer: Path) -> None:
    for name in ("primary", "replay"):
        target = ROOT / name
        if target.exists():
            raise FileExistsError("Diagnostic runs are immutable; use a new diagnostic directory/version")
        target.mkdir()
        run_stage(["extract", "--public", str(prepared / "public/inputs.json"),
                   "--out", str(target / "predictions.json"), "--parse-out", str(target / "parse_report.json")])
        # Unmodified current scorer is launched only after predictions exist.
        subprocess.run([sys.executable, "-B", str(scorer), "score", "--prepared", str(prepared),
                        "--responses", str(target / "predictions.json"), "--out", str(target / "scorer_report.json")], check=True)
        run_stage(["diagnose", "--prepared", str(prepared), "--predictions", str(target / "predictions.json"),
                   "--parse-report", str(target / "parse_report.json"), "--score", str(target / "scorer_report.json"),
                   "--out", str(target / "diagnostic.json")])
    filenames = ["predictions.json", "parse_report.json", "scorer_report.json", "diagnostic.json"]
    replay = {}
    for filename in filenames:
        first, second = ROOT / "primary" / filename, ROOT / "replay" / filename
        same = first.read_bytes() == second.read_bytes()
        if not same:
            raise AssertionError(f"Deterministic diagnostic replay mismatch: {filename}")
        replay[filename] = {"primary_sha256": sha(first), "replay_sha256": sha(second), "byte_identical": same}
    report = json.loads((ROOT / "primary/diagnostic.json").read_text())
    summary = ["# Explicit bracket-ID extraction diagnostic", "",
               "This diagnostic reuses the immutable prepared pilot. It adds no new independent cases, model calls or method claim.", "",
               f"- Cases: {report['case_count']}; distinct rule contracts: {report['unique_rule_contracts']}; claim instances: {report['claim_instances']}.",
               f"- Exact immediate dependency graphs: {report['exact_immediate_graph_cases']}/{report['case_count']}; valid schemas: {report['valid_schema_cases']}/{report['case_count']}.",
               f"- Exact value-change routing: {report['exact_value_delta_routing_cases']}/{report['case_count']} cases.",
               f"- Reached claims: {report['routed_claim_instances']}; exactly changed rational targets: {report['exact_rational_changed_claim_instances']}.",
               f"- Unchanged claims conservatively selected: {report['over_selected_claim_instances']}; changed claims omitted: {report['omitted_changed_claim_instances']}.",
               f"- Routing micro precision: {report['routing_micro_precision']:.6f}; recall: {report['routing_micro_recall']:.6f}.", "",
               "The public rule schema already exposes the dependency graph: the first bracketed claim ID identifies the output, and subsequent bracketed IDs identify its direct operands. The baseline tokenizes those IDs and removes duplicate operands; it does not infer unrecorded semantic dependencies. Gold is unavailable to the separate extraction process, which rejects attempts to open gold.json. Predictions are saved before the unchanged scorer is called.", "",
               "Correct immediate edges give conservative reachability, not exact numeric impact. Unchanged ratios, threshold flags and saturated capacity branches can remain reachable after a source update. The post-hoc diagnostic independently verifies all affected IDs against exact Fraction before/after targets rather than rounded decimal displays.", "",
               "An explicit-ID baseline should accompany any model extraction score on these contracts. Success on this schema cannot establish robustness to implicit, missing or ambiguous provenance. Both runs produced byte-identical predictions, parsing reports, scorer reports and diagnostics. Frozen source files were read only.", ""]
    report_path = ROOT / "REPORT.md"
    with report_path.open("x", encoding="utf-8") as f:
        f.write("\n".join(summary))
    manifest = {"script_sha256": sha(Path(__file__)), "scorer_sha256": sha(scorer),
                "prepared_protocol_sha256": sha(prepared / "protocol.json"),
                "public_inputs_sha256": sha(prepared / "public/inputs.json"),
                "gold_sha256": sha(prepared / "evaluator/gold.json"), "report_sha256": sha(report_path),
                "replay": replay, "model_calls": 0, "frozen_files_modified": False}
    write_json(ROOT / "audit_manifest.json", manifest)
    print(json.dumps({key: report[key] for key in ("case_count", "unique_rule_contracts", "exact_immediate_graph_cases", "exact_value_delta_routing_cases", "routed_claim_instances", "exact_rational_changed_claim_instances", "over_selected_claim_instances", "omitted_changed_claim_instances", "routing_micro_precision", "routing_micro_recall")}, indent=2))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="stage", required=True)
    x = sub.add_parser("extract")
    x.add_argument("--public", type=Path, required=True)
    x.add_argument("--out", type=Path, required=True)
    x.add_argument("--parse-out", type=Path, required=True)
    d = sub.add_parser("diagnose")
    for arg in ("prepared", "predictions", "parse-report", "score", "out"):
        d.add_argument(f"--{arg}", type=Path, required=True)
    r = sub.add_parser("run")
    r.add_argument("--prepared", type=Path, required=True)
    r.add_argument("--scorer", type=Path, required=True)
    args = p.parse_args()
    if args.stage == "extract":
        extract(args.public, args.out, args.parse_out)
    elif args.stage == "diagnose":
        diagnose(args.prepared, args.predictions, args.parse_report, args.score, args.out)
    else:
        run(args.prepared.resolve(), args.scorer.resolve())


if __name__ == "__main__":
    main()
