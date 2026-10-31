# Exhaustive four-case pilot

The pilot splits retained target-0 branch-0 into four cases, one for each action
of a selected common-source row. The parent exactly-one clauses imply coverage
and pairwise disjointness. All four actions, including both emitted bits, remain
represented. Row selection prefers the most frequent source observation among
retained residuals; this heuristic has no measured speedup guarantee. No trial
solver probing or recursive refinement is implemented yet.

Each child copies the exact parent clauses and appends one selector unit.
The manifest records the parent hash, row, all actions/literals, selected case,
and child hash. The prior source-split branch 1 is not covered by this pilot.
Four checked child refutations would refute only parent branch 0. No automatic
aggregation or graph-level impossibility claim is made.

SAT models are saved as model.json. Before replay, every CNF clause and the
selector map are checked. The decoded complete policy is independently replayed
against all residual/source obligations by verify.cpp. SAT for the finite CNF
alone remains insufficient. Failures are retained in routing-replay.json.

The GitHub pilot runs four cases with 20 minutes for each solve and up to a
further 20 minutes for each proof check. Inputs and results are retained as
artifacts. Timeouts remain UNKNOWN. The ordinary search/checkpoints are unchanged.

Regression tests independently query coverage and disjointness with a SAT solver
on a small routing instance, save/decode/replay all four SAT models, and reject
mutated models and selector maps. Existing tests run before each GitHub case.
