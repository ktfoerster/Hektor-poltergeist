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

## Hybrid counterexample matrix 41170473396

The hybrid first-eight/hash-eight miner run
[`41170473396`](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41170473396)
completed all four jobs normally. All sixteen tests passed in each job. The
four artifact ZIP SHA-256 values match GitHub's recorded digests, every
internal manifest entry verifies, and freshly compiled independent binaries
reproduced the exact exhaustive replay counts.

| Target | Branch | Rejected candidates | Final masks | Variables | Clauses | Final candidate failures |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 0 | 2,272 | 1,010,672 | 3,803,311 | no candidate |
| 0 | 1 | 5 | 2,352 | 1,057,908 | 3,990,263 | 48,912 / 2,979,236 |
| 3 | 0 | 0 | 1,779 | 1,007,606 | 3,952,633 | no candidate |
| 3 | 1 | 3 | 1,827 | 1,040,610 | 4,087,819 | 150,813 / 2,937,186 |

All outcomes are `UNKNOWN`. The strict orbit unions increased by 80 masks for
target 0 and 48 for target 3, to 2,352 and 1,827. The final target-0 and
target-3 candidates were replayed over all 524,288 residuals and still fail;
the smaller failure counts do not imply proximity to a valid policy.

Artifacts (retained through 30 November 2026):

- [target 0, branch 0](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41170473396/artifacts/13031645204), SHA-256 `a3fc06fa6d7838e9ca6fec469266ade022237f11dc5be66e8903c65d2d0d3dec`
- [target 0, branch 1](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41170473396/artifacts/13031138748), SHA-256 `95af4997af7369f60442daa8ad87410a862b88d197ba0e68bca70a74345a6871`
- [target 3, branch 0](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41170473396/artifacts/13030589921), SHA-256 `ef3d141439bc238eb4429be8b94f35ea8afa5f2a55697a0cadc8cb4ed1c9f72b`
- [target 3, branch 1](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41170473396/artifacts/13031407324), SHA-256 `e86712727477e631e2c2f40993a7756bb54e59579bf696d4de36ebf68346e6df`

The exact branch checkpoints and provenance are preserved under
`k11122/checkpoints/run-41170473396/`; the merger imports only unconditional
residual masks. The next matrix uses their strict 2,352/1,827-mask unions.

## Second pinned SAT backend

The CNF runner now accepts `--backend cadical195` or
`--backend maplechrono`. Both backends receive the byte-identical clause
stream; the checkpoint records the canonical pinned backend and whether its
seed is effective. Differential tests cover identical formula fingerprints,
exhaustive triangle semantics, model extraction, and streamed clauses in a
persistent worker for both solvers. Seventeen tests pass locally.

A simultaneous 90-second smoke comparison on the exact 2,352-mask target-0
branch-0 input built 1,057,908 variables and 3,990,263 clauses with formula
SHA-256 `a976e5fa877e464491d0c90096b55c6eaccdbd71ffdcd573cf55926d3c862f79`
for both backends. MapleChrono completed two 200,000-conflict slices; CaDiCaL
did not complete the first before the parent wall bound. Shared-host contention
makes this a pipeline result, not a controlled speedup claim. The next bounded
four-job hosted matrix therefore tests MapleChrono on the same preserved
constraints. No solver timeout or uncertified result changes the scientific
status: both one-bit orbits remain unresolved and the 2–3-state bounds stand.

## MapleChrono hosted matrix 41172644514

The alternative-backend run
[`41172644514`](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41172644514)
completed all four jobs normally. All seventeen then-current tests passed in
each job. The four GitHub artifact ZIP digests and every internal manifest
entry verify.

| Target | Branch | SAT candidates | Masks | Conflicts completed | Status |
|---:|---:|---:|---:|---:|---|
| 0 | 0 | 0 | 2,352 | 7,800,038 | UNKNOWN |
| 0 | 1 | 0 | 2,352 | 9,000,039 | UNKNOWN |
| 3 | 0 | 0 | 1,827 | 7,800,031 | UNKNOWN |
| 3 | 1 | 0 | 1,827 | 11,400,047 | UNKNOWN |

Artifacts:

- [target 0, branch 0](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41172644514/artifacts/13032147746), SHA-256 `ac7baeee9c9124dd1afb3f6965dfcc69f5a7f20866d516fe7f4046fafc20f6fd`
- [target 0, branch 1](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41172644514/artifacts/13031988294), SHA-256 `c852308d83a547c467ce1229efb4373d3c0115ae9e8618ca202836ea57e6308f`
- [target 3, branch 0](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41172644514/artifacts/13032466995), SHA-256 `2409aaad6fb536f9d91b02086abaf82911623436e4a08868fe7d640a3f27c202`
- [target 3, branch 1](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41172644514/artifacts/13032202836), SHA-256 `830ab359c2233120fceb2faa34c92cd6be487acc6bb4e6492acc15226b2f8710`

