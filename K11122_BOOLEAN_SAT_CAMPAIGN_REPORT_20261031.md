# K11122 one-bit routing: Boolean-SAT campaign report

Date: 31 October 2026

## Result

The one-bit question remains unresolved for both destination orbits. No branch
produced an exhaustively valid policy, and no independently checked negative
certificate was produced. The established 2–3-state bounds are unchanged.

The campaign nevertheless made verified computational progress. Commit
[`bf2e497`](https://github.com/ktfoerster/Hektor-poltergeist/commit/bf2e497771e56119c21465db880a385fd108eeed)
adds the Boolean CNF/CaDiCaL backend, differential tests, wall-clock-bounded
owned solver processes, deterministic formula fingerprints, and documentation.
The single push-triggered four-job matrix is
[`41164233786`](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41164233786).

## Hosted results

Every job used `python-sat==1.8.dev24/Cadical195`, seed `20261031`, a 1,200
second total search budget, and the same merged residual input as the preceding
SMT run. Each SAT model was a complete legal table and was replayed by the
unchanged C++ checker before its counterexamples were added.

| Target | Branch | SAT candidates | Input masks | Final branch masks | Final vars | Final clauses | Final candidate failures |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 13 | 1,221 | 1,429 | 578,500 | 2,137,585 | 210,118 / 2,979,236 obligations |
| 0 | 1 | 16 | 1,221 | 1,477 | 590,148 | 2,174,371 | 221,568 / 2,979,236 obligations |
| 3 | 0 | 11 | 1,027 | 1,203 | 637,032 | 2,450,637 | 272,632 / 2,937,186 obligations |
| 3 | 1 | 13 | 1,027 | 1,235 | 655,138 | 2,521,793 | 291,926 / 2,937,186 obligations |

All four jobs ended `UNKNOWN` after a final bounded timeout. Across them,
CaDiCaL returned 53 candidate policies. Every candidate failed exhaustive
replay, and each failure contributed 16 previously unenforced residuals to its
branch formula. The branch unions contain 1,541 masks for target 0 and 1,325
masks for target 3: 320 and 298 new unique unconditional residuals,
respectively, beyond the prior merged inputs.

This is a material improvement over run 41160956866: the earlier integer-rank
Z3 baseline made five solver attempts per branch but returned no SAT candidate
and learned no new residual mask. The comparison is an observed search outcome,
not a claim that clause count alone proves a general speedup.

## Independent checks

- All 14 hosted tests passed in every matrix job. The tests include the
  exhaustive 64-policy triangle comparison among CNF, SMT, and literal walks;
  exact-one selectors; all guarded three-bit comparator boundaries; common
  injection; disconnected cases; both target orbits; transient source revisits;
  unreachable loops; both emitted bits in the branch partition; corruption
  controls; and malformed-policy rejection.
- All four artifact ZIP SHA-256 digests match GitHub's recorded digests; all
  ZIP CRC tests and every internal `SHA256.json` entry pass.
- `verify.cpp` was independently recompiled after download. Replaying the four
  final tables reproduced exactly 524,288 masks and the expected 2,979,236
  target-0 or 2,937,186 target-3 connected-source obligations, including the
  failure counts in the table.
- The two branches use the same resume hash within each orbit. Their partition
  rows are identical within the orbit, disjoint by physical next hop, and keep
  both emitted bits.

The final formula SHA-256 fingerprints are:

| Target | Branch | Formula SHA-256 |
|---:|---:|---|
| 0 | 0 | `6e480e133d50671e8b3a3a1c7d0f3a0133b081cb65695e3cdd147a67f1c288cb` |
| 0 | 1 | `0ab6d7a94c0d7c7a8fba3a881e2225d4ddb4f58a20a54a7efc699bd5262dc693` |
| 3 | 0 | `3c80a38eb981b60c471895933051de114ed8b63954e46ef8ae37d18d1a23f82f` |
| 3 | 1 | `0b58853ea3f8cc67d765a3ad73d963d117a6a40d31d8eae9d5e2e4be33fbf898` |

## Durable checkpoints and artifacts

The cross-branch unions and provenance are under
`research-checkpoints/k11122-run-41164233786/`. Only unconditional mask
obligations are merged; no branch assertion, candidate, rank, auxiliary
variable, or solver conclusion crosses branches.

- [target 0, branch 0 artifact](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41164233786/artifacts/13028882993), ZIP SHA-256 `05bf9d806a94f75e2b6095fc633fe1177880a74b5bc84fda5ca03a635449a31a`
- [target 0, branch 1 artifact](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41164233786/artifacts/13029232369), ZIP SHA-256 `6e766bdeacf63daa29af8ceff93c5ec8f332eaefcbcc380c7a1d3e5e7d63cd39`
- [target 3, branch 0 artifact](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41164233786/artifacts/13028497215), ZIP SHA-256 `461d833cbf15e2303ecb7282ba4d53e6c6ebbe8a7da69910032166b265bb8b46`
- [target 3, branch 1 artifact](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41164233786/artifacts/13028823204), ZIP SHA-256 `f4824a6127bfa5aa34c1a595a11d238d655624dd6da6d9072702cd0e782fd557`

GitHub retains these run artifacts through 30 November 2026. The small merged
checkpoints are committed so future work does not depend on that retention.

Reproduce the tests and one branch with:

```sh
python -m pip install z3-solver==4.13.3.0 python-sat==1.8.dev24
python -m unittest discover -s k11122 -p 'test_*.py' -v
python k11122/sat_search.py --target 0 --branch 0 --seconds 1200 \
  --solve-seconds 1200 --conflicts 200000 \
  --resume research-checkpoints/k11122-run-41164233786/merged-target0.json \
  --output results/t0-b0-next
```

## Follow-up implementation

Commit [`60120ba`](https://github.com/ktfoerster/Hektor-poltergeist/commit/60120ba34710c0316110ece1739fa1f10d2994d8)
implements the next experiment identified above. CaDiCaL now
runs in one owned persistent worker with deterministic 200,000-conflict
checkpoint slices. Normal slice exhaustion keeps the worker and all learned
clauses alive. After an invalid candidate, the parent retains the independent
C++ replay and streams only the newly generated CNF clauses into the same
worker. An independent parent wall bound can still kill and join a stuck
worker; the replacement inherits the exact formula but not the killed
process's learned clauses.

Fifteen tests pass, including worker clause propagation and partition coverage
for both target orbits. A full merged target-0 branch-0 smoke test accumulated
550,009 conflicts over eleven slices in the same worker and stopped cleanly at
its 90-second parent bound. This validates interruption/checkpoint behavior;
it does not resolve either orbit. The next hosted matrix starts from the new
1,541/1,325-mask unions. Raw UNSAT remains uncertified unless a proof is emitted
and independently checked.

## Persistent-worker hosted matrix 41166640954

The push-triggered follow-up
[`41166640954`](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41166640954)
completed all four jobs normally. All 15 tests passed in every job. Each job
kept one worker PID and generation for its complete 20-minute search, including
ordinary conflict-slice UNKNOWNs, SAT candidates, and streamed clauses.

| Target | Branch | SAT candidates rejected | Final masks | Final vars | Final clauses | Conflicts | Final candidate failures |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 27 | 1,973 | 830,812 | 3,105,881 | 8,408,862 | 245,206 / 2,979,236 |
| 0 | 1 | 26 | 1,957 | 820,616 | 3,069,475 | 7,853,465 | 246,303 / 2,979,236 |
| 3 | 0 | 18 | 1,613 | 895,648 | 3,497,623 | 5,527,177 | 239,592 / 2,937,186 |
| 3 | 1 | 19 | 1,629 | 902,086 | 3,520,191 | 5,596,793 | 229,807 / 2,937,186 |

The 90 complete finite-suite candidates all failed unchanged exhaustive C++
replay. Freshly recompiling `verify.cpp` and replaying the four final tables
again produced exactly 524,288 masks and 2,979,236 or 2,937,186 connected-source
obligations, with the failure counts above. No encoder/checker disagreement
occurred. Every branch ended `UNKNOWN`; no raw UNSAT was used.

The new strict branch unions contain 2,092 target-0 masks and 1,745 target-3
masks. This preserves 551 and 420 new distinct unconditional obligations beyond
the preceding 1,541/1,325 inputs. Compared with the first Boolean matrix, the
persistent-worker run rejected 90 rather than 53 candidates despite starting
from stronger suites. This is a measured campaign outcome, not a general
solver-speed theorem.

Artifacts:

- [target 0, branch 0](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41166640954/artifacts/13030390269), SHA-256 `757f46a851aeb4ba8564be8401e54de8ed397aa1317f5e5485161dd43b936419`
- [target 0, branch 1](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41166640954/artifacts/13029782198), SHA-256 `b219002323e7f8e96d80474a9add475e8d6a1ee36eab93e51a440bd3f29a585a`
- [target 3, branch 0](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41166640954/artifacts/13029547838), SHA-256 `e56220073b0cb4bffecca5087eb48db257024258f467f397f223aafde894085a`
- [target 3, branch 1](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41166640954/artifacts/13029552874), SHA-256 `05a4e235433ddc3f833ca19a0f9049f2166e6a3af9a74dd26dafb48e8da3c841`

The durable unions and exact source provenance are under
`research-checkpoints/k11122-run-41166640954/`.

## Current status and next experiment

Both one-bit destination orbits remain unresolved; the established 2–3-state
bounds are unchanged. Repeating this matrix unchanged would mostly continue a
lexicographically clustered first-16 counterexample stream. The next concrete
experiment should change the CEGIS batch selection: retain exact exhaustive
replay, but choose a deterministic diverse set of failing residuals across the
full scan (for example by failure-edge-count strata and stable mask order),
then differentially test that every returned mask really rejects the candidate.
This preserves unrestricted semantics while testing whether broader clauses
reduce candidate churn. A negative claim still requires checked DRAT/LRAT for
both branches; timeouts and invalid candidates remain non-results.
