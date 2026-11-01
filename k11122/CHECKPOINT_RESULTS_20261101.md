# Measured checkpoint optimization — 1 November 2026

**Classification remains UNKNOWN for both destination orbits.** These are
bounded engineering measurements, not independently verified SAT or UNSAT.
No complete finite-suite candidate appeared in any of the six comparisons.
No full-size rank solving, exhaustive positive verification, or recurring job
was launched. The unchanged independent checker still reconstructs every
necessary lasso clause and the complete emitted CNF.

## Measurement design and results

Baseline: unmodified repository commit
`02f7acbfbab6bdbd71cfeb671c2c61aa621c03ff`. Improved: the source hashes in
`checkpoint_evidence_20261101/new-*.json`. The benchmark harness wraps functions
for timing without editing the baseline. Both variants use CaDiCaL195,
`python-sat==1.8.dev24`, seed 20261101, target 0, branch 0, 96 witnesses per
round, the identical C++ binary, and all 2,701 strictly merged frozen masks.

Three sequential pairs, **15 seconds of search per run**, in order old/new,
new/old, old/new. Search budgets include construction and ongoing checkpoints;
final publication and independent audit can overrun the deadline, as in the
original implementation. Their costs and total wall time are reported, not
hidden. This is a shorter bounded local comparison, **not a reproduction of
45-second GitHub runner throughput**. Timing varies with the host; three pairs
do not establish statistical confidence across machines or other branches.

| Pair | Original models | Improved models | Ratio | Original witnesses | Improved witnesses |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 454 | 727 | 1.60 | 43,488 | 69,696 |
| 2 | 388 | 690 | 1.78 | 37,152 | 66,144 |
| 3 | 462 | 756 | 1.64 | 44,352 | 72,480 |

Median model count: **454 → 727 (1.60×)**. Every baseline witness file is an
exact byte prefix of its paired improved witness file; counts and prefix
SHA-256 values are in `checkpoint_evidence_20261101/prefixes.json`. The stopping
boundary may interrupt the last model's scan, explaining nonmultiples of 96.
All six final CNFs and every stored witness passed independent audit.

| Measured wall seconds (range across runs) | Original | Improved |
| --- | ---: | ---: |
| Snapshot export including hashing | 5.184–5.759 | 0.069–0.099 |
| Hashing within snapshot export | 4.299–4.929 | 0.060–0.086 |
| CNF and manifest writes within export | not separately instrumented | 0.006–0.011 |
| Copy, fsync, directory/pointer publication outside export | absent | 0.194–0.268 |
| Complete checkpoint cost including publication | 5.184–5.759 | 0.265–0.368 |
| Lightweight progress writes | absent | 0.240–0.269 |
| Policy validation and writing (common wrapper) | 1.700–1.783 | 2.575–2.788 |
| SAT worker wall time | 2.471–2.838 | 3.410–3.784 |
| Witness/walk processing, including independent clause checks | 4.838–5.462 | 8.050–8.294 |
| Final independent audit, outside search window | 1.437–1.843 | 2.535–4.181 |
| Total run including final publication, shutdown and audit | 16.489–16.917 | 17.723–19.433 |
| Complete checkpoint count | 389–464 | 4 |

Rows overlap where explicitly stated; do not sum the whole table. Improved
nonoverlapping `other_seconds` is 0.040–0.055 s. More solver/witness/audit time
reflects more useful work, not faster individual checks. End-to-end throughput
including audit also improved in these pairs, but the total run durations are
**not identical**. Most baseline export cost was hashing; the remaining cost
includes file writes, copying and serialization, not pure disk I/O. We did not
label all unaccounted baseline time as checkpoint work.

A preliminary cProfile run (10-second search, profiling overhead enabled) also
identified policy validation/writing and final audit as material costs. It is
diagnostic only, not included in the throughput comparison.

## Recovery contract

`--checkpoint-seconds 5` is the default. `0` publishes after each processed
round (it is not the old implementation, which lacked generation durability).
A complete initial checkpoint and a complete final checkpoint are mandatory.

- Mutable solver outputs, CNF body, witness log, policies and scanner logs live
  in `.working`. They are **never** recovery inputs.
- A checkpoint copies all certificate inputs and scanner provenance into a
  private `checkpoints/NNNNNN.tmp` directory, exports and fingerprints the
  complete CNF, and hashes all certificate files into its manifest.
- Files and the staging directory are fsynced. The directory is renamed to its
  immutable generation name; its parent is fsynced. A relative `current`
  symlink is then atomically replaced and the output directory is fsynced.
  Root-level compatibility aliases refer through `current`.
- Audit and resume resolve `current` **once**, pinning one complete generation.
  They also accept the previous flat checkpoint format. They ignore staging,
  working files and `progress.json`. Existing generations are retained, so a
  pinned reader cannot race with deletion.
- `progress.json` is small, atomically replaced, advisory, and deliberately not
  fsynced each round. It can describe more work than the committed generation.
  It cannot authorize any solver conclusion or supply imported clauses.
