# K11122 — equal active-search timing for certified opposite-branch transfer

This is a **reproducible benchmarking facility**, not a theorem or claim that
one-bit perfectly resilient routing exists or is impossible. The original
model, legal one-hot source/transit selectors, explicit emitted bit,
physical-first-hop partitions, independent lasso-witness checker,
and unchanged exhaustive C++ verifier are preserved.

## Why this experiment is necessary

The preceding same-total-time transfer pilot yielded more necessary
constraints but fewer raw SAT assignments because source CNF auditing
and importing itself consumed 8.50 seconds of a 25-second budget.
Those raw counts cannot determine whether imported clauses improve SAT
convergence. This benchmark isolates **equal active SAT/walk search
time** and reports preparation/audit costs separately, without hiding
any of the costs or deleting any unproductive outcomes.

## Search clock

The default CLI remains \`--budget-scope total\`: the existing
\`--seconds\` budget includes construction, any audited import, and
search. This retains backward compatibility.

An explicitly requested \`--budget-scope search\` starts the countdown
only after **all necessary source audits, opposite-branch witness imports,
and initial durable checkpoint writes**. The \`--seconds\` value then
bounds active SAT/independent-walk/refinement time, while
\`preparation_seconds\`, \`transfer_seconds\`,
\`elapsed_seconds\` (search), \`total_wall_seconds\` (including final
audit and artifact generation), and externally observed wall time are
reported separately. Both journal and immutable-generation checkpoint
implementations use exactly this definition. The original total
budget remains the default and the hosted job itself has a hard
14-minute upper limit. No unlimited search is introduced.

## Separate solver-effort accounting

The unmodified PySAT backend already produces cumulative
\`accum_stats\` counters for conflicts, decisions, propagations,
and restarts in each successful worker response. The
\`lasso_effort.py\` module combines only verified monotone counter
*differences within each persistent worker generation*, including
fresh generation first readings. Counter resets and missing
samples after an externally bounded timeout are recorded explicitly:
the result is **observed effort**, possibly an underestimate, not
a complete proof log. Negative or malformed values cause failure.

## Independent last raw policy quality

\`lasso_policy_quality.py\` checks the exact output CNF and full
policy mapping, independently reconstructs the local 19-edge graph,
replays **every connected source** on all **2,701 target-0** or
**2,181 target-3** frozen residual masks and counts failing source
obligations and distinct masks with at least one failure. A missing
last-policy table receives \`NO_RAW_POLICY\`, never a fabricated
zero-failure result. A passing frozen finite suite does *not*
establish a positive for the entire graph. Nor is the last raw
policy assumed to be the best one generated earlier.

## Three-seed matched benchmark

\`amortization_benchmark.py\` first generates an independently audited
target-0/branch-0 source CNF in a **12-second** bounded search and a
target-3/branch-0 source CNF in **8 seconds**. These are created in the
same job: no prior workflow artifact access, token privileges or
credential installation are required.

It then uses those *same exact source bundles* for paired cold/warm
branch-1 searches across target-0 seeds 20261103, 20261104 and
20261105, each with **12 seconds of equal active search time**,
and a target-3 one-seed sanity pair with **8 seconds**.
The legal routing-policy search domain, sorted frozen masks,
physical first-hop branch, CaDiCaL195 backend, seed, hybrid scanner
schedule (every eighth model), and maximum 96 witness clauses per
SAT assignment are matched within each pair.

Each warm trial **re-audits the complete source CNF and every witness**
before use; source provenance, input mask family, branch difference,
and imported clause count are independently checked every time.
The one-time source construction cost and per-run import/audit cost
are reported in full. For each output, a separate journal-prefix
audit and full byte-for-byte CNF reconstruction are required.
The experiment records solver effort, raw models, new and inherited
verified clauses, exact CNF digest, candidate counts, replay time,
and independent last-raw-policy diagnostic.

The seeds are intentionally few: this is a **pilot**, not a
statistically significant runtime superiority study. A warm-start
with many clauses could solve fewer raw SAT assignments precisely
because it constrains invalid policy assignments more strongly;
the only decisive endpoints remain an independently exhaustive
positive or certified complete negative.

## Reproduction

Run on Ubuntu 24.04 with Python 3.12, the pinned solvers
\`python-sat==1.8.dev24\` and \`z3-solver==4.13.3.0\`:

\`\`\`sh
python -m pip install python-sat==1.8.dev24 z3-solver==4.13.3.0
python -m unittest discover -s k11122 -p 'test_*.py' -v
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_batch.cpp -o lasso_batch
g++ -O3 -std=c++17 k11122/verify.cpp -o verify
python k11122/amortization_benchmark.py \
  --output evidence-amortized \
  --scanner ./lasso_batch --verifier ./verify \
  --source-seconds 12 --search-seconds 12 \
  --target3-seconds 8 --seeds 20261103,20261104,20261105
\`\`\`

The wrapper uses bounded Python subprocesses and a fully
reproducible output directory; all source bundles, destination CNFs,
selector maps, crash-safe journals, witness JSONL, validation logs,
seed/backend metadata, C++ binary hashes and summary comparisons
are preserved. Source modifications require fully audited migration
before reusing an older checkpoint. No automatic recurring search
or unbounded retry is scheduled.

The output's \`amortized-comparison.json\` is the primary index.
Its last-policy failure counts are qualitative diagnostics,
not certified feasibility or infeasibility conclusions.
