# K11122 shortest/diverse clause selection — independently checked pilot

Date: **3 November 2026**. Scientific classification: **UNKNOWN** for target 0
and target 3; all original first-hop branches remain unresolved. Established
bound remains 2–3 packet states. This is an engineering and finite-suite
heuristic experiment, not an impossibility proof or resilient routing policy.

## Exact source and artifacts

- Tested source commit: c0a37bfb8cb4a8de52bcb188df5ab600ba6ae88a
- GitHub Actions run: https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41547783660
- Downloadable evidence: https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41547783660/artifacts/13190005712
- Artifact ZIP SHA-256: 77cb306bad547dec23063a7ea018f71dff8a56eb60ce6bddb6868bb15560d0d4
- The 3,481 ZIP entries passed CRC validation. The 3,480 manifest-indexed
  files ALL passed SHA-256 checks; the remaining entry is SHA256SUMS itself.
  The manifest records paths prefixed with evidence/ (repository-working
  paths), while GitHub stores its archive contents relative to evidence/.
  Strip that prefix when comparing manifest paths to ZIP member names.
- Complete regression suite: **65 tests passed**, including semantic
  comparison with reference rank constraints, target-orbit differential
  C++/Python walks, deterministic shortest-source selection, duplicate and
  subset-clause checks, corruption, and crash-safe journal integration.
- The unchanged independent full-graph C++ verifier was rebuilt and hashed,
  but NOT invoked for a positive candidate: no finite-suite positive
  candidate emerged. No negative proof was produced.

## Fixed-policy clause quality (structural experiment, NOT solver runtime)

Two preserved complete *invalid* phase policies were independently replayed
on exactly the same strict merged residual families by both heuristics.
Every emitted lasso clause passed separate Python source-walk replay and
translation checking. Short-diverse chose the shortest failing connected
source per mask, removed locally redundant superset clauses and attempted
failure-mask diversity. The old first-witness output remained unchanged.

| Target / 19-edge residual family | First witness | Short-diverse |
| --- | ---: | ---: |
| Target 0, 2,701 residual masks: independent necessary clauses | 20 | 19 |
| Target 0, average selected clause literals | 7.50 | 6.53 |
| Target 0, average nearest selected-mask Hamming distance | 3.75 | 3.84 |
| Target 3, 2,181 residual masks: independent necessary clauses | 92 | 88 |
| Target 3, average selected clause literals | 6.32 | 5.24 |
| Target 3, average nearest selected-mask Hamming distance | 3.09 | 3.19 |

Minimum selected-mask pairwise Hamming distance was **1** under both
heuristics for both orbits. Thus diversity improvement here is *modest*,
not an increased minimum-separation guarantee.

## Equal-budget actual SAT experiment

Both cold trials used **target 0, branch 0**, the same exact 2,701 residuals,
CaDiCaL195 through python-sat==1.8.dev24, seed 20261103, unchanged global
selectors, the same C++ scanner executable, independently checked learned
clauses, a 96-new-clause cap per SAT model, and a **25-second** search budget.
Both end as UNKNOWN. The solver trajectories and CNFs differ because the
necessary-clause selection differs; neither represents a mathematical
restriction of the legal routing policy set.

| Measurement | First | Short-diverse |
| --- | ---: | ---: |
| Raw SAT assignments evaluated | 1,468 | 1,314 |
| Newly learned, independently checked necessary clauses | 140,928 | 126,048 |
| Mean literals per learned clause | 8.000 | 6.235 |
| Final CNF variables | 4,736 | 4,736 |
| Final CNF clauses | 152,283 | 137,403 |
| SAT solver time (s) | 5.695 | 5.755 |
| Replay/witness/checking time (s) | 9.559 | 10.807 |
| C++ subprocess time (s, within replay) | 3.968 | 5.939 |
| Peak reported RSS (KiB) | 105,208 | 88,708 |
| Full completed frozen-suite scans | 0 | 0 |
| Finite-suite candidates | 0 | 0 |

Mean learned clause length decreased by **about 22.1%** (8.000 to 6.235),
but candidate throughput fell by **about 10.5%** (1,468 to 1,314).
This is NOT a throughput improvement, and these bounded observations do
not establish better convergence or mathematical solvability.
The new heuristic scans every residual and connected source, increasing
C++ work per SAT assignment.

Exact first-mode CNF SHA-256:
24e43e2f5ae1aff849d16b6f62964b9ba35745c525f5d7110aeb1a7d3b3db4fd

Exact short-diverse CNF SHA-256:
91c15766d76918689ab5bb19d6f7ef6cb83719bc2cb60227fba6d45497f7ba7c

Both complete emitted CNFs passed independent byte-for-byte reconstruction,
including every necessary witness clause, exact one-hot global selector base
and disjoint first-hop branch assertion. End status UNKNOWN for both trials.

## Target-3 cross-orbit smoke

A separate bounded 12-second target 3, branch 0, short-diverse run used the
strict 2,181 residual union. It evaluated **630** raw SAT assignments,
independently checked **60,384** necessary clauses, and exported a
**6,240-variable, 76,507-clause** CNF. The independent audit passed.
CNF SHA-256:
c1f6e07deb18cc7caabbc7ac4dcdc2291c995fc8f3876d78668ce22d35d861f0

Status: UNKNOWN. No finite-suite candidate or certified UNSAT was obtained.

## Interpretation and next concrete experiment

The tradeoff is promising for SAT propagation but not yet for overall search
throughput. The next justified experiment would be a **deterministic hybrid**:
use fast first-witness batches by default and periodically request shorter,
more diverse batches, while retaining exact independent certificate auditing.
Compare at equal CPU budgets and record full-CNF solve conflicts/propagation
as well as short-clause distribution, not raw file size alone. Do not infer
impossibility from timeouts or raw UNSAT.

All code, test configuration, exact seed/backend, artifacts and mathematical
soundness argument are documented in CLAUSE_SELECTION.md. Source changes
require explicit, fully audited checkpoint migration. No recurring task or
duplicate hosted search was created.
