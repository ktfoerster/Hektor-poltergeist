# K11122: same-process, independently attested cross-branch transfer cache

**Research classification:** UNKNOWN for both destination orbits. One-bit
perfect resilience on K_{1,1,1,2,2} remains unresolved, with established
bound 2–3 packet states. No solver timeout, raw SAT assignment, or certified
partial CNF is a graph-positive or graph-negative result.

## Why this experiment

The preceding equal-active-search benchmark found that repeatedly auditing
and importing exactly the same independently verified first-hop-branch
counterexamples cost about 5.8 seconds of preparation per transferred
target-0 run. This work reuses the result of **one full semantic audit within
the same Python process**, without weakening or modifying the original
routing model or silently trusting a persisted manifest.

## Trust and mathematical soundness

- \`lasso_transfer_session.certify_session\` invokes the unchanged original
  \`lasso_transfer.transfer\`. That function first reconstructs the **entire
  source DIMACS CNF** independently, including all global legal routing-action
  selectors, all exactly-one and source-branch assertions, every complete
  source-reachable failing-walk clause, and source/manifest hashes. It then
  independently rechecks the semantic witness for every source clause.
- The resulting \`SessionTransfer\` is a *nonportable* immutable in-process
  snapshot of the necessary clauses and their complete JSONL witnesses.
  It cannot be loaded from disk or from user JSON; programmatic reuse
  requires a live cache instance created by the checker in this process.
- Before **every** reuse, the five input files (\`manifest.json\`,
  \`formula.cnf\`, \`selectors.json\`, \`masks.json\`,
  \`witnesses.jsonl\`) are checked against the exact SHA-256 values
  captured at certification. Changes fail closed, as do other graphs,
  target orbits, first-hop branches and frozen residual-mask families.
  A source-code-version mismatch requires explicit audited migration,
  which can only follow the original complete independent source audit.
- On reuse the solver receives the same already-certified clause/witness
  sequence, not a reconstructed verdict and not the old branch assertion.
  The destination's own independent full-CNF/witness audit is **not skipped**:
  it checks every imported witness and necessary clause, exactly-one
  selectors, its own branch assertion, and all new learned constraints.
  Crash-safe journal recovery retains these certificates and provenance.
- The cache is not a portable proof, a standalone trusted artifact, a signed
  theorem or a way to accept externally supplied unverified clauses. Its
  in-memory attestation remains valid only within the same trusted process.
  Restarts must re-certify the source. The original fully audited source
  bundle is always preserved in the output artifact.
- Nothing changes the packet bit, source injection, forwarding observations,
  failure model, allowed source revisits or unreachable-cycle semantics.
  Each transferred constraint still follows from a complete reachable
  deterministic failing execution.

## Benchmark

The self-contained hosted workflow creates two fresh independently audited
source bundles, using frozen target-0 **2,701-mask** and target-3
**2,181-mask** families. It creates the target-specific session cache once
and compares, for each seed, a traditional *full source audit per warm run*
against the **same** globally valid source-reachable clauses replayed from
the cache (with 5-file hash check). Both approaches use the same
global selector table, target, branch 1, exactly the same frozen mask suite,
same CaDiCaL195/pinned Python SAT backend, same seed, same hybrid one-in-eight
witness sampler, and equal **active search budgets**.
Preparation/auditing, source creation, cache certification and final
destination verification are separately timed; no overhead is hidden.

Target 0 uses seeds 20261103, 20261104, 20261105 with 10 active seconds each
per condition. Target 3 has a single independent sanity pair using seed
20261103 and 7 active seconds. The source creation is separately bounded
to 10 and 7 seconds. The entire hosted workflow has a hard 14-minute cap
and creates no recurring task.

The primary evidence index is \`cache-bench/session-cache-comparison.json\`.
For each run it preserves raw models, observed SAT worker counters,
imported and newly independently checked witnesses, exact CNF SHA-256,
preparation/active/total wall time, finite-suite candidate counts, and
independent last-raw-policy failing-mask and connected-source counts.
**The last raw policy is not the best-so-far**, and a smaller number of
raw assignments does not by itself indicate worse SAT convergence.

## Commands

On Ubuntu 24.04 with Python 3.12:

\`\`\`bash
python -m pip install python-sat==1.8.dev24 z3-solver==4.13.3.0
python -m unittest discover -s k11122 -p 'test_*.py' -v
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_batch.cpp -o lasso_batch
g++ -O3 -std=c++17 k11122/verify.cpp -o verify
python k11122/session_cache_benchmark.py \
  --output evidence-session \
  --scanner "$PWD/lasso_batch" --verifier "$PWD/verify" \
  --source-seconds 10 --search-seconds 10 --target3-seconds 7 \
  --seeds 20261103,20261104,20261105
\`\`\`

To generate a cache programmatically, call
\`certify_session(source_bundle, n, target, opposite_branch, exact_masks,
expected_source_hashes=source_hashes())\` in the SAME process that calls
\`lasso_search.run(..., transfer_session_cache=cache)\`. The traditional
\`--transfer-opposite-bundle\` CLI remains the default reproducible standalone
mechanism, and **always re-audits the source**. The cache cannot be passed
through a CLI string or a serialized file.

No positive policy is accepted without the unchanged C++ verifier
exhaustively replaying both destination orbits over all 524,288 masks
and every connected nonself source. No negative conclusion is accepted
without independently checked refutations of both exhaustive first-hop
branches for one destination orbit, with sound, complete constraints.
