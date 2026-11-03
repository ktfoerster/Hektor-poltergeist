# K11122 multi-solver necessary-lasso portfolio — independently audited pilot

**3 November 2026. Status: UNKNOWN for both destination orbits.**
One-bit perfect resilience on \(K_{1,1,1,2,2}\) is unresolved, and
the established packet-state bounds remain 2–3 states. This experiment
does **not** provide a full resilient routing table, a finite-suite SAT
candidate, or an independently checked impossibility proof.

## Exact provenance

- Tested implementation source:
  \`4ec2ad63d276d1c212f9a20bba7009d3def73cce\`.
- Successful GitHub Actions run:
  https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41615268456
- Complete reproducible source/checkpoint/verification artifact:
  https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41615268456/artifacts/13221356526
- Downloaded evidence ZIP: **33,738,582 bytes** and SHA-256
  \`30d95d181a4898ac8620701f7df493018df8a01dcb8234c95e79033b3840b2aa\`.
- The downloaded archive matches GitHub's digest, passes complete
  CRC validation of all **2,611 entries**, and all **2,610
  SHA256SUMS-indexed files** passed independent SHA-256 checks.
  The remaining entry is the checksum index. Inside the ZIP, paths
  are relative to the \`evidence/\` source directory; the manifest
  records that directory as a prefix.
- **94 regression tests passed**, including all earlier source-reachable
  routing-model safety tests, exact literal/walk semantics, separate
  C++ and Python verifiers, journal and generation checkpoint recovery,
  transfer/caching/phase policies, best historical policy validation,
  and new portfolio provenance, duplicate-clause, corruption,
  cross-branch/target rejection, and SAT resume tests.
- The complete exact source CNFs, candidate policies, witnessed
  necessary clauses, branch constraints, global selector maps,
  frozen mask family, portfolio CNF and all three final CNFs were
  independently reconstructed and audited. The unchanged C++ exhaustive
  \`verify.cpp\` was built separately. It had no finite-suite-passing
  candidate to test for a full-graph positive.

## Mathematical safety of clause pooling

Both sources use **exactly** the same seven-vertex graph, target 0,
physical first-hop branch 0, and 2,701 strict unconditional residuals,
plus the same local injection and forwarding observation semantics.
The phase / SAT backend state itself is not imported. Every learned
\`witnesses.jsonl\` entry describes one connected source's deterministic
failing walk, from injection through the first repeated full arrival
configuration. The independent \`checked_clause\` program reconstructs
its necessary negative selector clause from the entire reachable trace.

The new \`lasso_portfolio.py\` first fully audits **each** source
formula. It then independently checks every witness again, deduplicates
identical selector sets, and reconstructs the complete CNF as the
legal exactly-one base constraints, *one newly generated common
branch assertion*, and the union of the sound necessary clauses.
No solver-internal learned clauses, backend UNSAT statuses, rank
variables, phase preferences, source packet identity or additional
mutable bit are transferred. The union is valid because every
individual necessary clause holds in every legal successful
routing policy.

The resulting new portfolio includes exact SHA-256 fingerprints of
the source CNFs, witness streams and source manifests, the source
backend/seed/phase metadata, clause counts, and independent source
audits. The portfolio itself passes the unchanged independent
full-CNF audit before being accepted as an ordinary resumable
checkpoint. Source code version mismatches continue to require
an explicit full audit and migration, rather than bypassing validation.

## Strict matched target-0 experiment

Two separate **9-second active** source searches independently
generated necessary failing-walk clauses on the same frozen
2,701-mask target-0/branch-0 suite. The CaDiCaL195 and
MapleChrono complete-policy SHA-256 sequences showed **actual
divergence**, not just different backend labels.

| Certified input | Original source witnesses |
| --- | ---: |
| CaDiCaL195 | **42,816** |
| MapleChrono | **31,296** |
| Sum before deduplication | **74,112** |
| Identical clauses deduplicated | **1,418** |
| **Unique necessary clauses in portfolio** | **72,694** |

Thus the two sources contributed **29,878 useful distinct additional
clauses beyond CaDiCaL alone**, while 1,418 clauses overlapped.
The portfolio retained every independent source fingerprint, exact
witness and source-audit result in the checkpoint artifact.

Three resumed continuations then used identical CaDiCaL195,
seed 20261103, the same frozen residual suite, the same
normalized one-bit selectors and branch 0, and exactly
**12 seconds active search** each, using the hybrid
one-in-eight lasso sampling policy with up to 96 new
necessary witnesses per completed SAT assignment.
The initial CNFs differ solely in their independently
certified sets of necessary lasso clauses.

| Measurement | CaDiCaL source only | MapleChrono source only | **Pooled portfolio** |
| --- | ---: | ---: | ---: |
| Imported independently certified clauses | 42,816 | 31,296 | **72,694** |
| Newly learned, independently certified clauses | 54,624 | 56,352 | 54,816 |
| Total certified clauses after continuation | 97,440 | 87,648 | **127,510** |
| Raw SAT models processed | 570 | **588** | 571 |
| Best sampled historical policy, distinct failing masks | 395 | 435 | **366** |
| Best sampled historical policy, failing connected sources | 1,088 | 1,186 | **1,086** |
| Initial independent audit/import/checkpoint preparation | 4.187 s | 3.134 s | **7.099 s** |
| Active search time | 12.003 s | 12.005 s | 12.017 s |
| Finite-suite candidates | 0 | 0 | 0 |
| Terminal classification | UNKNOWN | UNKNOWN | UNKNOWN |

The portfolio's best sampled historical raw policy failed
**29 fewer masks (7.34%)** than the CaDiCaL-only source
continuation, and **69 fewer (15.86%)** than the
MapleChrono-only source continuation. The pooled run
examined essentially the same number of raw models as
the CaDiCaL source continuation (571 vs 570).
This is an *encouraging, limited one-budget computation*,
**not** evidence of a theorem, statistical convergence
superiority, or an end-to-end runtime win.

The pooled run costs more setup and input computation. Its
**7.099-second initial portfolio audit/resume preparation**
exceeds the single-source preparation costs. The two
separate 9-second source searches, their independent audits
and constructing/deduplicating the portfolio are also
additional research overhead; none is hidden inside the
12-second active continuation budget. The experiment did
not include a matched target-3 or branch-1 portfolio search.
Both destination orbits remain open.

A best historical policy is a raw SAT assignment from an
*earlier learned CNF*, not necessarily a satisfying assignment
of the terminal strengthened formula. The best policy was
measured by the first complete assignment and every eighth
thereafter. It is best among those samples, **not among all
examined assignments**. Every selected best table passed
an independent complete finite-suite Python replay on all
connected sources and its original 2,701 residuals.

## Complete CNF fingerprints

| Bundle | SHA-256 of the independently audited CNF |
| --- | --- |
| CaDiCaL source-only continuation | \`ff4c0ce7d43db62baede261fb7fbfaa54b5624f2d7679f7c2ebfa2ada75ebd1c\` |
| MapleChrono source-only continuation | \`5f2560fe4e839bbb907da6c88037443d6c615201233dacc841a0529d478a81ac\` |
| Portfolio continuation | \`ce8051fc7f04096fd12d9bde8cede0fccfe0a7aed0228e49ece7f96c7b689909\` |

These digests fingerprint the three *terminal CNFs*, not
abstract mathematical proof objects. The initial source
CNF/manifest/witness digests are available in the
\`portfolio/portfolio-summary.json\` report and the final
artifact's SHA256SUMS index.

## Interpretation and next research direction

Pooling independently justified necessary source-reachable
lasso clauses from genuinely distinct solver trajectories is
safe and reproducible. It may improve the quality of the
best *sampled* invalid routing table after fixed active
search, as observed here, but the experiment is too small
to establish repeatability, end-to-end efficiency or progress
toward the terminal mathematical classification.

The next justified step is to test **more than one independent
solver trajectory, target and physical-first-hop branch**
with a fixed, auditable clause-portfolio construction. Rank
portfolio and single-source methods on best *independently
checked* raw-policy failures and on actual finite-suite
candidate acquisition; measure all source searches and audit
overheads. Reject false independence by comparing complete
policy SHA-256 traces. A longer job is warranted only with
evidence of useful improvement, not repeated unchanged
solver timeouts.

Mathematical **positive**: an independently verified legal
policy for *both target orbits* surviving all 524,288
residual masks for every connected nonself source.
Mathematical **negative**: a sound complete reduction and
independently checked UNSAT refutations of *both exhaustive
first-hop branches of one orbit*. Neither exists here.

All exact commands and constraints are in
[PORTFOLIO.md](PORTFOLIO.md) and the committed
\`.github/workflows/k11122-portfolio.yml\`. No recurring
automation or uncontrolled external compute was created.
