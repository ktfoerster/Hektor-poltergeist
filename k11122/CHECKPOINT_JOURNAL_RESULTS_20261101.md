# K11122 — crash-safe incremental journal: verified bounded experiment

Date: 1 November 2026. **Both target orbits remain UNKNOWN.**
No tested candidate has established positivity; no independently checked UNSAT
certificate exists for the original complete target/branch classification.
Established K11122 bounds remain 2–3 states.

## Authoritative run and evidence

- Tested implementation: commit \`7a1dc64c9fef849c239f1866388db56f40d63261\`
- Hosted run: https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41311372327
- Evidence artifact: https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41311372327/artifacts/13085089668
- Artifact ZIP SHA-256: \`869f0b36b014aac5a2cf4c7905a0da9b6034ddf18f938647a0cc522002ddf8db\`
- All **48 regression tests passed**, including 6 new journal-related cases
  covering byte-identical reconstruction, interrupted journal recovery,
  tampering, forged hashes, partial writes and owner lock. The unchanged
  \`verify.cpp\` was rebuilt. No complete full-mask routing replay was
  triggered because no finite-suite candidate was found.
- The ZIP passed its CRC test. **3,055** manifest-referenced actual files
  passed SHA-256 checks. The manifest also listed three empty
  \`.owner.lock\` coordination files which GitHub's default artifact upload
  excluded as hidden; these are not research evidence. The workflow is
  subsequently configured not to list these transient locks in future
  manifests. The reported ZIP digest itself matches GitHub's digest.

## Equal-budget controlled comparison

Both runs used target 0, physical-first-hop branch 0, exactly **2,701**
strict merged unconditional residual masks, \`python-sat==1.8.dev24\`,
CaDiCaL195, seed \`20261101\`, the same verified C++ witness generator
and independent Python clause checker, and a **35-second** end-to-end budget.

| Measurement | Full materialization each round | Incremental journal |
| --- | ---: | ---: |
| Raw SAT assignments | 916 | 1,553 |
| Newly learned independently checked clauses | 87,845 | 148,992 |
| Total output CNF clauses | 99,200 | 160,347 |
| Global selector variables | 4,736 | 4,736 |
| Checkpoint saves | 918 | 1,554 |
| Measured checkpoint-writing time | 15.932 s | 3.443 s |
| Solver time | 5.008 s | 7.975 s |
| Walk/certificate time | 9.732 s | 16.265 s |
| Peak reported maximum RSS | 81,056 KiB | 108,980 KiB |
| Complete frozen-suite passes | 0 | 0 |
| Finite-suite SAT candidates | 0 | 0 |
| Final scientific status | UNKNOWN | UNKNOWN |
| DIMACS SHA-256 | \`11d037cc6ad113eddccf12b3ad0114cdc4b7cc3237a423d6ac4b13673cdbc549\` | \`01cb01f48c3d13f03c9544a78330c51fbbb85b67fbffb3c454d50e26fc517607\` |

**Measured speedup:** 1,553/916 = **1.70× more SAT candidate
assignments** evaluated within the same search window. Approximately
78% less *total* time was spent on checkpointing despite 69% more
checkpoint events. The improvement does not imply the SAT solver itself
was faster; the two runs can follow different model trajectories and
produced different output formula sizes. Peak memory increased.
The exact CNF content was independently audited for both outputs.

## Additional target orbit

A separate 12-second journal pilot on target 3, branch 0, with the
strict **2,181-mask** unconditional union, examined **529 raw models**,
learned **50,701** independently checked necessary lasso clauses and
produced a **66,824-clause** final CNF with **6,240** global selectors.
CNF SHA-256:
\`14c1c15830bb06a2c4c74ae5295c2bc3329df21e01232b8f1816d85cba5abdef\`.
The independent audit passed. There were no finite-suite positive
candidates or certified negative results.

## Crash-recovery invariant and limitations

The journal appends witness proofs and matching clauses, fsyncs both
files, then atomically replaces a small metadata pointer and fsyncs
its directory. Independently checked recovery accepts **only**
committed byte prefixes; uncommitted suffixes after a simulated crash
are explicitly reported and never treated as constraints. Source hashes,
exact sorted frozen masks, selector mapping, branch, and per-clause
translation are checked. Cross-version migration remains an explicit
opt-in with full independent rechecking. The original full-snapshot
mode remains available as a control; the conventional DIMACS and manifest
are still emitted once at the end and independently rechecked.

No change to the packet model, graph, allowed port/bit actions,
branch-exhaustiveness argument or independent verifier has been made.
The journal preserves SAT constraints but not backend-internal solver
learned state. An UNSAT result without independently verified refutation
is never a graph-negative conclusion; a finite-suite SAT assignment
is never graph-positive without full exhaustive replay.

Reproduction commands and the journal correctness argument are in
[CHECKPOINT_JOURNAL.md](CHECKPOINT_JOURNAL.md). The next experiment should
measure strengthening clause selection/reducing redundant clauses or
proof-producing SAT; repeating this exact 35-second benchmark will not
advance the graph classification.
