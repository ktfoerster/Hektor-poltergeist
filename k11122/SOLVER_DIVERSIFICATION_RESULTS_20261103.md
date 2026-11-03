# K11122 rank-free SAT: verified genuine trajectory diversification

**3 November 2026. Scientific result: UNKNOWN for both destination
orbits.** This experiment does not change the established 2–3
packet-state bound for K_{1,1,1,2,2}. No valid one-bit routing
table passed complete verification for both target orbits, and
no independently checked impossibility proof was obtained.

## Completed and reproducible evidence

- **Tested source commit:**
  \`9020058c9275f70168dff0fb46e65e7b77fc4dde\`.
- **Successful hosted run:**
  https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41610463239
- **Complete downloadable evidence:**
  https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41610463239/artifacts/13219485488
- **Exact artifact size:** 59,644,940 bytes.
- **Exact artifact ZIP SHA-256:**
  \`bde08ae134059820887babfdade91c7bc737788a2f9f7f3977398862baeff5eb\`.
- The downloaded ZIP matches that GitHub digest. All **4,809**
  ZIP entries passed CRC inspection; all **4,808 SHA256SUMS-indexed
  files** matched SHA-256, with the extra file being SHA256SUMS.
  Manifest paths are repository-root-relative (\`evidence/\`);
  ZIP member paths are relative to that evidence directory.
- **91 regression tests passed**, including every earlier routing
  and certificate safety test, plus exhaustive legal phase-row
  coverage, strict phase-file validation, phase-preference
  nonrestriction of the SAT formula, journal/generation checkpoint
  phase-file integrity, and correct hash-sequence divergence checks.
- Strict \`g++ -O3 -std=c++17 -Wall -Wextra -Werror\`
  compilation succeeded for the untrusted C++ witness selector
  and policy scorer. The unchanged exhaustive independent
  \`verify.cpp\` was built and hashed separately.
- Every source and destination checkpoint CNF, global selector
  map, first-hop partition, witness stream, and independently
  reconstructed source-reachable lasso necessary clause passed
  the existing complete audit. Best sampled raw policies were
  separately replayed in Python against every connected source
  on every mask in their frozen target-specific suites.

## Why this experiment is substantive

Prior seed-only trials returned **identical complete policy
SHA-256 sequences** at each common model index, so they were
not independent solver trajectories even though three different
seed values were configured. This follow-up tests actual
solver-path alternatives, not merely new seed labels:

1. **No hints:** original CaDiCaL195 solver.
2. **Legal first-action preferences:** CaDiCaL195,
   using \`solver.set_phases()\` on the identical CNF.
3. **Legal SHA-256 keyed preferences:** CaDiCaL195,
   same CNF with a different deterministic complete
   legal policy table.
4. **Glucose42 without hints:** independent SAT backend,
   identical selector/CNF input.
5. **MapleChrono without hints:** independent SAT backend,
   identical selector/CNF input.

Each phase file is complete, legal, target-specific, branch-compatible
and byte-preserved. It adds **no constraint** or routing state:
the solver is still permitted to choose every action in its
original one-hot policy domain. Its SHA-256, canonical file,
backend, branch and interpretation are retained with
the audited checkpoint. Forced-negative-selector tests
verify that a preferred action remains rejectable without
making the formula UNSAT.

All target-0 runs begin from precisely the same independently
certified branch-0 checkpoint, with **42,144 necessary
source-reachable lasso clauses** over the same **2,701 frozen
residual masks**. Each receives **12 seconds of active SAT,
witness-checking and checkpoint search**, with source audits
and initial checkpoint publication accounted for separately.
The common seed is 20261103, the hybrid lasso selection period
is 8, and at most 96 certified necessary clauses are learned
per raw SAT assignment.

The target-3 controls begin from another identical
target-3/branch-0 checkpoint for their orbit, with **40,704**
necessary clauses over **2,181 masks**, and **9 seconds
of active search** each.

## Actual model divergence: confirmed, not inferred

\`lasso_divergence.py\` checked every complete routing-table
SHA-256 in \`cpp-batches.jsonl\` at matching *relative model
indices* of the resumed searches, not just selected model
scores. Every tested alternative first differed from its
CaDiCaL no-hint baseline at **relative complete model 1**.

| Comparison with original CaDiCaL, no hints | Target 0 | Target 3 |
| --- | --- | --- |
| CaDiCaL with first-action phases | Divergence at model 1 | Not run |
| CaDiCaL with SHA-keyed phases | Divergence at model 1 | Divergence at model 1 |
| Glucose42 with no phase hint | Divergence at model 1 | Not run |
| MapleChrono with no phase hint | Divergence at model 1 | Divergence at model 1 |

Additionally, across the entire completed target-0
experimental windows, **none** of the four alternatives
produced any exact routing-policy hash present in the
561 complete scanner models of the CaDiCaL baseline.
The two target-3 alternatives likewise had **zero**
whole-table hash overlap with the 399 CaDiCaL baseline
scanner records.

This establishes *genuine exploration of different
complete routing tables*. It does **not** prove that
the generated trajectories are statistically independent,
that any particular search policy is better, or that
the graph is one-bit perfectly resilient.

## Independently replayed best-sampled candidate quality

The new historical-best diagnostic scored the first raw SAT
assignment and every eighth subsequent complete model.
It retained a full policy file, hash, model index, score,
and checksum-bearing provenance. Every reported best table
was independently re-evaluated in Python, on every
connected nonself source in every frozen residual mask.
The score is **best among the sampled raw SAT policies**,
not necessarily among all raw assignments and **not a
SAT model of the final learned CNF**.

### Target 0, branch 0

| Solver / phase | Raw models | Best failing masks (of 2,701) | Best failing connected-source obligations |
| --- | ---: | ---: | ---: |
| CaDiCaL, no hint | 561 | 365 | 1,035 |
| CaDiCaL, first action | 565 | 491 | 1,513 |
| CaDiCaL, hashed action | 554 | 455 | 1,190 |
| Glucose42, no hint | 566 | 409 | 1,126 |
| MapleChrono, no hint | 424 | **355** | **971** |

MapleChrono found a sampled table failing ten fewer distinct
masks than the CaDiCaL baseline (**2.7% fewer**),
and 64 fewer connected-source obligations (**6.2% fewer**).
However, it evaluated **24.4% fewer raw SAT models**
under the same active-search budget. The different
solver paths and a single sample do not establish an
end-to-end convergence advantage.

CaDiCaL with either legal phase preference diverged
immediately but was **worse** on this particular
best-sampled score. Introducing additional heuristics
is not automatically useful for the actual mathematical
problem.

### Target 3, branch 0

| Solver / phase | Raw models | Best failing masks (of 2,181) | Best failing connected-source obligations |
| --- | ---: | ---: | ---: |
| CaDiCaL, no hint | 399 | **246** | **643** |
| CaDiCaL, hashed action | 400 | 385 | 1,027 |
| MapleChrono, no hint | 252 | 265 | 670 |

The no-hint CaDiCaL run had the strongest sampled
table for this orbit. MapleChrono also diverged at
the first complete model but did not improve the
best score. The seeded phase hints showed no benefit
in the one controlled target-3 trial.

## Terminal independently audited CNF fingerprints

All variants use the *same source CNF within their
target orbit*, then learn different necessary lasso
clauses as their policy trajectories diverge.

- Target-0 source CNF SHA-256:
  \`06def853fcaeae699781fc1ff52782d71fc7f07d343e67ce0dafbc1805728f49\`.
- Target-3 source CNF SHA-256:
  \`2eed85c75343a0def4f8c1306fd7df410468d0040a9f356fcbf0ede2d82f3d5b\`.

| Terminal CNF | SHA-256 |
| --- | --- |
| t0 CaDiCaL none | \`c0685f00ab4b6db35261d44f731344bdc8d0558dfebed32cdaa1ff02f7b93022\` |
| t0 CaDiCaL first | \`aa5f5f3d65f99e4aad5065819d25a63d5dca1e81f2ec121192036eda30288068\` |
| t0 CaDiCaL hashed | \`e2c3e4119ff99cb03e967fec7ff9c1fb6b5e669a1841133b9bb011f7e183fd66\` |
| t0 Glucose42 none | \`d1a822d4f60dd532265fcbc8979cae50866105a01e2db3d6ee471498c13d9178\` |
| t0 MapleChrono none | \`540e93e17103aff984228cebe707e23bb1de872e1338a517a4aece258f37d235\` |
| t3 CaDiCaL none | \`0f6a1584e203ed3e5423b393b7f150ba00d96a623107ae720a57f7423041f903\` |
| t3 CaDiCaL hashed | \`7a1382a4e80857a3ca3785564332d67000ac028f46298d236f12c7a20e237a12\` |
| t3 MapleChrono none | \`7ff65e0cc8a8c626b5304852106f16e96da7ed6ec6f238e53381bec44a3ab6a2\` |

Every complete CNF and every mandatory witness was
independently reconstructed and checked. The raw SAT
solver conflict counts differ substantially across
backends and must not be treated as comparable
measures of theoretical proof progress.

## What we learned and what comes next

**Engineering milestone:** The original repeated-seed
problem is now resolved operationally. We can deliberately
generate different search paths, demonstrate exact
policy-hash divergence, and reproduce the complete
constraints and independently checked policy scores
without modifying the routing model.

**Mathematical progress:** There is still no
independently verified complete finite-suite policy,
no verified one-bit policy for both destination orbits,
and no complete checked UNSAT refutation of both
exhaustive first-hop branches of an orbit. Both
orbits remain **UNKNOWN**.

The next research experiment should examine **verified
certificate portfolio learning**: collect independently
checked necessary source-reachable failing-walk
clauses from genuinely different solver trajectories,
deduplicate/canonicalize them without changing the
policy space, and test whether sharing their union
improves conflict efficiency and best-observed
policy quality on a fixed target and branch.
Compare against each unpooled trajectory under equal
**active** search budgets, and report full
independent audit/import overhead separately.
The portfolio must never import backend solver
conclusions, assumptions, or non-necessary learned
internal clauses. A longer computation should only
follow evidence that this is useful, rather than
repeating unchanged timeouts.

Reproduce the complete experiment using
[SOLVER_DIVERSIFICATION.md](SOLVER_DIVERSIFICATION.md),
the pinned GitHub workflow, and the exact downloaded
evidence archive. No recurring automation, external
paid compute, or uncontrolled retry was created.
