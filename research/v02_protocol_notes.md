# Prospective v0.2 protocol notes — 2026-10-14

Status: design only. No model calls or new research outcomes were produced for these notes. The public v0.1 package and its frozen data must remain immutable. A versioned v0.2 protocol, prompts, view generator, controller and scorer must be frozen before any v0.2 benchmark response is observed.

## What the prepared 18 cases can establish

The prepared pilot has 18 authored synthetic workspaces, six per budget/capacity/pricing domain, twelve numeric claims per workspace, four source facts and two separate human notes. Its task contract explicitly names bracket IDs for immediate operands. An independent reviewer found that a public-only bracket-ID parser recovers the complete dependency graph in all 18 cases. This result makes the parser a mandatory zero-model baseline, and makes the existing view an integration smoke test rather than a test of implicit dependency discovery. Paying for many repetitions of the same easy extraction would add little evidence.

Exact dependency reachability and exact value changes are different targets. The reviewer's true-graph calculation selects 9.17 claims on average while only 7.11 change numerically; the sets coincide in 2/18 cases. Ratios, floor operations, bottlenecks and Boolean thresholds can remain unchanged despite genuine dependence. Report these conservative extra selections separately from extraction errors.

The frozen extraction prompt correctly excludes after-update facts and evaluator DAGs. The optional repair prompt uses after-update facts and English task contracts. Both remain synthetic arithmetic tasks. Separate note blocks are structurally protected by the numeric-only patch interface; this does not test whether a language model preserves arbitrary human edits in prose.

## Recommended minimum next study

1. Use the original public view for route/integration acceptance and the zero-model parser baseline. A successful call establishes provider feasibility and schema handling, not research superiority. If all 18 original-view calls are run, publish their outcomes descriptively, including perfect or worse-than-parser results.
2. Before substantive model comparison, construct a separate prospective public view of the same 18 latent cases. Preserve numeric facts, targets and evaluator DAGs. Remove bracket IDs from derivation rules, refer to meaningful metric names and unambiguous aliases, and independently permute rule order and displayed claim order. Claim record IDs still identify the requested output schema. The view must not expose expressions, gold edges, after-values or gold impact sets.
3. Have an independent reviewer check that every harder-view sentence still unambiguously specifies the same computation. Freeze the reviewed view and all controller choices before calls. Do not revise wording after seeing a model miss and then count the same cases as held out. Any debugging revision starts a separately named exploratory cohort.
4. Treat these as three shared templates with six numeric variants each, not 18 independently sampled business workflows. A harder wording view changes the measurement; it does not turn synthetic arithmetic into customer evidence or establish a new method.

The harder view is proposed, not implemented by these notes. If only the existing prepared view is available, stop at the accurately labeled integration pilot rather than publish it as implicit-dependency research.

## Questions and arms to freeze

RQ1: How accurately does a configured model extract immediate dependencies from the public task contract?

- P0: deterministic bracket-ID parser on the original view; on the harder view, use a declared public-name/alias matcher with no evaluator access. Preserve the original perfect-parser result as a dataset-difficulty warning.
- P1: the configured model with the existing schema-constrained extraction instruction. Change only the public workspace payload for the harder view. One request per case is the minimum pilot; a prespecified second independent repeat is optional but adds runs, not workspaces.
- P2, only if feasible within the declared cost cap: LEDGER-inspired counterfactual pairwise checking on a fixed public-only shortlist. Charge shortlist construction and every pair check. Label this an adaptation; do not claim reproduction of the complete published system. Compare cost/accuracy with P1, not just with an intentionally weak retrieval baseline.

RQ2: Given observed dependencies, how do selection and numerical refresh behave at equal selected-claim budgets?

Use a fixed budget of six distinct claims per workspace. Freeze each selector without gold impact labels:

- S1: observed-graph closure priority, then a deterministic public-ID fill if fewer than six claims are reached.
- S2: changed-source/name lexical ranking, top six, with public-ID tie breaking.
- S3: uniform six-claim sampling with a recorded seed independent of evaluator labels.
- S4: three claims from the same declared public ranking, then three uniformly selected from the remaining pool. This tests the opportunity cost of random inspection. It is an existing hybrid policy, not a new audit theorem.
- F: full refresh of all twelve claims, the practical correctness/cost reference.

All S arms receive the same current facts, old artifact text and English task contract, use the same model, response cap and numeric instruction, and request exactly six values in one call. F requests all twelve in one call with the same source/context payload and cap. Each arm's message differs only in its selected IDs. Preserve actual billed input/output tokens and latency; equal selected counts or call counts do not imply equal model cost. Charge P1's extraction once to every graph-dependent pipeline that needs it. Report both amortized reuse and first-update costs if relevant, without silently treating construction as free.

For this small cohort, P1 plus four S arms plus F is at most 108 successful benchmark calls for one model and one repeat. The original-view integration calls and health checks are separate. An implementation may run a smaller explicitly declared subset, but must not present absent arms or planned calls as executed. Specify the monetary/token ceiling from the real configured route before dispatch; the number above is not authorization to exceed a budget.

The twelve-claim scale may make full refresh cheaper and more accurate. Preserve that result. A favorable selection result here would justify a larger, independently sourced study, not a competitive-method claim by itself.

## Prompt and execution discipline

Retain the exact extraction and repair message builders in the frozen artifact, including the system instructions, user payloads, requested token cap and provider-visible model identifier. Record their hashes before requests. Do not include hidden expression DAGs or exact changed-value IDs in any prompt.

