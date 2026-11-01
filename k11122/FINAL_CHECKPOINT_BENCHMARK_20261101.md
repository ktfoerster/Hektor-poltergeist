# Final checkpoint validation — 1 November 2026

Scientific status: **UNKNOWN for both destination orbits**. The following is
engineering evidence, not independently verified SAT or UNSAT.

## Exact comparison

Original commit: `02f7acbfbab6bdbd71cfeb671c2c61aa621c03ff`.
Final implementation: `94ac8e3cfa5d1ec57d11ab5e05b90ccd478b0925`.
A clean checkout of the final commit passed all **54 regression tests** before
benchmarking. There were no runtime source edits during or after measurement.
The initial evidence commit adds reports only. A later conflict resolution
preserves this measured engine as described below; the public default follows
the newer journal implementation on main.

Six sequential local runs, ordered old-1/new-1/new-2/old-2/old-3/new-3,
used identical 2,701 frozen target-0 masks, branch 0, seed 20261101,
CaDiCaL195 (`python-sat==1.8.dev24`), the same compiled C++ walker, and 96
new witnesses per round. Each received a **45-second search budget**.
Final publication and independent audit are included separately in total wall
time, as in the previous harness. No rank-based full-size experiment was run.
Shared-host scheduling was not isolated; three pairs do not establish a
universal speedup. Exact source, binary, mask, CNF and witness hashes and raw
nested timers are in `checkpoint_evidence_final_20261101/comparison.json`.

| Pair | Original assignments | Improved assignments | Search-window ratio | Original witnesses | Improved witnesses | Ratio including total wall time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1,013 | 2,158 | 2.13 | 97,152 | 207,072 | 1.97 |
| 2 | 1,059 | 2,282 | 2.15 | 101,664 | 218,976 | 1.99 |
| 3 | 1,041 | 2,025 | 1.95 | 99,840 | 194,331 | 1.83 |

The final ratio column compares assignments per second using each run's actual
total wall time, including final audit. It does not imply equal total run time.
Every baseline witness file is an exact byte prefix of its paired improved
file; counts and prefix SHA-256 values are recorded in `comparison.json`.
All six complete CNFs and every witness passed independent reconstruction.
All six runs returned UNKNOWN with zero finite-suite candidates.

| Metric across the three runs | Original | Improved |
| --- | ---: | ---: |
| Complete checkpoint wall seconds | 22.711–23.983 | 0.873–0.931 |
| Hashing inside checkpoint export, seconds | 20.406–21.509 | 0.406–0.452 |
| Final independent audit, seconds | 3.508–3.635 | 6.591–7.370 |
| Total wall seconds | 48.674–48.752 | 51.845–52.706 |
| All retained run data, MiB | 56.4–59.0 | 391.4–431.2 |
| Final certificate alone, MiB | 26.6–27.9 | 53.9–60.9 |

Checkpoint and hashing rows overlap. The improved checkpoint metric includes
copying, fsync and publication. The old implementation did not provide this
whole-generation durability. Higher final audit cost reflects roughly twice
as many independently checked witnesses. Timing definitions from
`CHECKPOINT_RESULTS_20261101.md` still apply; do not sum nested fields.

## Review and acceptance

The measured search and end-to-end throughput gains justify the change for
bounded searches. The independent checker still reconstructs every clause,
checks exact DIMACS bytes, counts and hashes, and rejects corrupted/incomplete
manifests. Tests cover source migration, a pinned audit during publication,
rehashed tampering, and real SIGKILL before pointer replacement, after
replacement, and after directory fsync, each followed by audited continuation.
Solver memory is not restored, and no metadata status bypasses certification.

The material tradeoff is storage: retaining all generations makes total run
storage about seven times larger in this comparison. The separately preserved
benchmark archive contains each complete **final** certificate and its full
witness/scanner provenance, not redundant intermediate generations or advisory
working files. This does not change measured on-disk usage. Generation pruning
is not implemented and must not race pinned readers. Account for disk growth
before longer campaigns; this result is not authorization for unbounded runs.

POSIX symlink/rename/fsync support is required. Recovery uses the most recently
committed generation and can discard later uncommitted work. The interval is
checked at search boundaries, not a hard recovery-point deadline. For physical
power-loss durability, the output's parent hierarchy must already be durable;
the writer fsyncs the immediate parent, not arbitrary newly created ancestors.
The regression suite tests process crashes, not physical power loss.

The final code review and bounded comparison found no remaining blocker within
these documented assumptions. The unchanged raw source at the tested commit is
the code proposed for merge. Both destination-orbit classifications remain UNKNOWN.

## Reproduce

