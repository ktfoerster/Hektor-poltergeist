# K11122: matched four-case selective pooling across CaDiCaL195 and MapleChrono

**Date: 4 November 2026. Mathematical classification: UNKNOWN for both
destination orbits.** One-bit (two-state) perfect resilience for
\(K_{1,1,1,2,2}\) remains unresolved within the established 2–3-state bound.
No independently checked whole-graph positive or certified UNSAT refutation
was found. All 24 terminal searches ended \`UNKNOWN\` and found **zero**
complete finite-suite candidates.

## Provenance

- Tested source commit:
  \`172f039767657c5f83ffff8bd9e36bface2f5ce3\`.
- Completed and successful GitHub Actions run:
  https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41811555234
- Full immutable artifact:
  https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41811555234/artifacts/13312369356
- Artifact ZIP exact SHA-256:
  \`6321080266616aca088462f50e3c0d7d5d2761862dfc57dddd03e2fdb83b037d\`,
  117,861,804 bytes.
- **109 regression tests passed**. The unchanged independent C++
  \`verify.cpp\` and original C++ lasso and policy-quality scanners were
  separately compiled with the pinned tools.
- The downloaded GitHub artifact matched the published SHA-256.
  An independent pass decoded and CRC-checked all **8,170 ZIP files**,
  verified all **8,169 SHA256SUMS-indexed file hashes**, found **zero
  missing/extra entries** and **zero hash mismatches**. The remaining
  ZIP member is the SHA256SUMS index itself.
- Every one of the 8 source searches, 12 new portfolio CNFs and
  24 terminal continuation CNFs passed the original independent
  full-CNF/reachable-witness audit, including the global legal one-hot
  selector domain, precise first-hop branch, all certified prefix/cycle
  witnesses and complete frozen mask family. All 24 historical best
  raw policies passed independent literal-walk replay.
- Exact raw evidence and parsed matrix:
  \`independent-cross-backend-summary.json\`,
  \`matrix/matched-backend-summary.json\` and
  \`matrix/t*-b*/case-results.json\` in the artifact.

## Controlled experiment

Four original target/first-hop combinations are investigated:
\`t0-b0\`, \`t0-b1\` (singleton target orbit; **2,701** strict residuals);
\`t3-b0\`, \`t3-b1\` (doubleton target orbit; **2,181** strict residuals).

For **each** case, two distinct initial source searches ran for **four
seconds active time each** on the same exact routing model, mask family
and branch, using CaDiCaL195 and MapleChrono. Their full routing-policy
SHA-256 streams *actually diverged in every case*. All source CNFs and
their necessary source-reachable lasso clauses were independently
audited before portfolio construction.

From these **same two source checkpoints**, exactly three initial
CNFs were constructed and independently audited: complete union
(\`all\`), \`shortest-half\`, and source/mask-\`balanced-half\`.
All omitted clauses in half portfolios are independently necessary
clauses discovered by the sources; selecting fewer is a **weaker**
starting CNF, not an extra restriction on the policy space. No source
solver-internal conflict clauses, source backend state or arbitrary
arrival obligations were imported.

Each portfolio was continued for a nominal **five-second active search**
with CaDiCaL195 and with MapleChrono, same seed \`20261103\`,
identical fast first-witness learned-clause method, same 96-new-witness
cap per raw SAT assignment, and identical frozen masks. The backend
policy-hash streams diverged on **all 12** fixed-portfolio backend pairs.
Observed active durations were approximately **5.00–5.64 seconds**,
so these are bounded nominal budgets, not exactly equal CPU instruction
counts or a statistical runtime study.

The diagnostic independently replays the best **historically sampled
raw SAT policy** against every connected source for every frozen
residual; scoring is on model 1 and every eighth model, not on all
models. These historical policies may violate necessary clauses
learned after they were generated. They are **not** terminal CNF
models, finite-suite-passing policies or graph-positive certificates.

## Main quantitative result: best sampled failing residual masks

**Lower is better. Scores across different target orbits should
not be compared as if they were drawn from the same mask family.**

| Case | Continuation backend | Complete union | Shortest half | Source-balanced half |
| --- | --- | ---: | ---: | ---: |
| t0-b0 | CaDiCaL195 | 741 | 764 | **658** |
| t0-b0 | MapleChrono | 516 | **423** | 529 |
| t0-b1 | CaDiCaL195 | 720 | **681** | 812 |
| t0-b1 | MapleChrono | 538 | **459** | 461 |
| t3-b0 | CaDiCaL195 | 484 | **427** | 479 |
| t3-b0 | MapleChrono | **265** | 328 | 332 |
| t3-b1 | CaDiCaL195 | 540 | 515 | **413** |
| t3-b1 | MapleChrono | 331 | **251** | 268 |

**Shortest-half beat complete pooling in six of eight** matched
case/backend conditions (three of four CaDiCaL, three of four
MapleChrono); the balanced-half variant beat complete pooling in
**five of eight** (three of four CaDiCaL, two of four MapleChrono).
Neither is universally superior, and selecting the best-looking
half *after the experiment* is post-hoc selection, not validation.
For t3-b0, MapleChrono preferred the **full** portfolio
(265 failures versus 328/332), while CaDiCaL preferred shorter
subsets (427/479 versus 484). The direction of the clause-pooling
effect therefore **interacts with continuation backend**.

A striking second descriptive observation is that MapleChrono
obtained fewer failing masks than CaDiCaL in **all 12**
same-portfolio/case pairs: a fixed-bundle backend change can
have a larger effect than selection of 50% versus 100% of the
necessary source clauses. This is **one seed on one CI runner**
with different backend algorithms and nonidentical per-backend
sampled trajectories, not evidence of a universally better solver.

## Full portfolio sizes and search costs

| Cell | Full unique necessary clauses | Shortest half | Balanced half |
| --- | ---: | ---: | ---: |
| t0-b0 | 41,881 | 20,941 | 20,941 |
| t0-b1 | 45,803 | 22,902 | 22,902 |
| t3-b0 | 41,881 | 20,941 | 20,941 |
| t3-b1 | 40,359 | 20,180 | 20,180 |

The actual **raw model** counts across all 24 continuations,
in order \`all / shortest / balanced\`, were:

| Cell | CaDiCaL195 raw models | MapleChrono raw models |
| --- | --- | --- |
| t0-b0 | 315 / 316 / 315 | 182 / 223 / 215 |
| t0-b1 | 306 / 273 / 280 | 163 / 230 / 182 |
| t3-b0 | 287 / 285 / 274 | 163 / 134 / 143 |
| t3-b1 | 278 / 289 / 289 | 158 / 182 / 159 |

The independently audited **continuation preparation time**
was approximately 2.77–3.22 seconds for full portfolios and
1.24–1.48 seconds for half portfolios. This is a substantial
reduction in import/recheck overhead for the smaller initial
witness families. It does **not** include the two original
source-search and per-portfolio construction/audit costs.
The same five-second active search budgets do not establish
an overall end-to-end speedup.

Cumulative observed SAT conflicts were recorded for all
runs. They are backend-specific counters and must **not**
be compared as directly interchangeable solver operations.
The exact conflict/propagation counts, wall timings,
preparation timings, policy hashes and all source and
terminal CNF SHA-256 fingerprints are in the linked
machine-readable artifact.

## Interpretation and next research step

Compared to the prior single-backend selective pilot,
these results **reject the blanket hypothesis** that
shortest-half pooling produces better historical raw-policy
quality in all four graph cells irrespective of backend.
They support a narrower engineering hypothesis: *selective
necessary-clause pooling is worth exploring and can reduce
audit/import overhead, but its search benefit is
backend- and case-dependent*. The earlier pilot and this
one also differ in source/continuation time budgets and
hence cannot be treated as controlled repeated samples.

The next useful experiment should avoid still more
unchanged solver timeouts. Candidate directions are
(i) cross-backend portfolio schedule selection using an
**independent training suite** rather than picking the best
post-hoc, (ii) actual finite-suite candidate acquisition
rather than historical sampled failure-count improvements,
and (iii) targeted structural constraints/proofs for the
remaining hard cases. For any new hypothesis, retain exact
source-visible failure models, independently checked lasso
certificates and full checkpoint auditability.

**Mathematical positive:** one legal policy for *both* target
orbits, independently verified across all **524,288**
residual masks and all connected nonself sources.
**Mathematical negative:** a sound complete reduction and
independently checked UNSAT refutations for *both*
exhaustive first-hop branches of one orbit. Neither is
provided by these results. No recurring automation,
unbounded computation or uncontrolled cloud job was started.

Reproduction is documented in
[SELECTIVE_CROSS_BACKEND.md](SELECTIVE_CROSS_BACKEND.md).
The tested CI workflow is
\`.github/workflows/k11122-selective-robustness.yml\`.