A controller must compute and freeze `selected_ids` from its declared public selector, then hash `{case_id, arm, source_snapshot, artifact_snapshot, observed_graph, selected_ids, prompt}` before the repair call. The current generic `score_repair` API accepts caller-provided selections; it alone does not establish that a declared policy selected them. The v0.2 scorer must reject a response if its arm/selection/prompt binding differs from the controller record. Gold-selected IDs are permitted only in a separately labeled oracle diagnostic, never in the proposed method arm.

Randomize or rotate arm request order using a prespecified seed, so that a route outage or provider change does not systematically affect the last arm. Do not feed another arm's response into the next request. Use fresh request contexts. Fix the sampling settings if supported; if immutable model snapshots or seed control are unavailable, disclose that limitation rather than claim deterministic model replay.

The refresher must derive selected values from current facts and the contract, rather than trust old upstream artifacts. This is a deliberately bounded numerical refresh interface. Do not infer that a production file, external API action, or live workspace was repaired from returned JSON alone.

## Scoring and estimands

Freeze scoring code and tolerance before calls. Reuse exact rational evaluator targets; the existing numeric acceptance tolerance is `max(0.0001, abs(target)*0.000001)`. Count Boolean values, NaN, infinity, absent values, extra update IDs and invalid schemas as failures under a declared rule. Retain failed/missing requests in the intent-to-evaluate denominator; separately report conditional-on-completion accuracy.

- Extraction: immediate-edge precision/recall/F1, exact graph by workspace, schema validity, missing and wrong edge lists. Do not score only transitive closure, which can hide wrong immediate graphs.
- Selection: actual value-change recall, unnecessary selected claims, selected count, and exact affected-set match. Do not classify mathematically unchanged descendants as graph-extraction mistakes.
- Refresh: correctness among selected claims, stale unselected claims, wrong selected updates, and final all-current workspace frequency after applying only the declared patch keys.
- Cost: provider calls including retries, billed input/output tokens, monetary usage when recorded, and end-to-end latency including extraction, discovery and fallback. Distinguish parallel wall time from summed provider latency.
- Preservation: report only structural retention of the two protected notes. A later open-ended document-editing experiment is required for semantic human-edit preservation.

Use paired per-workspace arm differences and show all 18 case rows. Report domain/template-level summaries and descriptive variability. This small three-template cohort does not justify a population success-rate claim, a general language-model ranking or a claim of operational ROI. Repeated calls do not increase the independent workspace count. If intervals are shown, identify their sampling unit and their severe three-template limitation.

## Auditing and theory boundary

The existing exact finite-population audit is known methodology: cite Anthony/Nobari arXiv2607.21480 and Hu et al., Mathematics14(18)3427. No new statistical theorem is proposed.

A model's numerical answer or semantic verdict is fallible; treating it as a perfect audit label does not inherit v0.1's confidence guarantee. A controlled oracle-label condition can isolate routing, but its gold labels must be charged and explicitly identified as evaluator feedback. Model-label conditions need empirical false-negative measurements or a separately justified noise model. For twelve claims, a strict zero-stale guarantee under arbitrary defect placement typically demands near-census inspection; do not hide the cost by selecting a permissive residual tolerance after seeing results.

For this minimum study, keep statistical release certification out of the primary model comparison. It can remain a separately labeled oracle-label diagnostic. Evaluate whether the model actually refreshed the claims correctly before attempting a stronger selective-release claim.

## Route recovery and failure contingency

The recorded v0.1 preflight has two unsuccessful smoke attempts, with a retained BYOK-provider HTTP502 diagnostic and zero successful benchmark calls. HTTP502 is an infrastructure outcome, not a model reasoning failure. Preserve these records and version them separately from v0.2 outcomes.

The release owner should recheck the current effective configured route without exposing secrets. Require recorded BYOK billing/source metadata for successful actual calls, as the repository instructions require. Preserve the configured model/provider. Do not silently switch to platform credentials or a different model because the preferred endpoint fails.

After a concrete route repair, permit a bounded health check on a constant nonsensitive prompt before the experiment. Predetermine one retry for a retryable transport failure, the timeout, and any backoff; retain request IDs, status codes, timestamps and attempt counts. Do not spin through repeated provider calls or count a failed response as a completed case. If the route remains unavailable, leave the model study unexecuted and finish offline protocol/controller checks; no synthetic or oracle response may stand in for a model result.

If a different already configured BYOK route is explicitly selected by the user, freeze its identity as a separate condition before dispatch. Keep model conditions separate. Partial outages require paired-completion reporting as a secondary view, while primary intent-to-evaluate rows retain every scheduled arm. No arm may be rerun until favorable and then substituted silently.

## Publication gate for a stronger claim

The existing v0.1 is a bounded reproducible composition study. Do not rewrite that released evidence. A subsequent v0.2 report must say exactly which original/harder view and arms actually ran, provide raw requests/responses and usage metadata, and disclose the parser ceiling, shared templates and oracle/model distinctions.

A competitive new-method paper still requires a concrete method contribution and a larger evaluation with natural dependency omissions, independently prepared tasks, strong complete-system or faithful adapted baselines, genuinely generated repairs, and measured total costs. The present minimum study can expose failure modes and guide that work; passing it is not sufficient grounds to claim state-of-the-art autonomous workspace repair.
