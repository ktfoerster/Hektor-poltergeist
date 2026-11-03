# K11122: both-orbit × both-first-hop portfolio matrix — completed

**3 November 2026. Scientific classification: UNKNOWN for both destination
orbits and all four first-hop branches.** No complete finite-suite positive
routing table and no independently checked impossibility proof was found.
The established 2–3-state bound is unchanged.

## Provenance

- Tested source commit: \`ea7c5a4bd8e26b630f4f2b4faecfea7a59c85129\`.
- **Successful full hosted GitHub Actions run:**
  https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41624096550
- **Complete uploaded evidence ZIP:**
  https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41624096550/artifacts/13224879222
- GitHub-reported artifact size: **145,222,754 bytes**.
- GitHub-reported artifact ZIP SHA-256:
  \`2cd8085a86db91b473975e6ac04602ffbcae6b0279057cc33a383edd5c244400\`.
- The job successfully generated its internal \`SHA256SUMS\`, uploaded its
  archive, and passed all independent CNF/witness audits and
  cross-language policy replays. An additional external ZIP download
  attempt was rejected by an account-ingress limit, so **a separate
  post-download ZIP integrity recheck is not claimed here**.
- **97 regression tests passed**, including all prior certificate
  integrity, routing semantics, journal, checkpoint, transfer,
  diversification, portfolio and historical-best checks, plus new
  four-case model-hash and corruption tests.
- Separate strict C++ builds passed for the rank-free scanner and
  historical-policy quality scorer; the unchanged independent
  exhaustive \`verify.cpp\` was compiled and hashed.

## Exact experimental conditions

Four exhaustive combinations were studied:

| Cell | Orbit | Physical first-hop branch | Strict frozen masks |
| --- | --- | --- | ---: |
| t0-b0 | Singleton target 0 | 0 | 2,701 |
| t0-b1 | Singleton target 0 | 1 | 2,701 |
| t3-b0 | Doubleton target 3 | 0 | 2,181 |
| t3-b1 | Doubleton target 3 | 1 | 2,181 |

Each cell separately generated two **seven-second active-search**
source-CNF checkpoints, one by CaDiCaL195 and one by MapleChrono.
Both used identical normalized legal one-bit selector rows,
the same frozen masks, branch, seed 20261103, and a one-in-eight
hybrid rank-free lasso sampler with 96 necessary clauses at most per
SAT assignment.

For each cell, every emitted C++ failing-walk witness, from
source injection through its reachable prefix to the first repeated
full arrival state, was independently checked in Python. Both entire
source CNFs passed reconstruction against their witness streams.
Their complete routing-policy SHA-256 traces were compared at
corresponding SAT model indices, rather than assuming different
backends automatically imply different exploration.

**Genuine divergence was confirmed in all four cells:**

| Cell | First different complete-policy hash |
| --- | ---: |
| t0-b0 | SAT model 2 |
| t0-b1 | SAT model 1 |
| t3-b0 | SAT model 2 |
| t3-b1 | SAT model 1 |

Thus the sources actually explored distinct complete routing tables
on the same legal problem within every cell. This establishes
operational diversity, not independent statistical sampling.

The new standalone portfolio in each cell contains only
canonical, deduplicated **necessary** source-reachable lasso
clauses. Its exactly-one base CNF and physical-first-hop branch
assertion are reconstructed from scratch. No source SAT backend
memory, assumptions, proof verdict, source policy, phase hint,
rank variable or extra mutable packet state is imported.
The complete portfolio was independently audited again.

The three continuation arms per cell started with the
CaDiCaL-only source, the MapleChrono-only source, or the combined
portfolio. **All three continuations used CaDiCaL195,
seed 20261103, the same first-witness C++ scanner and a
nine-second active-search budget.** This deliberately avoids
a scheduling confound from different inherited hybrid modulo
counters. Source generation, certificate auditing, checkpoint
construction and import time are outside the active budget
but recorded explicitly; none is treated as free.

The historical policy-quality diagnostic scored the first raw
SAT policy and every eighth subsequent policy. Every selected
best historical policy was **independently replayed in Python**
over every connected nonself source in every frozen residual mask.
These are scores of historically generated raw policies, **not**
necessarily satisfying assignments to the terminal strengthened
CNF and not graph-positive certificates.

## Certified portfolio contribution

| Cell | CaDiCaL necessary clauses | MapleChrono necessary clauses | Exact duplicates removed | **Unique clauses pooled** |
| --- | ---: | ---: | ---: | ---: |
| t0-b0 | 48,768 | 35,232 | 1,719 | **82,281** |
| t0-b1 | 46,464 | 32,256 | 1,453 | **77,267** |
| t3-b0 | 47,712 | 27,648 | 1,638 | **73,722** |
| t3-b1 | 44,832 | 29,280 | 1,299 | **72,813** |

Every pooled clause traces to an independently certified
source-reachable deterministic failure and is necessary
for any successful routing policy of that cell's model.
None of these totals proves the space of legal policies empty.

## Best *sampled historical* invalid policies

**Lower distinct failing-mask count is better.** The denominator
differs by target orbit (2,701 versus 2,181), so numbers from
different orbits should not be compared without normalization.

| Cell | CaDiCaL-only | MapleChrono-only | Pooled | Pooled result |
| --- | ---: | ---: | ---: | --- |
| t0-b0 | 651 | 631 | **531** | **Better** than both |
| t0-b1 | **534** | 709 | 629 | **Worse** than CaDiCaL alone |
| t3-b0 | 440 | 491 | **427** | **Better** than both |
| t3-b1 | 400 | 447 | **339** | **Better** than both |

The pooled run improved over the **best single-source
continuation** in **three of four** cells:

- Target 0, branch 0: 631 → 531 (100 fewer masks, **15.8% reduction**).
- Target 0, branch 1: 534 → 629 (**95 more**, approximately
  **17.8% worse**).
- Target 3, branch 0: 440 → 427 (13 fewer, **3.0% reduction**).
- Target 3, branch 1: 400 → 339 (61 fewer, **15.3% reduction**).

The independent connected-source failure counts tell the
same qualitative story:

| Cell | CaDiCaL-only | MapleChrono-only | Pooled |
| --- | ---: | ---: | ---: |
| t0-b0 | 2,070 | 1,969 | **1,542** |
| t0-b1 | **1,651** | 2,261 | 1,803 |
| t3-b0 | 1,254 | 1,511 | **1,219** |
| t3-b1 | 1,125 | 1,449 | **921** |

These are **best among sampled raw SAT assignments**, not proof
of delivery for all connected sources on the frozen suite.
In particular, none of the twelve continuations produced a
complete finite-suite-passing candidate.

## Search work and all preparation overheads

| Cell | Raw models, CaDiCaL | Raw models, Maple | Raw models, pooled |
| --- | ---: | ---: | ---: |
| t0-b0 | 579 | 591 | **604** |
| t0-b1 | 613 | **656** | 592 |
| t3-b0 | 621 | **661** | 608 |
| t3-b1 | 635 | **646** | 638 |

Every continuation consumed approximately 9.00 seconds of
active-search time. The pooled CNF contains more necessary
constraints, which may improve propagation or may impose
costs; raw SAT assignment counts are not a reliable
standalone measure of progress.

| Cell | CaDiCaL start preparation | Maple start preparation | Pooled start preparation |
| --- | ---: | ---: | ---: |
| t0-b0 | 2.565 s | 1.913 s | **4.438 s** |
| t0-b1 | 2.510 s | 1.709 s | **4.110 s** |
| t3-b0 | 2.434 s | 1.428 s | **3.791 s** |
| t3-b1 | 2.283 s | 1.511 s | **3.718 s** |

The **two seven-second source-generation runs per cell** and
their independent complete audits are additional portfolio
research costs. The pooled setup also costs more than
either single-source setup. A one-run, equal-active-time
quality advantage is **not** a measured end-to-end
amortized speedup, and it does not establish repeatability.

## Outcome and next research step

**Engineering:** genuinely diversified and independently
audited necessary-lasso portfolios can be constructed for
all four cells without changing the routing model.
Their best sampled historical invalid routing-table quality
improved in three cells but worsened in target 0, branch 1.
This rules out the naive claim that more certified clauses
always yield better short-budget SAT search.

**Mathematics:** all **twelve continuation runs ended UNKNOWN**
with **zero complete finite-suite candidates**. Neither
destination orbit is classified, and no one-bit feasible
policy or certified impossibility proof follows.

The next justified experiment should target **selective
clause-portfolio construction** and the t0-b1 regression:
determine whether clause subsets, diversity or subsumption
reductions can improve SAT search without excluding any
legal routing policy. Use multiple **genuinely divergent**
solver trajectories and report actual candidate attainment,
independently checked best raw policy failures, conflicts,
source construction and import costs at equal total and
active budgets. Avoid merely increasing timeouts on an
unchanged configuration.

Reproduction commands and exact semantics are in
[PORTFOLIO_MATRIX.md](PORTFOLIO_MATRIX.md).
The successful hosted workflow preserves all four case
results, 8 source searches, four independent portfolio
CNFs, 12 terminal continuations, exact source hashes,
policy tables, full witness streams, checksums and
independent audit logs in the linked artifact.

An actual positive still requires an independently verified
legal routing policy for **both destination orbits on all
524,288 residual masks** and every connected nonself source.
An actual negative requires a sound complete encoding and
independently checked UNSAT refutations of **both exhaustive
first-hop branches** of at least one orbit. No recurring
automation or unbounded computation was created.
