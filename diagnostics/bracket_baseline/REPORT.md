# Explicit bracket-ID extraction diagnostic

This diagnostic reuses the immutable prepared pilot. It adds no new independent cases, model calls or method claim.

- Cases: 18; distinct rule contracts: 3; claim instances: 216.
- Exact immediate dependency graphs: 18/18; valid schemas: 18/18.
- Exact value-change routing: 2/18 cases.
- Reached claims: 165; exactly changed rational targets: 128.
- Unchanged claims conservatively selected: 37; changed claims omitted: 0.
- Routing micro precision: 0.775758; recall: 1.000000.

The public rule schema already exposes the dependency graph: the first bracketed claim ID identifies the output, and subsequent bracketed IDs identify its direct operands. The baseline tokenizes those IDs and removes duplicate operands; it does not infer unrecorded semantic dependencies. Gold is unavailable to the separate extraction process, which rejects attempts to open gold.json. Predictions are saved before the unchanged scorer is called.

Correct immediate edges give conservative reachability, not exact numeric impact. Unchanged ratios, threshold flags and saturated capacity branches can remain reachable after a source update. The post-hoc diagnostic independently verifies all affected IDs against exact Fraction before/after targets rather than rounded decimal displays.

An explicit-ID baseline should accompany any model extraction score on these contracts. Success on this schema cannot establish robustness to implicit, missing or ambiguous provenance. Both runs produced byte-identical predictions, parsing reports, scorer reports and diagnostics. Frozen source files were read only.
