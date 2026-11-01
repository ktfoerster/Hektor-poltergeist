# K11122 rank-free lasso pilot — verified 1 November 2026

Scientific classification: **UNKNOWN** for target 0 and target 3.
This pilot tests only target 0, physical-first-hop branch 0.

## Exact run

- Hosted run: https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41293198280
- Evidence artifact: https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41293198280/artifacts/13078265845
- Artifact ZIP SHA-256: `abcf16e57c1cb096483b627c386e590adba0c036e2793d3656b2c156b3608ce5`
- Code tested: `56e7956c0f399cfc0ac0dc758deb0477fdbe84ae`
- Frozen strict target-0 union: **2701 residual masks**, original two branches 2648 and 2632, intersection 2579. Unconditional masks merged, no branch assumptions imported.
- Existing rank CNF on identical masks, branch 0: **1,277,670 variables**, **4,871,885 clauses**, exported in **7.59 wall seconds** (30,276 KiB peak for exporter). Rank CNF was *not* solved in this comparison; do not present as a solver speedup.
- New rank-free CNF, same masks and branch: **4,736 global selector variables**, **72,603 clauses** at checkpoint, including **61,248 independently replayed reachable-failure witness clauses**; exact final DIMACS SHA-256 `34792b5e850afc31b586604756a2ce3d4e60674b9b53eafff8e00eafb6cf1ba6`.
- Search: **75-second budget**, **638 raw SAT assignments**, **0 complete frozen-suite scans**, **0 finite-suite candidates**, **UNKNOWN**. It added at most 96 necessary witness clauses per raw model and never interpreted that model as satisfying the complete frozen suite.
- Timing: roughly **61.49 s** in Python finite-suite walks, **2.79 s** in SAT solver slices. Measured external learner wall time **77.55 s**, peak **90,568 KiB**. Construction alone was **0.041 s**, but these timings measure different work and do not establish any solver speedup.
- No independent C++ exhaustive replay was executed for a full candidate, because no candidate survived the entire frozen suite. It was rebuilt and its SHA-256 preserved.
- Both the original tests and new semantic/differential/corruption tests passed: **38 tests**.
- The exported lazy formula was independently reconstructed and fully re-audited: **CHECKED**, all **61,248** witness clauses, global selector map, branch clause, exactly-one clauses, and DIMACS byte content matched.
- No UNSAT refutation or graph-positive routing table has been obtained.

## Interpretation and next experiment

The smaller lazy CNF is a meaningful **representation change**, not yet a
demonstrated speedup: search time in this pilot is dominated by Python
walk generation and the policy has not passed even one entire frozen suite.
Before allocating longer solver budgets, optimize independent walk scanning
and reduce redundant equivalent witnesses; benchmark the optimized replay
against the unmodified independent C++ checker on small domains and selected
larger residuals. Retain all 61,248 audited clauses for a possible bounded
resume, preserving their hashes and exact code dependencies. The current
baseline makes it easy to distinguish a genuine improvement from rerunning
the same rank-based timeout.

Full classification still needs independent exhaustive replay for both
destination orbits for a positive, or independently audited CNF-to-routing
translation and checked refutation for both exhaustive branches of one orbit
for a negative. Test success is not a correctness proof.
