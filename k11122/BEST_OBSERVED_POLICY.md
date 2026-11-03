# K11122 — independently replayed best-observed policy tracking

**Status:** Both destination orbits on \`K_{1,1,1,2,2}\` remain UNKNOWN
under the one-bit routing model. A historical raw SAT assignment is **not**
a successful policy for the terminal learned CNF, and neither shorter
clauses nor improved quality on a frozen residual suite constitutes
a graph-positive result.

## Why this experiment

Recent paired experiments found differences in the **last** raw SAT
policy's failure counts. This was not monotonic progress: the SAT
solver may generate a better raw policy earlier and then move to
another invalid policy as new necessary clauses are learned.

To assess meaningful progress without changing the policy space, this
work optionally scores complete raw SAT assignments against *every*
connected nonself source on the **same strictly frozen residual masks**,
and preserves the best observed historical table with exact provenance.
A deterministic scoring interval makes the overhead explicit:
\`--best-interval 1\` evaluates **every raw SAT assignment**;
\`--best-interval N\` samples model 1 and each Nth model,
so the result is only the **best among sampled assignments**.
\`--best-interval 0\` (default) disables the feature, preserving
all original search behavior.

## Mechanism and independent checking

The \`lasso_quality.cpp\` tool uses the existing C++ source-reachable
first-repeated-complete-arrival walk semantics to count:

1. All connected nonself-source obligations in the frozen suite;
2. Connected sources for which the raw policy loops indefinitely; and
3. Residual failure masks for which at least one connected source loops.

It is **an untrusted ranking aid**, not a replacement for the independent
exhaustive \`verify.cpp\`. The parent checks its graph, target, mask and
obligation accounting and ranks policies lexicographically by
\`(failed_residual_masks, failed_connected_sources, policy SHA-256)\`.
It copies the best historical candidate to an atomically published
\`best-policy.tsv\` with matching \`best-policy.json\`,
\`quality-samples.jsonl\`, exact mask-domain hash, scanner binary
hash, source-model index and sampling period.

The **independent Python** \`lasso_best.independently_check_best\`
verifies those hashes and decodes the entire chosen policy without
using the C++ scorer or the SAT encoding. It rebuilds the original
graph independently and simulates every connected source on every
frozen mask to reproduce the complete failure counts. A mismatch,
truncated policy, changed mask family or incomplete atomic pair
causes failure. Every successful hosted output also passes
\`lasso_witness.audit\` of the entire final CNF and all necessary
source-reachable lasso witnesses. Thus even if the C++ ranking aid
were erroneous, no unverified best score is accepted.

**Critical distinction:** the best policy is a *historical raw SAT
assignment to a preceding learned CNF*, not necessarily an assignment
satisfying the terminal CNF after new clauses. It cannot be submitted
as a positive policy without full unchanged C++ replay on all
**524,288 residual masks** for both destination orbits and every
connected nonself source. Likewise, solver exhaustion without an
independently checked refutation of both exhaustive branches of at
least one orbit proves no impossibility.

## Recovery and scope

The optional diagnostic does **not** change selector variables,
routing actions, packet memory, branch assertions, the SAT worker,
or which sound failing-walk clauses are learned. It is timed within
the active search budget as \`quality_sampling_seconds\`; any raw
model lost to this overhead is reported, not concealed.

The checkpoint journal continues to govern *only necessary SAT
clauses*. The best observed historical table and scoring history
are diagnostic artifacts. Atomic policy and metadata writes avoid
partly written records on interruption. On reopening or after a
crash, a diagnostic must pass independent Python replay; the
current run never inherits or trusts best scores from an old
checkpoint without recomputation. Immutable-generation checkpoints
also copy these files into the published generation, and both
journal and generation implementations are tested.

## Reproducible benchmark

The new hosted workflow runs the same-process certified transfer
cache with paired *uncached full-audit* versus *cached same-process*
opposite-first-hop constraints. It creates the target-0 **2,701**
and target-3 **2,181** strict unconditional mask families, and uses
three deterministic target-0 seeds 20261103, 20261104 and 20261105,
plus one target-3 control seed. Each target-0 condition receives
10 seconds of active SAT/walk/search budget, and target 3 receives
7 seconds, with identical hybrid selection, policy domain and
shared seed in each pair. The diagnostic samples model 1 and every
16th raw SAT assignment. The last raw assignment is scored separately.

Paired comparison records best-observed and last failing masks,
failed connected-source obligations, selected model index, per-run
sampling overhead, independent best replay, raw model counts,
solver effort, source audit/caching preparation, and full CNF hashes.
These few seeds are **descriptive**, not statistically convincing
evidence for convergence, and the benchmark is not a 1-bit theorem.

### Commands

On Ubuntu 24.04 with Python 3.12:

\`\`\`sh
python -m pip install python-sat==1.8.dev24 z3-solver==4.13.3.0
python -m unittest discover -s k11122 -p 'test_*.py' -v
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_batch.cpp -o lasso_batch
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_quality.cpp -o lasso_quality
g++ -O3 -std=c++17 k11122/verify.cpp -o verify
python k11122/lasso_search.py run --target 0 --branch 0 --seconds 30 \
  --walker cpp --batch-binary "$PWD/lasso_batch" \
  --best-interval 16 --quality-binary "$PWD/lasso_quality" \
  --verify "$PWD/verify" --witness-selection hybrid \
  --checkpoint-mode journal --output evidence-best-t0
python k11122/lasso_search.py audit --output evidence-best-t0
python k11122/session_cache_benchmark.py --output matched-best-study \
  --scanner "$PWD/lasso_batch" --quality-binary "$PWD/lasso_quality" \
  --best-interval 16 --verifier "$PWD/verify" --source-seconds 9 \
  --search-seconds 10 --target3-seconds 7 \
  --seeds 20261103,20261104,20261105
\`\`\`

The workflow has a hard 14-minute cap. It preserves complete source,
compiled binary hashes, exact masks, recovered journals, independently
replayed best tables, seed/backend identifiers, final CNFs and witness
certificates. No recurring automation, new cloud account, or unbounded
compute is introduced.
