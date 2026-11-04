# K11122 — four-case selective clause-pooling pilot

**Date:** 4 November 2026. **Scientific classification: UNKNOWN for both destination orbits.** The one-bit (two-state) problem on (K_{1,1,1,2,2}) remains unresolved within the established 2–3-state bounds. No complete finite-suite candidate, independently verified whole-graph policy, or checked UNSAT certificate was produced.

## Reproducibility and external validation

- Tested implementation commit: `7d53bd1f9114cb961f97bebdab8ad95e062445e8`.
- Successful GitHub Actions run: https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41776143667
- Complete evidence artifact: https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41776143667/artifacts/13298115418
- Exact artifact ZIP SHA-256: `af205307196fcf2390d17a14daa3bdd02270d57a1c712d7a5a7038b07d4bf02c` (120,847,121 bytes).
- **105 regression tests passed**. The job independently validated every source CNF, the full/deduplicated portfolio, lossless and half-size portfolios, their witness streams, source identities, dominance proofs, all resumed terminal CNFs and the independently replayed best historical policies. The unchanged `verify.cpp` was compiled separately.
- I downloaded the exact artifact ZIP through the connected GitHub application. Its computed SHA-256 matches GitHub's digest, all **8,626 ZIP entries** passed CRC validation, and **8,625/8,625 manifest-indexed files** passed independently computed SHA-256 checks. The one remaining ZIP entry was the checksum manifest itself.

## Exactly matched four-case methodology

The two singleton/doubleton destination orbits are target 0 and target 3. Each is split into its two exhaustive first-hop branches, yielding t0-b0, t0-b1, t3-b0 and t3-b1. Their pinned frozen failure-mask families have **2,701 masks for target 0** and **2,181 for target 3**. Each cell generated **one** CaDiCaL195 and **one** MapleChrono independently audited source CNF, with five seconds of active source-search time apiece. Actual complete-policy SHA-256 divergence was required, not inferred from backend names.

All selected portfolios in the same cell derive from these **identical two source CNFs**, preserving the same one-bit legal selector encoding, common source injection, locally observed live ports, incoming port, and the same physical-first-hop branch. The *only intended different dimension* is which independently necessary clauses from the same certified pool are initially retained.

The continuation arms used CaDiCaL195, seed `20261103`, first-witness refinement, the same 96-new-clause cap per raw assignment and **seven seconds of active search time each**. Independent source generation, new portfolio construction, source audits and checkpoint import/setup were measured separately rather than treated as free. Best historical invalid policies were sampled on raw model 1 and each eighth model thereafter and independently replayed in Python.

## Main comparison — best sampled historical invalid policy

Lower is better: counts are **frozen residual masks on which at least one connected nonself source fails delivery**. These are *best among periodically sampled historical raw SAT assignments*, not terminal CNF satisfying policies and not graph-positive certificates.

| Case | CaDiCaL only | MapleChrono only | Full pooling | Shortest half | Source-balanced half |
| --- | ---: | ---: | ---: | ---: | ---: |
| Target 0, branch 0 | 772 | 959 | 662 | 658 | 721 |
| Target 0, branch 1 | 672 | 735 | 700 | 673 | 663 |
| Target 3, branch 0 | 473 | 416 | 444 | 439 | 410 |
| Target 3, branch 1 | 418 | 496 | 549 | 443 | 426 |

The globally shortest-half selection improved on full pooling in **all four cells** for this single bounded configuration. Balanced-half improved on full pooling in **three cells**; in target-0/branch-0 it was worse. The best of the two half-size choices improved the sampled score relative to the full union in every case, but selecting whichever treatment happened to score best after observing outcomes creates selection bias. Importantly, even the improved half-size portfolios did **not** outperform the best single-source control in every cell.

| Case | Best individual source | Best half variant (chosen post hoc) | Improvement vs full pooling (fewer masks) | Improvement vs best individual source |
| --- | ---: | ---: | ---: | ---: |
| Target 0, branch 0 | 772 | 658 | +4 | +114 |
| Target 0, branch 1 | 672 | 663 | +37 | +9 |
| Target 3, branch 0 | 416 | 410 | +34 | +6 |
| Target 3, branch 1 | 418 | 426 | +123 | -8 |

