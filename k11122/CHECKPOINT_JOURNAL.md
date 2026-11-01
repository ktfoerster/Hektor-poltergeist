# Incremental crash-safe K11122 lasso checkpoints — 1 November 2026

Both target orbits remain **UNKNOWN**. This work changes only checkpoint I/O,
not routing semantics, target orbits, first-hop branch coverage, SAT selectors
or the unchanged independent exhaustive C++ verifier.

## Atomic journal and sound recovery

The rank-free learner retains global one-hot selectors and necessary clauses
from entire reachable failure walks (injection, prefix, first repeated full
incoming-port/packet-bit state). These clauses do not impose success at
arbitrary arrivals or forbid unreachable cycles.

In new default \`--checkpoint-mode journal\`, every batch appends the checked
witness JSON lines and their exact SAT clauses. The two files are **fsynced**
before \`journal.json\` is atomically replaced and its containing directory
fsynced. The journal records byte boundaries, incremental SHA-256 digests,
variable/clause/witness counts, exact frozen mask and selector hashes, source
dependency hashes, branch, seed, backend and progress. An exclusive nonblocking
local lock prevents competing writers. No checkpoint restores internal SAT
learned clauses or assumes continuous computation.

A torn final append can leave extra bytes after the last atomic journal
pointer. \`lasso_journal.check_committed\` independently reconstructs every
committed base clause, branch clause and witness clause, byte for byte, and
rejects any corrupted committed prefix even if its digest has been recomputed.
It reports uncommitted suffix bytes explicitly. Resume from a journal-only
interruption uses only the validated committed prefix in a NEW output directory
and records parent hashes, provenance and discarded trailing-byte counts.
Cross-version import requires explicit \`--allow-audited-migration\`, which
still independently checks every source-reachable failure clause. The old
\`--checkpoint-mode full\` is retained for an equal-budget control.

At normal termination the code exports one complete DIMACS and manifest,
runs the existing independent \`lasso_witness.audit\`, and preserves the
journal body as independently recoverable evidence. The old full-snapshot mode
continues to produce the previous conventional artifact.

## Tests and controlled benchmark

The new tests exercise exact prefix reconstruction, uncommitted trailing
bytes, corruption with forged SHA-256, truncated committed lines, empty
journals, nonblocking locking, and an actual solver-backed journal-only crash
recovery. Full regression tests still compare the reference rank encoding,
independent source-reaching literal walks, both target orbits, C++ vs Python
walk generation, shared injection, connected/disconnected cases, and
first-hop partitions.

The GitHub-hosted workflow runs exactly one **35-second** target-0, branch-0
search with full snapshots and one **35-second** journal search on the same
frozen **2,701** masks, solver seed/backend and C++ walker. It also runs one
short target-3 check on its strict **2,181** masks. Measurements of checkpoint
I/O, raw SAT assignments, checked clauses, solve/walk time, peak memory and
formula counts are preserved as downloadable, hashed Actions evidence. Lower
checkpoint I/O alone does **not** prove a research speedup or existence/nonexistence
of a resilient policy.

## Reproduction

\`\`\`bash
python -m pip install python-sat==1.8.dev24 z3-solver==4.13.3.0
python -m unittest discover -s k11122 -p 'test_*.py' -v
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_batch.cpp -o lasso_batch
g++ -O3 -std=c++17 k11122/verify.cpp -o verify
python k11122/lasso_search.py run --target 0 --branch 0 --walker cpp \
    --batch-binary "$PWD/lasso_batch" --verify "$PWD/verify" \
    --seconds 35 --checkpoint-mode journal --output journal-output
python k11122/lasso_search.py audit --output journal-output
# If the original was interrupted before the conventional final export:
python k11122/lasso_search.py run --target 0 --branch 0 --walker cpp \
    --batch-binary "$PWD/lasso_batch" --seconds 35 \
    --resume interrupted-journal-only-dir --output new-output
\`\`\`

All output paths must be new. Negative claims require an independently
checked complete refutation of both exhaustive branches of one orbit;
a positive requires the independent unchanged full replay for both orbits.
