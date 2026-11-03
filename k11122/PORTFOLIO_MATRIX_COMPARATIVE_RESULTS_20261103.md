# K11122 — four-case portfolio robustness: verified independent implementations

**Date: 3 November 2026. Mathematical classification: UNKNOWN.**
One mutable packet bit on \(K_{1,1,1,2,2}\) is not yet classified for
either destination orbit; the established state bounds remain 2–3 states.
Neither of the two completed matrix experiments produced a complete
finite-suite candidate or an independently checked UNSAT proof.

This report reconciles **two overlapping but different bounded
four-case portfolio experiments**. They share the same mathematical
problem, strict frozen mask families and SAT input semantics. They
do **not** constitute statistically independent repetitions and
should not be treated as such. Their active search budgets and
continuation witness-selection heuristics are different.

## Audited provenance

| | Longer first-witness experiment | Shorter hybrid experiment |
| --- | --- | --- |
| Tested source commit | \`ea7c5a4bd8e26b630f4f2b4faecfea7a59c85129\` | \`f35eaf69f2cd7082a00265f345433a9f2971e9c3\` |
| Hosted run | [41624096550](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41624096550) | [41624732089](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41624732089) |
| Full artifact | [13224879222](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41624096550/artifacts/13224879222) | [13225168494](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41624732089/artifacts/13225168494) |
| SHA-256 of downloaded ZIP | \`2cd8085a86db91b473975e6ac04602ffbcae6b0279057cc33a383edd5c244400\` | \`04df2d0582da2f7f316f0a880079f264c296175645ba7e09570b4df2ab6d76a9\` |
| Byte size of ZIP | 145,222,754 | 86,495,523 |
| CRC-verified ZIP members | 11,116 | 6,524 |
| Externally SHA-256 checked files | **11,115 / 11,115** | **6,523 / 6,523** |
| Passing full regression suite | **97 tests** | **98 tests** |
| Source active search (per backend/case) | 7 s | 6 s |
| Continuation active search (per arm/case) | 9 s | 8 s |
| Source witness selection | Hybrid, period 8 | Hybrid, period 8 |
| Continuation witness selection | **First-witness** | **Hybrid, period 8** |
| Historical-best scoring interval | Every 8th model, plus first | Every 8th model, plus first |
| Source backends | CaDiCaL195 / MapleChrono | CaDiCaL195 / MapleChrono |
| Continuation backend | CaDiCaL195 | CaDiCaL195 |
| Seed | 20261103 | 20261103 |
| Scientific verdict | UNKNOWN in all 4 cells | UNKNOWN in all 4 cells |

I obtained both exact ZIPs through the connected GitHub application
and independently computed their SHA-256 checksums, streamed and
validated every SHA256SUMS-indexed ZIP member and required that no
unlisted entry remained except the checksum index itself.
The first experiment's earlier report correctly noted that its
*own* external download attempt was rejected by ingress limits.
The external check was subsequently completed here, so both
archives now have independently verified integrity.

Both hosted runs compiled the original unchanged C++ exhaustive
full-graph checker and strict C++ rank-free failing-walk scanner;
they independently audited every initial source formula,
deduplicated portfolio and all terminal CNFs, including every
necessary source-connected witnessed walk, global selector row
and first-hop branch restriction. The separate historical-best
policy scorer was also cross-checked by independent Python
literal-walk replay.

## Exactly four matched problem cells

These are the two distinct destination orbits crossed with the
two exhaustive physical-first-hop branches:

| Cell | Target orbit | Branch | Frozen failure residuals |
| --- | --- | ---: | ---: |
| t0-b0 | Singleton target 0 | 0 | 2,701 |
| t0-b1 | Singleton target 0 | 1 | 2,701 |
| t3-b0 | Doubleton target 3 | 0 | 2,181 |
| t3-b1 | Doubleton target 3 | 1 | 2,181 |

All source backends genuinely diverged in each cell:
CaDiCaL195 vs MapleChrono first differed in complete routing-policy
SHA-256 at **model 2 for t0-b0 and t3-b0**, and **model 1 for
t0-b1 and t3-b1**, in both experiments. Backend names or
different random seeds alone were *not* accepted as evidence
of distinct trajectories.

Within each cell, every pooled witness is a sound necessary
negative-selector clause for the **same** source-injection/local
forwarding one-bit routing model. Source targets, branches, residual
sets and selector numbering are required to match exactly.
Neither cross-branch branch assertions, rank variables, arbitrary
arrival obligations, extra packet memory, unverified solver
conflict clauses nor backend conclusions were pooled. The portfolio
constructor audited all source CNFs **before creating the
portfolio**, independently rechecked every witness, deduplicated
identical clauses and rebuilt a fresh CNF with the same legal
base and branch assertion.

## Result 1: seven-second sources, nine-second first-witness continuations

Lower is better: each value is the number of distinct frozen
residual masks on which at least one target-connected source
fails. These are **best periodically sampled historical raw
SAT policies**, not necessarily terminal CNF satisfying
assignments or verified graph policies.

| Cell | CaDiCaL-only | MapleChrono-only | Portfolio | Portfolio vs best single |
| --- | ---: | ---: | ---: | ---: |
| t0-b0 | 651 | 631 | **531** | **100 fewer** |
| t0-b1 | **534** | 709 | 629 | **95 more** |
| t3-b0 | 440 | 491 | **427** | **13 fewer** |
| t3-b1 | 400 | 447 | **339** | **61 fewer** |

Pooling improves the best sampled score in **3/4** cells.
Each of the twelve continuations used the same nine-second
active search budget and "first" witness sampler within
this experiment. No finite-suite-passing candidate emerged.

| Cell | Portfolio unique certified clauses | Exact duplicate clauses removed |
| --- | ---: | ---: |
| t0-b0 | 82,281 | 1,719 |
| t0-b1 | 77,267 | 1,453 |
| t3-b0 | 73,722 | 1,638 |
| t3-b1 | 72,813 | 1,299 |

Input source-generation compute, source certificate rechecking,
portfolio construction, independent source import and final audits
are additional overhead and not counted as free. Pooled continuation
preparation costs ranged from **3.718 to 4.438 seconds** before
active nine-second search.

## Result 2: six-second sources, eight-second hybrid continuations

This separately implemented bounded workflow uses the same
four cells, canonical normalized one-bit policy domain,
diversified source backends, seed, frozen suites and independent
proof obligations. Continuations use **hybrid period 8** rather
than the other workflow's "first" heuristic, and their
active budgets are **eight** seconds rather than nine.

| Cell | CaDiCaL-only | MapleChrono-only | Portfolio | Portfolio vs best single |
| --- | ---: | ---: | ---: | ---: |
| t0-b0 | **441** | 472 | 502 | **61 more** |
| t0-b1 | 455 | 487 | **369** | **86 fewer** |
| t3-b0 | 297 | 280 | **273** | **7 fewer** |
| t3-b1 | **250** | 288 | 278 | **28 more** |

Pooling improves the best sampled score in **2/4** cells,
and regresses in two. The raw model counts, respectively
CaDiCaL/Maple/portfolio, were t0-b0 (354/354/345),
t0-b1 (350/358/355), t3-b0 (328/338/326),
and t3-b1 (326/340/333). The number of inherited
unique necessary portfolio clauses was:

| Cell | Unique necessary portfolio clauses | Exact duplicates removed |
| --- | ---: | ---: |
| t0-b0 | 49,824 | 960 |
| t0-b1 | 49,096 | 824 |
| t3-b0 | 46,599 | 941 |
| t3-b1 | 43,292 | 580 |

The total output of the shorter source runs is smaller,
but its four pooled constructions still passed independent
witness replay and entire CNF reconstruction. Portfolio
construction and verification took 5.757–6.820 seconds;
each pooled continuation then spent an additional
4.223–4.986 seconds on independent CNF import/initialization,
before its eight-second active search budget.

All **12 terminal continuations** remained UNKNOWN and
produced **zero** finite-suite-passing candidates.

## Interpretation: reliable clause soundness, conditional heuristic gain

These two controlled configurations prove a useful **engineering
result**: checked necessary certificates can be pooled for all
four graph/target/branch combinations, with little exact overlap
between genuinely divergent SAT backend trajectories, and the
union can be imported without changing the routing-model search
space or trusting the original solver.

They do **not** establish that pooling accelerates mathematical
convergence. Within-case quality gains are mixed, and the sign
of the benefit changes between configurations. Crucially, the
two completed experiments change **multiple dimensions**:
source and continuation active budgets, and continuation
witness-selection heuristic ("first" versus "hybrid").
Consequently **neither the budget difference nor the witness
selection can be credited as the cause** without a future
factorial experiment holding the other variable fixed.

The two configurations share the same deterministic seed and
backends. They must **not** be treated as independent random
samples in significance tests. The best raw historical score
is measured only on model 1 and every eighth model; an
unsampled intermediate assignment may be better, and the
historical best may violate the terminal strengthened CNF.
No proof follows from lower failure counts, more clauses,
higher solver throughput or checked UNKNOWN.

## Next targeted research move

Rather than increasing unchanged SAT timeouts, test **selective
necessary-clause pooling** under matched input sources:
canonical subset/subsumption removal, shorter-clause prioritization,
and controlled failure-mask diversity. Use the **same already-audited
source certificates** to compare all-clause pooling with selective
pooling, keeping the source searches, solver backend, phase policy,
routing model, active budget and witness-selection heuristic fixed.
Include all four branches, especially t0-b1 where gains have
reversed, and demand independent final-CNF/witness audits and
actual policy-hash divergence before attributing effects.

A genuine **positive** requires a complete legal policy for **both
destination orbits** independently verified across all 524,288
residual masks and every connected source. A genuine **negative**
requires a complete sound reduction and independently checked UNSAT
proofs of **both exhaustive first-hop branches** for at least one
orbit. Neither was obtained here.

The first workflow, exact source and data are in
[PORTFOLIO_MATRIX.md](PORTFOLIO_MATRIX.md),
[PORTFOLIO_MATRIX_RESULTS_20261103.md](PORTFOLIO_MATRIX_RESULTS_20261103.md)
and its complete linked ZIP. The separately preserved
shorter-budget hybrid workflow and runnable script are in
[PORTFOLIO_MATRIX_HYBRID.md](PORTFOLIO_MATRIX_HYBRID.md)
and the second linked ZIP.
No recurring automation or unbounded external compute was started.
