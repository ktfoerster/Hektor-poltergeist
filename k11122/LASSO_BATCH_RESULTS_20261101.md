# K11122: accelerated lasso experiment — checked results, 1 November 2026

**Scientific status: UNKNOWN** for both target orbits; one-bit perfectly resilient
routing remains unresolved, with established bounds of 2–3 states. All four
original target/physical-first-hop branches remain unresolved. These experiments
do not constitute an impossibility certificate or a positive routing table.

## Provenance

- Tested commit: `a85dbb1ae0c582731ea0c61b2945a1205add0b31`
- Exact hosted run: https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41295146847
- Full reproducible artifact: https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41295146847/artifacts/13079175824
- Artifact ZIP SHA-256: `30b7b62a7404e2ab5e6b9ea9ce84d01afd83dec82bd0d537c9714b4c6d0aeb95`
- All 3,523 entries in artifact `SHA256SUMS` verified, with no mismatch;
  the ZIP CRC check also succeeded. The evidence includes compiled binary/source
  hashes, pinned solver dependencies, test logs, DIMACS, exact global selector
  mapping, sorted masks, every JSONL certificate and independent audit.
- **42 regression tests passed**, including differential C++/Python walks for
  random complete policies for both target orbits, the rank encoding comparison,
  shared source injection, successful source revisits, malformed policy/mask
  controls, and explicitly audited version migration.
- The unchanged `verify.cpp` was independently rebuilt. No complete
  finite-suite candidate survived to the stage requiring a new full 524,288-mask
  exhaustive C++ replay. This is not a positive verification.

## Frozen benchmarks and quantitative outcome

Cold comparison: exactly the same deterministic merged **2,701 target-0 masks**,
physical first-hop branch **0**, `python-sat==1.8.dev24`, CaDiCaL195,
seed **20261101**, and **45-second** end-to-end bounded search budget. The
Python and C++ approaches use the same selector variables and independently
audited lasso blocking clauses. The previous reference rank-CNF on these masks
had 1,277,670 variables and 4,871,885 clauses; it was not solved in this pilot.

| Measurement | Python cold | C++ cold |
| --- | ---: | ---: |
| Raw SAT assignments | 370 | 1,156 |
| Independently checked new lasso clauses | 35,475 | 110,880 |
| Variables | 4,736 | 4,736 |
| Clauses in final CNF | 46,830 | 122,235 |
| SAT worker wall seconds | 1.669 | 5.538 |
| Walk-processing wall seconds | 38.416 | 11.437 |
| C++ subprocess seconds (within walks) | 0 | 4.149 |
| Independent Python clause checks (within walks) | 2.732 | 3.754 |
| Full completed frozen-suite scans | 0 | 0 |
| Finite-suite candidates | 0 | 0 |
| Final status | UNKNOWN | UNKNOWN |
| External process RSS | 69,244 KiB | 138,664 KiB |
| Exact final CNF SHA-256 | `e732acb35bd9ea4801bc914cd5fe2914c05cc65b07e89c19f22eba0ad40aa2ac` | `3fd9922863ac09f25b406ab126f9ffa2d3b9a6bd2b5ff070d317cb4203caebe9` |

**Measured throughput:** 1,156 / 370 = **3.12 times as many SAT
assignments** per equal 45-second search window; 110,880 / 35,475 =
**3.13 times as many independently checked witness clauses**. The walk
processing itself was approximately **3.36 times faster**, including C++
process launches and independent Python clause checking. The peak memory
increase is material. These measurements are for one fixed branch, not a
general proof of superiority or a scientific classification result.

## Audited checkpoint continuation — target 0 branch 0

The previous independently audited artifact from run
[41293198280](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41293198280)
was downloaded by the workflow and checked again. It contained 61,248 unique
necessary lasso clauses with CNF SHA-256
`34792b5e850afc31b586604756a2ce3d4e60674b9b53eafff8e00eafb6cf1ba6`.

An explicit `--allow-audited-migration` rechecked every witness and the exact
old CNF from scratch, enforced the exact same graph, target, branch and masks,
and recorded prior source/formula/manifest digests. **61,248** clauses were
imported without importing any solver conclusion or learned SAT backend state.
The new C++ scanner independently checked and learned **76,128 further
clauses** in a separate bounded 45-second search, for **137,376 total**
reachable-failure clauses in that checkpoint. It examined 793 raw models;
no complete candidate emerged. Final CNF: **148,731 clauses**,
**4,736 variables**; exact SHA-256
`53757e919c8e8ce5c40aa2a2a969dc88072e0fd7d2268f9e6339e688ad2600eb`.
Status **UNKNOWN**, not UNSAT.

## Additional other-orbit pilot — target 3 branch 0

Using its own strict **2,181-mask** merged suite, with the same model,
seed, backend and bounded 45-second budget, the accelerated walker examined
**1,139 raw models**, learned **109,344** independently checked necessary
clauses, and produced a **125,467-clause** CNF with **6,240** global selectors.
The full CNF was independently audited, SHA-256
`adbfe7080a1b783acc62be2ac697d37d880bc49c2e6d2482c05e788e08c157c7`.
No finite-suite candidate was produced; status **UNKNOWN**.

## Scope and next measurable engineering step

The C++ miner is treated as an **untrusted witness generator**. Python
`lasso_witness.checked_clause` independently reconstructs the entire
reachable prefix from source injection and verifies the first full arrival
cycle, then yields a necessary blocking clause. The full emitted CNF is
independently reconstructed and audited at the end. C++ cannot certify SAT or
UNSAT; proof-producing SAT plus checked refutations would still be required
for negatives, and full unmodified C++ replay of both destination orbits for
positives.

The remaining 45-second cold C++ experiment spent about 5.5 seconds in SAT
slices and 11.4 seconds in walk processing. More time was spent elsewhere,
including repeated checkpoint export and bookkeeping. A promising next
experiment is to **instrument and reduce checkpoint-writing overhead without
compromising atomic recovery**, then measure on the same frozen suite and seed.
Do not infer an improvement merely from reduced file size or launch another
identical rank-based timeout.

Reproduce with the exact commands in [LASSO_BATCH.md](LASSO_BATCH.md), using
the pinned dependencies and the preserved run artifact. **No recurring
automation was created.**