- An interruption before pointer publication recovers the prior generation;
  after publication it recovers the new complete generation. A corrupt current
  generation fails closed; there is no silent fallback. An older generation
  can be explicitly audited and selected with `--resume path/checkpoints/NNNNNN`.
- Recovery may discard work since the last committed snapshot. The interval is
  checked at round boundaries (and every five inconclusive solver slices),
  **not a hard maximum loss duration**. First publication must finish before
  any recoverable checkpoint exists. No SAT backend memory is restored.
- POSIX symlink/rename/fsync semantics and a filesystem honoring fsync are
  required. Failure injection and SIGKILL test process interruption; they do
  not simulate physical power loss or establish network-filesystem guarantees.
  The final version additionally fsyncs the newly created output's parent
  before search starts. This post-benchmark durability correction is outside
  the search timer; exact pre-correction benchmark source is in the archive.

Every committed learned clause retains its full source injection, reachability
prefix, cycle, mask and independent translation. Scanner batch reports, source
and binary hashes, frozen masks, seeds and imported checkpoint hashes remain.
Resume re-audits the entire prior CNF and every witness, enforces model/branch/
suite equality, and requires explicit `--allow-audited-migration` for changed
source hashes. The independent auditor has no dependency on the checkpoint
writer or solver: its only change is resolving and pinning `current`.

Tradeoff: retaining all generations uses more disk space. These short runs
used about 74–82 MiB each including working files, versus 23–27 MiB for the
original. Archive committed generations and source, or explicitly select one
complete generation; do not copy individually changing root aliases during a
live run. This implementation prioritizes simple recovery and concurrent
read safety over pruning or a more complex incremental journal.

## Timing interpretation

`summary.json` contains completed timings. A generation manifest contains
progress as of its export, so it cannot include its own final publication or
later audit duration. The advisory progress record includes publication costs
up to its write. Neither is a substitute for certificate audit.

Nonoverlapping search buckets: `construction_seconds`, `resume_seconds`,
`solver_seconds`, `replay_seconds`, `policy_seconds`,
`checkpoint_total_seconds`, `progress_seconds`, `independent_replay_seconds`,
and residual `other_seconds`. Resume includes its initial audit.
`audit_seconds` includes resume audit (if any) and final audit, so it overlaps
resume. `snapshot_export_seconds`, `checkpoint_hash_seconds`,
`checkpoint_write_seconds` and `checkpoint_publish_seconds` describe nested
checkpoint phases. `batch_cpp_seconds` and `batch_python_check_seconds` are
nested inside `replay_seconds`. Policy timing includes solver-row validation
and TSV writing. Witness processing includes scanner launch, parsing, checking,
clause addition, deduplication and certificate serialization. Hash costs outside
checkpoint export remain in their owning phase; audit hashes are audit costs.

## Correctness evidence and reproduction

`python -m unittest discover -s k11122 -v`: **48 tests passed**. Six new test
methods cover advisory/uncommitted corruption, immutable generations and live
continuation, failures during copy/export/fsync/rename/pointer publication and
after the commit point, committed corruption and rehashed semantic tampering,
a real SIGKILL immediately before pointer replacement followed by audited
continuation, and invalid checkpoint intervals. Existing tests retain both
orbit differential walks, literal-versus-rank checks and explicit source
migration. No scientific status is upgraded by a timing result.

A separate five-second audited migration imported **43,488** baseline witness
clauses and added **6,624** newly checked clauses. Both the old and the new
full CNFs passed independent audit. Its status remained UNKNOWN, with zero
finite-suite candidates. The search budget included 3.497 seconds of initial
audit and reconstruction; total wall time including final audit was 6.967
seconds. The summary, audit and migration manifest are preserved alongside
the six comparison reports.

```sh
python -m pip install python-sat==1.8.dev24 z3-solver==4.13.3.0
git worktree add --detach ../lasso-baseline 02f7acbfbab6bdbd71cfeb671c2c61aa621c03ff
g++ -std=c++17 -O3 -Wall -Wextra -Werror k11122/lasso_batch.cpp -o /tmp/lasso-batch
python -m unittest discover -s k11122 -v
# Use distinct output directories. Repeat in old/new, new/old, old/new order.
python k11122/benchmark_checkpoints.py --source ../lasso-baseline \
  --output /tmp/old-1 --binary /tmp/lasso-batch --seconds 15
python k11122/benchmark_checkpoints.py --source . \
  --output /tmp/new-1 --binary /tmp/lasso-batch --seconds 15 --interval 5
python k11122/lasso_search.py audit --output /tmp/new-1
# Audited source migration; budget includes prior audit and clause import.
python k11122/lasso_search.py run --target 0 --branch 0 --seconds 5 \
  --walker cpp --batch-binary /tmp/lasso-batch --resume /tmp/old-1 \
  --allow-audited-migration --output /tmp/migrated
```

The six compact reports preserve exact source/binary/mask/CNF/witness hashes,
Python/platform/dependency versions, raw timers, and audit results. The separate
compressed evidence archive preserves complete final certificates, intermediate
committed generations, matching benchmark source, and test output. These data
are measurements from this local environment, not a GitHub Actions run.
