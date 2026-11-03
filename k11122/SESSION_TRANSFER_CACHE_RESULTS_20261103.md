# K11122: independently attested same-process transfer cache — completed pilot

**3 November 2026. Scientific status: UNKNOWN for both destination orbits.**
The one-bit perfect-resilience classification of
\(K_{1,1,1,2,2}\) remains unresolved, with the known 2–3-state bound.
No complete legal routing policy or independently checked impossibility
refutation was obtained. Neither raw SAT assignments, source-reachable
necessary clauses, nor passing regression tests constitute a graph theorem.

## Exact provenance and independently checked evidence

- **Tested implementation commit:**
  \`fa90498e18bc95d722e46052fd2ae0d60151610f\`.
- **Successful GitHub Actions run:**
  https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41576262046
- **Complete reproducibility artifact:**
  https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41576262046/artifacts/13203399183
- **Exact archive size:** 71,825,035 bytes; **ZIP SHA-256:**
  \`0fcb435a6093c4d1b0ffa449e043a0ae0f358b91052227f69e2a65821ae22432\`.
- The exact downloaded ZIP matched GitHub's digest; **all 5,535 ZIP
  entries passed CRC validation**; all **5,534 files indexed by SHA256SUMS**
  matched SHA-256 exactly. The one extra ZIP member is the hash manifest
  itself. Manifest paths have an \`evidence/\` prefix, while ZIP members
  are relative to that folder.
- **82 regression tests passed**, including all previous routing-model,
  rank/literal differential, C++-scanner, certificate corruption,
  immutable-generation, crash-safe journal, deterministic scheduling,
  cross-branch transfer and bounded search-clock tests, plus the new
  cache forgery, source mutation, mismatch and both-checkpoint-mode
  integration tests.
- Every source and destination CNF, each one-hot selector mapping,
  both first-hop branch assertions, all generated source-reachable
  lasso clauses and frozen residual suites, and every committed
  destination journal were independently audited. The unchanged
  independent exhaustive C++ graph verifier was built and hashed.
  It was not invoked for a complete candidate because none emerged.

## What the cache does (and does not do)

\`lasso_transfer_session.py\` is a **same-Python-process cache**, not a
portable proof. Initial construction calls the original independent
\`lasso_transfer.transfer\`, which reconstructs the entire source CNF
and independently replays and translates every witness. The cache
holds the resulting immutable source-reachable necessary clauses and
complete witness JSONL records. Every reuse checks SHA-256 digests of
**all five source inputs**: manifest, complete CNF, policy selector map,
frozen mask list, and witness stream. Changes or wrong target, branch
or masks cause rejection.

On every destination run, even a cache reuse, the **complete
destination CNF and all its source-reachable witnesses** are
reconstructed and audited independently. The cache cannot be loaded
from an untrusted JSON file, is invalid after a process restart, and
does not import source branch restrictions, solver state or verdicts.
It retains the exact original packet-bit and local forwarding model.

Traditional standalone \`--transfer-opposite-bundle\` continues to
perform a fresh full source semantic audit for *every* invocation,
without special flags or altered defaults. The new
\`transfer_session_cache\` argument is programmatic and available
only within the one Python process in which it was fully certified.

## Controlled paired benchmark

The self-contained hosted workflow constructed two fresh branch-0
source bundles, each independently certified on its own exact
strict mask union:

| Source orbit | Strict residual suite | Original necessary lasso clauses | Useful certified clauses transferred to branch 1 |
| --- | ---: | ---: | ---: |
| Target 0 | 2,701 | **63,264** | **62,432** |
| Target 3 | 2,181 | **44,499** | **44,366** |

Every matched pair imports **exactly the same source clauses**.
The 10-second target-0 branch-1 active-search experiments used
seeds 20261103, 20261104, 20261105, CaDiCaL195,
\`python-sat==1.8.dev24\`, \`z3-solver==4.13.3.0\`, one-bit
normalized legal global selectors, the same hybrid one-in-eight
witness selection and up to 96 independent new lasso clauses
per SAT model. Preparation/importing and final CNF auditing were
measured separately from the equal active-search budget.

| Target-0 measurement (mean of 3 seeds) | Full source audit every run | Session cache |
| --- | ---: | ---: |
| Preparation seconds per run | **3.376** | **0.896** |
| Raw SAT assignments | 600 | 564 |
| Failing masks of LAST raw policy | 507.0 | 438.7 |
| New learned clauses | 57,536 | 54,048 |
| Imported independently checked clauses | 62,432 | 62,432 |
| Finite-suite candidates | 0 | 0 |
| Status | UNKNOWN | UNKNOWN |

The cache reduces per-run preparation by **73.45%**, saving
approximately **2.480 seconds per reuse**. Its initial full
source certification took **3.084 seconds**. Thus the three-seed
target-0 comparison saved **4.356 total preparation seconds after
including the initial certification** (10.128 seconds for three
uncached preparations versus 3.084 + 2.689 seconds for the
cached strategy). The independent source search itself required a
separate bounded 10-second run and is a **common cost** in both
strategies, not silently excluded from a global research campaign.

The cached trials processed **6% fewer raw SAT models**, but their
last raw policies happened to fail **13.5% fewer masks on average**.
Per-seed failing-mask counts were 509 vs 478, 475 vs 424 and
537 vs 414 (uncached versus cached). These are trajectories of
different SAT executions measured under a small wall-clock budget.
The last raw policy is not the best-so-far policy, and three seeds
do not establish stronger convergence or resilience.

Exact final source/destination SHA-256 values, solver effort
counters, failed connected-source obligations and complete audit
manifests are preserved in
\`cache-bench/session-cache-comparison.json\` in the artifact.

## Other-orbit control and limitations

One 7-second paired target-3/branch-1 run (seed 20261103)
imported **44,366** certified clauses in both conditions.
Preparation dropped from **2.319** to **0.646** seconds. However,
building the cache required **2.037** seconds, so at only one reuse
the observed net saving was **negative 0.364 seconds**. Last-policy
failing masks increased from 327 (uncached) to 406 (cached),
while raw models dropped from 399 to 336. Both remain UNKNOWN.

This demonstrates a real *certification/engineering* amortization
benefit after several uses in the target-0 experiment, **not**
a scientific advance to a solved one-bit classification.
The cache consumes extra process memory for retained certificates;
this pilot does not establish cross-platform memory superiority,
statistical search superiority, or a portable independently signed
proof. A process restart necessarily requires a new independent
full source audit.

## Reproduction and research follow-up

Run the exact pinned commands and workflow in
[SESSION_TRANSFER_CACHE.md](SESSION_TRANSFER_CACHE.md) or use the
complete downloadable artifact. The hosted experiment includes
the 5-file input hashes for each cache, every source and destination
CNF, raw policies, individual seed comparison, solver statistics,
checkpoint journals, exact tested Python/C++ source and workflow,
and all byte-exact audit reports.

**Next meaningful research step:** test whether a retained, independently
checked clause pool actually improves *best-so-far* finite-suite
policy quality or leads to a complete finite-suite candidate, rather
than inferring progress from the last raw model. Use independently
scored best-policy tracking at controlled intervals and compare
conflicts, clause length and achieved failures across paired seeds
on the same suite. Longer compute should be gated on measured
improvement, not simply repeated solver timeouts.

A mathematically positive result still needs independently verified
policies for **both destination orbits** over all 524,288 failure
masks and every connected nonself source. A mathematically negative
result still needs independently certified refutations of **both
exhaustive first-hop branches of one orbit** and a sound complete
CNF-to-routing reduction. Neither condition is satisfied here.

No recurring automation, indefinite search or unmanaged background
compute was started.
