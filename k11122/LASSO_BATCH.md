# Accelerated, independently checked lasso discovery (1 November 2026)

The first rank-free pilot (run 41293198280, target 0 branch 0, all 2,701
merged unconditional masks) spent 61.49 s in Python finite-suite walk replay
versus 2.79 s in SAT solving. This change targets only that measured bottleneck.
It does **not** modify the reference Boolean/rank encoding, the graph, global
routing semantics, or the unchanged independent `verify.cpp` exhaustive checker.

## Soundness and trust boundaries

`lasso_batch.cpp` is an UNTRUSTED candidate-witness generator. It reads an
entire legal normalized routing policy and a strictly increasing explicit
residual-mask list. It traverses only connected nonself sources, beginning
with the shared source injection, and records the first repeated **full**
(vertex, incoming port, packet bit) arrival configuration. Source revisits
and unreachable cycles are permitted. For each failing residual it considers
the first failing source; globally it keeps up to `MAX_WITNESSES` distinct
sets of chosen local selectors. It records the full source-injection,
reachability prefix, and closing loop. Selecting only a subset of witnessed
failures is safe: each observed failure produces a necessary clause.

Each C++-generated witness is independently reconstructed and translated by
`lasso_witness.checked_clause`, which imports no C++ or solver code. A conflict
with an existing clause aborts, rather than silently discarding disagreement.
If the C++ tool reports a full scan with *no* failures, the separate Python
walker independently replays **every** frozen mask and connected source before
accepting finite-suite SAT. The unchanged `verify.cpp` alone can confirm
positive delivery on ALL 524,288 masks and the exact connected-source obligation
count for one orbit. Both orbit positives are needed for the graph.

C++ unique-witness deduplication is by sorted `(vertex, local live mask,
incoming port, packet bit, selected action)` tuples, not by vertex or
unreachable cycle. It never removes or freezes any global routing option.
The source/transit observation table remains the same shared one-hot table.

An `UNSAT_UNCERTIFIED` from PySAT still cannot prove nonexistence. A negative
needs an independent refutation of the fully audited emitted CNF and both
exhaustive first-hop branches of at least one destination orbit. Every CNF
and witness is audited on completion; solver timeouts are `UNKNOWN`.

## Checkpoints and explicit migration

Full suites are constructed by `merge_checkpoints.merge`, which validates both
source branches, file SHA-256, schema, target and model before merging only
unconditional residual masks. Snapshots contain the actual CNF, source version
hashes (including the C++ generator), canonical witnesses, input masks,
solver and scanner seeds, emitted policy, and hashed batch logs. Hashes of
C++ binary, source, frozen masks and parent commit are preserved.

By default, resumption requires the exact source-hash dictionary. A reviewed
version change can be resumed only with `--allow-audited-migration`. This
option first independently rechecks **all old** witness clauses, selector
numbering, branch clause, DIMACS byte content, hashes and the exact same
residual-mask suite. It records both original manifest and CNF hashes and old
source hashes before importing clauses. There is no solver-memory restoration,
no claim that the entire old SAT search state is retained, and no unverified
source substitution.

The old run 41293198280 artifact (ID 13078265845) contains 61,248 such
witnesses. The new workflow retrieves it in order to try an explicitly
re-audited continuation. It does not write old large artifacts to GitHub.

## Local commands

```sh
python -m pip install python-sat==1.8.dev24 z3-solver==4.13.3.0
g++ -std=c++17 -O3 -Wall -Wextra -Werror k11122/lasso_batch.cpp -o lasso_batch
g++ -std=c++17 -O3 k11122/verify.cpp -o verify
python -m unittest discover -s k11122 -v
python k11122/merge_checkpoints.py --target 0 --output frozen-t0.json
python k11122/lasso_search.py run --target 0 --branch 0 --seconds 45 \
  --walker python --verify "$PWD/verify" --output python-cold
python k11122/lasso_search.py run --target 0 --branch 0 --seconds 45 \
  --walker cpp --batch-binary "$PWD/lasso_batch" --verify "$PWD/verify" \
  --output cpp-cold
python k11122/lasso_search.py audit --output cpp-cold
# Optional, after downloading and independently auditing the prior artifact:
python k11122/lasso_search.py run --target 0 --branch 0 --seconds 45 \
  --walker cpp --batch-binary "$PWD/lasso_batch" --verify "$PWD/verify" \
  --resume /path/to/old-artifact/lasso --allow-audited-migration \
  --output cpp-migrated
```

The hosted comparison uses identical frozen suites and seeds for the two
**cold** walker variants and records wall, solve, walk, audit and construction
costs separately. Differences in model trajectories are not guarantees of
reproducible search speedups on other cases. The migration and target-3
experiments are separate, not mixed into the cold comparison. The workflow
is bounded, single-job, and nonrecurring; the run artifact contains all
source, test output, CNF/witness records and hashes.

The classification remains **UNKNOWN for both destination orbits** until
independently verified proofs or fully resilient policies exist.

## Checkpoint overhead measurements and recovery update

See [CHECKPOINT_RESULTS_20261101.md](CHECKPOINT_RESULTS_20261101.md) for the
bounded original/improved comparison, timing definitions, crash tests and
recovery contract. Complete snapshots now default to five-second intervals,
with lightweight advisory progress between them; `--checkpoint-seconds 0`
publishes each round. Audit/resume pin the atomically published `current`
generation. Working/staging files and progress records never authorize resume.