All **20 continuation arms** ended `UNKNOWN` and acquired **zero complete finite-suite candidates**. Smaller failure counts do not establish eventual convergence.

## Clause counts and exact mask coverage

The `lossless` selector checks clause subsumption exactly with a shortest-first trie. A clause is removed only when some retained (D) is a subset of it, (Dsubseteq C); then its negative-selector disjunction is logically implied by (D). The complete dominator indices and original clause ordering are preserved. No exact subsumption was found in any of these four source collections, so the lossless CNFs retained the full numbers of clauses.

| Case | Full unique necessary clauses | Shortest-half clauses | Balanced-half clauses | Subsumed clauses | Full witness masks | Shortest-half witness masks | Balanced-half witness masks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Target 0, branch 0 | 42,366 | 21,183 | 21,183 | 0 | 1244 | 1205 | 1244 |
| Target 0, branch 1 | 43,164 | 21,582 | 21,582 | 0 | 1253 | 1222 | 1253 |
| Target 3, branch 0 | 40,465 | 20,233 | 20,233 | 0 | 1378 | 1339 | 1378 |
| Target 3, branch 1 | 39,131 | 19,566 | 19,566 | 0 | 1381 | 1335 | 1381 |

In all four cells, source-balanced half retained **every static failure mask represented by at least one certified witness** in the full union. The globally shortest-half selection lost some witness-mask coverage. These figures describe the diversity of **retained failing-walk certificates**, not the routing policy's success/failure rate.

The half-size CNFs are logically **weaker** than the full union, but all clauses they retain remain independently necessary for any successful routing policy. Hence they introduce no false restrictions. Their full CNFs and each selected source-reachable witness passed independent reconstruction and audit.

## Search work, resource costs, and limitations

| Case | CaDiCaL raw models | Maple raw models | Full raw models | Shortest raw models | Balanced raw models |
| --- | ---: | ---: | ---: | ---: | ---: |
| Target 0, branch 0 | 315 | 319 | 313 | 314 | 320 |
| Target 0, branch 1 | 319 | 319 | 316 | 320 | 316 |
| Target 3, branch 0 | 302 | 296 | 297 | 302 | 305 |
| Target 3, branch 1 | 302 | 300 | 302 | 304 | 305 |

Each source search had five seconds of active budget, but the observed source wall time was roughly 7.5–8.1 seconds after construction and auditing. Creating the original full portfolio took about 5.2–5.9 seconds per cell; creating the selected variants took about 5.1–7.0 seconds each. Each continuation's **independent checkpoint resume and full audits are additional preparation costs** before its seven-second active-search budget. The selected variants' time savings in the CEGAR step do not automatically repay this preparation overhead.

These are **four mathematically defined partitions under one deterministic seed**, not four independent random samples or statistically replicated optimization trials. The result is an informative one-budget heuristic comparison, **not** a claim that short portfolios are consistently superior, a proof of a one-bit routing construction, or a negative impossibility theorem. Earlier matched experiments on different budgets/refinement schedules also showed mixed pooling effects, so longer and genuinely diversified validation remains appropriate.

## Reproduction

Complete parameters and the precise soundness argument are in [SELECTIVE_PORTFOLIO.md](SELECTIVE_PORTFOLIO.md). The tested workflow is `.github/workflows/k11122-selective-pooling.yml`. The evidence ZIP preserves all source and derived CNFs, sorted mask sets, global legal selector numbering, complete witness JSONL, hashed source manifests, dominance indices, logged SAT runs, C++ binary hashes, independent best-policy replays, and 105 passing test logs. The machine-readable report is [SELECTIVE_PORTFOLIO_RESULTS_20261104.json](SELECTIVE_PORTFOLIO_RESULTS_20261104.json).

A genuine **positive** still requires a complete legal one-bit routing table for **both** target orbits, independently checked on all **524,288** failure masks and every target-connected source. A genuine **negative** requires sound complete translation and independently checked UNSAT refutations of **both exhaustive first-hop branches** of at least one orbit. Neither has been obtained. No recurring automation or unbounded search was started.