MapleChrono processed more conflict slices but discovered no candidate and no
new residual. This is an observed throughput/candidate-discovery comparison,
not a solver theorem and not a negative result. The strict unions therefore
remain 2,352 masks for target 0 and 1,827 for target 3.

## Phase-guided repair implementation

The next search mode uses a complete previously rejected table only to set SAT
branching phases. The parser verifies the graph/target, every legal row, exact
completeness, and table SHA-256. It supplies positive and negative phases for
all global selectors but adds no clause or assumption. A corruption test and a
test that forces a preferred selector to its alternative demonstrate that the
hint does not constrain satisfiability. Eighteen tests pass locally, including
the existing semantic/differential suite for all three supported backends.

The four seed tables were independently replayed again before commit:

| Target | Branch | Seed SHA-256 | Exhaustive failures | Source artifact |
|---:|---:|---|---:|---:|
| 0 | 0 | `c813cbcabbd4ceda65b2fc6501c5566e5b3592fa82b20abe92a7c0c39eaf289b` | 90,269 / 2,979,236 | 13030766546 |
| 0 | 1 | `6a76eae2407cea086f51c2ddad90e0995ef0350d61925110d1d1b521d90618b2` | 48,912 / 2,979,236 | 13031138748 |
| 3 | 0 | `7438fb8b73e265d58c1f89d7b643be3e45cde1e5f01a4d2bd3e96d4c8c6805a3` | 234,653 / 2,937,186 | 13031225368 |
| 3 | 1 | `8be1e02819569916fe211529f1ef163046f41563dad5eea3dda1a7c803e22f85` | 150,813 / 2,937,186 | 13031407324 |

CaDiCaL receives a different deterministic recorded seed in each branch. This
changes the search trajectory while preserving the exact 2,352/1,827-mask CNF
and both emitted bits in every physical-first-hop branch. Any returned table
still requires unchanged exhaustive replay; any timeout remains `UNKNOWN`.

## Phase-guided hosted matrix 41176610833

Run [`41176610833`](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41176610833)
completed all four jobs normally. All eighteen tests and all four committed
phase-policy SHA-256 checks passed in every job. Phase guidance produced 30
complete finite-suite candidates across all four branches; every one failed
the unchanged exhaustive verifier, and the separate miner agreed on exact
obligation and failure counts.

| Target | Branch | Rejected candidates | Final masks | Variables | Clauses | Final candidate failures |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 5 | 2,432 | 1,109,956 | 4,200,623 | 72,031 / 2,979,236 |
| 0 | 1 | 10 | 2,512 | 1,156,696 | 4,386,225 | 43,905 / 2,979,236 |
| 3 | 0 | 3 | 1,875 | 1,075,518 | 4,231,891 | 160,548 / 2,937,186 |
| 3 | 1 | 12 | 2,019 | 1,171,768 | 4,619,387 | 104,303 / 2,937,186 |

Freshly compiled copies of `verify.cpp` and `counterexample_miner.cpp` replayed
all four retained tables over 524,288 residual masks and reproduced the exact
2,979,236 or 2,937,186 obligations plus the failure totals above. The strict
cross-branch unions are 2,568 masks for target 0 and 2,053 for target 3, gains
of 216 and 226 over the preceding 2,352/1,827 inputs. Only unconditional masks
are merged; phase tables, branches, ranks, policies, and solver conclusions
remain separate.

Artifacts (retained through 30 November 2026):

- [target 0, branch 0](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41176610833/artifacts/13033838330), SHA-256 `850ad131beac6a72efb5a69bdcb4e3d0580d7ed775cdb92ec36d72705bdf483b`
- [target 0, branch 1](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41176610833/artifacts/13034150068), SHA-256 `93ca7f8b30c42a3d725ba2165344896f3dfd41486eefe03d0b2e7c6cfb79c8fc`
- [target 3, branch 0](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41176610833/artifacts/13033429585), SHA-256 `7ecbfdb30ca1e3947214b6a9b704c4367cdfd25950c3ee3d7d4f7fa48b058cd3`
- [target 3, branch 1](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41176610833/artifacts/13033319868), SHA-256 `36a2abc1bb659ec8e8b714fb8a0728133daac7ccfd1973dff6c4f29f6a8fe567`

Relative to the same-input unphased hybrid matrix, phase guidance increased
candidate discovery from eight to thirty and produced progress on every
branch. This is a measured search improvement, not evidence of positivity or
negativity. Every branch remains `UNKNOWN`; both target orbits and therefore
the graph's one-bit classification remain unresolved. The latest four invalid
tables now serve as phase hints for one final bounded continuation with fresh
seeds and the stronger 2,568/2,053 unions.