```sh
python -m pip install python-sat==1.8.dev24 z3-solver==4.13.3.0
git worktree add --detach ../lasso-baseline 02f7acbfbab6bdbd71cfeb671c2c61aa621c03ff
git worktree add --detach ../lasso-final 94ac8e3cfa5d1ec57d11ab5e05b90ccd478b0925
cd ../lasso-final
g++ -std=c++17 -O3 -Wall -Wextra -Werror k11122/lasso_batch.cpp -o /tmp/lasso-final-batch
python -m unittest discover -s k11122 -v
python k11122/benchmark_checkpoints.py --source ../lasso-baseline \
  --output /tmp/old-1 --binary /tmp/lasso-final-batch --seconds 45
python k11122/benchmark_checkpoints.py --source . \
  --output /tmp/new-1 --binary /tmp/lasso-final-batch --seconds 45 --interval 5
# Repeat with unique output paths in new/old and old/new order.
# On the unpacked evidence archive, audit any flat complete certificate:
python k11122/lasso_search.py audit --output runs/new-1
```

The archive's `SHA256.json` indexes every bundled report and certificate file.
Run the independent audit as well as checking hashes: hashes alone do not prove
correct witness translation or any mathematical classification.


## Integration with the newer main branch

Main advanced independently to `d76c82fc3b55a7d0b1e5e382d481335a1a426390`
while this PR was being benchmarked. It added a separately tested incremental
journal (`lasso_journal.py`) and made journal mode the public default. The first
merge attempt correctly stopped on a conflict in `lasso_search.py`; none of that
newer work was overwritten.

Resolution preserves the journal/default and legacy full modes, all upstream
journal tests, workflow and reports. The periodic-generation engine is retained
as `lasso_generation_search.py` and selected by the public entry point using
`--checkpoint-mode generations`. Its search/checkpoint implementation is textually
identical to the measured commit apart from adding its new filename to the
source-hash dependencies and an explicit mode label in progress. The shared
independent auditor retains streaming and stricter integrity checks. Public
resume pins generation inputs before auditing/importing, including when the
output engine is journal mode. Cross-engine continuation requires explicit
source migration and independent re-audit.

**The 1.95–2.15× result compares generations with the original per-round full
exporter, not with the newer journal default.** No performance ranking between
generations and journal is claimed. The journal remains default because this
integration must preserve newer behavior and its per-round committed prefixes;
generations remains an explicit alternative with greater retained disk usage.

Current commands after merge:

```sh
# Existing journal default remains available unchanged as a choice:
python k11122/lasso_search.py run --output journal --seconds 30 --walker cpp --batch-binary /tmp/lasso-final-batch
# Select the separately measured periodic-generation engine:
python k11122/lasso_search.py run --output generations --seconds 30 --walker cpp --batch-binary /tmp/lasso-final-batch --checkpoint-mode generations --checkpoint-seconds 5
# The harness can select the generation engine explicitly on the merged tree:
python k11122/benchmark_checkpoints.py --source . --module lasso_generation_search --output /tmp/generation-bench --binary /tmp/lasso-final-batch --seconds 45 --interval 5
```

The resolved tree passed **61 tests**, including all upstream journal tests and
new public-dispatch/default-mode and bidirectional cross-engine continuation
checks (`integration-tests.log`). A five-second generation-mode integration
smoke run independently audited 25,824 new witnesses; every witness matched the
exact prefix of the earlier measured run (`integration-smoke.json`). This is
integration validation, not a new comparative throughput result.

## Merge and bounded continuation

PR #1 merged as `8ad0d711911c5b2f49115b96d7ed3c80704bcef9`, after resolving
main's independent journal development and passing the combined 61-test suite.
The merged tree exactly matches the tested integration tree.

A separate **30-second** continuation used a clean checkout of that merge,
the journal default, target 0 branch 0, and the same frozen suite, seed,
96-witness cap and C++ binary. It explicitly re-audited and migrated `new-2`'s
218,976 inherited witnesses into the journal engine. It then checked **44,448
new witnesses** from 464 raw assignments. The final complete certificate has
**263,424 witnesses, 274,779 clauses and 4,736 variables**. Both its full
independent certificate audit and committed-journal check passed.

Final CNF SHA-256:
`595db794a86c6ca9dfc3b8b9e86ef9cee2518c78eb99db5c172c7464fac46f99`.
Total subprocess wall time, including initialization, imported-certificate
audit/reconstruction, final export and final audit: **43.911 seconds**.
The 30-second search budget includes initial re-audit/import; it is not a
30-second fresh search or a strict total-process deadline. Reported peak RSS
was 224,132 KiB. This is an audited continuation, not another throughput pair.
No complete finite-suite candidate appeared; the exhaustive positive verifier
was available but never needed. Status remains **UNKNOWN for both orbits**.

The evidence archive preserves all six complete final benchmark certificates,
the continuation and its committed journal/body, reports, input masks,
canonical witnesses and hashed scanner logs. Parent manifest and formula hashes
in the continuation link back to its bundled `new-2` checkpoint. A `SHA256.json`
index covers archive contents. Redundant intermediate generations and
uncommitted working files are omitted; measured disk totals include them.

Preserved evidence file: `K11122_Final_Checkpoint_Benchmark_2026-11-01.tar.gz`
(71,792,839 bytes), archive SHA-256
`ec88d59d29defc5beb412b98fb3affbfd8321e975a30d33c817b22c59073f7d2`.
All 87 indexed file hashes were verified by reading the completed archive.
