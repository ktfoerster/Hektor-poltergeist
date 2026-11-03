# K11122: independently replayed best-observed historical policies — verified pilot

**3 November 2026. Scientific status: UNKNOWN for both target orbits.**
The packet-state bound remains 2–3 states. Neither a complete finite-suite
candidate nor an independently verified graph-positive policy or checked
impossibility refutation was obtained. This experiment scores historical
raw SAT assignments, which can violate clauses learned later in the run.
A best historical raw policy is **not** a solution of the final CNF.

## Provenance and reproducibility

- Tested implementation commit: `0cd696cfabc84501f5fe60743d0ff3c98632951d`.
- Successful GitHub Actions run: https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41606964011
- Complete downloadable evidence: https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41606964011/artifacts/13216474209
- ZIP SHA-256: `111429f194e0f9f1b53fd30adf2e0d711cf6b0dffc13cb7cfd25b5a052decf96`.
- The downloaded 48,823,309-byte ZIP passed CRC testing of **3,962 entries**.
  All **3,961 SHA256SUMS-indexed files** matched their SHA-256 hashes;
  the extra entry is the checksum manifest itself.
- **86 regression tests passed**, including existing rank/literal semantics,
  local forwarding and shared injection, two target orbits, lasso-witness
  corruption, audited cross-branch transfer, session cache integrity,
  journal and immutable-generation recovery, independent policy-quality
  replay and new best-policy tampering tests.
- The C++ quality scorer was built with strict warnings and compared
  against an independent Python evaluator for sampled complete policies
  on smaller graphs and both seven-vertex target orbits. The original
  exhaustive `verify.cpp` was rebuilt unchanged.
- Source and destination formulas, selectors, branch constraints, every
  source-reachable learned witness, and journal prefixes passed complete
  independent CNF reconstruction/auditing. No full-graph positive replay
  was attempted because no complete finite-suite candidate appeared.

## Exact scoring semantics

The untrusted fast C++ scorer evaluates *every connected nonself source*
on all masks in the frozen family. For each complete raw SAT assignment,
the optional `--best-interval N` evaluates the first observed assignment
and every Nth one thereafter. This pilot used **N = 16**, so the claimed
best is **best among periodically sampled assignments**, not necessarily
among all raw assignments. The default N = 0 disables the feature.

The tracked objective is lexicographic: (failing residual masks,
failing connected-source obligations, canonical policy SHA-256).
Whenever a better policy is observed, its exact TSV file and metadata
are atomically published with frozen mask and policy hashes. At the end
of each run, a separately implemented Python literal-walk evaluator
independently reconstructs all connected-source obligations and verifies
the entire chosen policy's score and metadata. A partial, corrupted
or mismatched best-policy snapshot is rejected. The quality scorer
is **only a ranking aid**; all actual necessary SAT clauses continue
to be independently checked.

## Experiment and source constraint pool

This self-contained run generated two fresh branch-0 source bundles,
fully audited them, and made one same-process attested transfer cache
per orbit. Only necessary complete source-reachable lasso clauses
were imported into branch 1. The frozen masks and route model did not
change. Source certificate counts:

| Source orbit | Strict masks | Verified source witness clauses | Nonvacuous transferred to branch 1 |
| --- | ---: | ---: | ---: |
| Target 0 | 2,701 | 39,264 | **38,715** |
| Target 3 | 2,181 | 29,376 | **29,288** |

For target 0, seeds 20261103, 20261104, 20261105 each received
**10 seconds active SAT/walk search**, with source audit/import billed
separately. Target 3 used seed 20261103 and **7 seconds**.
All destination runs used the same one-bit legal selector model,
CaDiCaL195, deterministic one-in-eight hybrid witness schedule and
maximum 96 fresh necessary clauses per raw SAT model.

## Three target-0 pairs — best sampled versus last assignment

| Seed | Full-audit raw models | Cached raw models | Full-audit best failing masks | Cached best failing masks | Full-audit last failing masks | Cached last failing masks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 20261103 | 419 | 400 | **419** | **446** | 481 | 481 |
| 20261104 | 420 | 401 | **419** | **446** | 506 | 413 |
| 20261105 | 428 | 395 | **419** | **446** | 475 | 493 |
| Mean | **422.3** | **398.7** | **419.0** | **446.0** | **487.3** | **462.3** |

The full-audit best was found at raw model index **416** and failed
**1,226 connected-source obligations** in addition to 419 masks.
Its exact policy SHA-256 starts `c3b6369ab4e0a7dd`.

The cached best was found at index **304** and failed **1,285**
connected-source obligations in addition to 446 masks.
Its exact SHA-256 starts `c775bfbc1d51d1f4`.

Across all three seeds, the same treatment's best policy appeared
at the **same assignment index with exactly the same full policy hash**.
These are **not independent solver trajectories**, despite different
integer seed values. Checking `quality-samples.jsonl` confirmed
that all 27 common recorded samples of the three full-audit runs were
byte-identical in policy hashes. Likewise, all 25 common recorded
samples of the three cached runs matched exactly.

More importantly, matching full-audit and cached runs also agreed
on **every common sampled policy**, through model 384 or 400 depending
on the run. The full-audit condition merely reached index 416 within
its 10-second active window; cached runs stopped at about index
395–401. Therefore these observations **do not show different solver
quality due to caching**. The cache accelerates preparation, not the
observed deterministic search trajectory.

Averaged target-0 preparation cost was **4.148 seconds**
with repeated full source audits versus **1.009 seconds** using the
same-process cache; the one-time certification took **3.672 seconds**.
Time spent sampling raw policy quality was about **0.13 seconds per
10-second run**. The source search cost is additional and common to
both conditions. Any apparent 3-seed statistical comparison of
routing quality is invalid without actual search diversification.

## Independent target-3 control

The target-3 single-seed pair gave the **same sampled best policy**
in both conditions: **291 failing residual masks**, **727 failing
connected sources**, found at model index **176**, with identical
policy hash beginning `309ca829ec384fce`.

| Metric | Full-audit transfer | Cached transfer |
| --- | ---: | ---: |
| Raw assignments | 296 | 261 |
| Scored assignments | 19 | 17 |
| Best sampled failing masks | **291** | **291** |
| Last raw policy failing masks | 415 | 277 |
| Preparation seconds | 3.016 | 0.756 |
| Status | UNKNOWN | UNKNOWN |

The cached condition's last raw table had only **277** failing masks,
fewer than the best *sampled* table's 291. This is an explicit
demonstration of the sampling limitation, not an error: model 261 was
not on the one-in-16 scoring schedule. The diagnostic does not
capture an absolute best unless every raw assignment is scored.

## Conclusions and next research question

1. Independently verified best-observed historical policies can be
   preserved without altering SAT semantics or sacrificing
   independent source/terminal CNF and full-walk audits.
2. Historical best values differ materially from last raw policy
   values. Tracking only the final model can misrepresent progress.
3. Session transfer caching reduces repeated audit/import
   preparation costs, but does **not** demonstrate better SAT
   convergence. The same full policy-hash sequences were observed
   across treatments on their common sampled prefix.
4. Integer CaDiCaL seed changes did not diversify any of the
   recorded target-0 policy-hash sequences in this experiment.
   Three seeds here behaved like repeated samples of the same
   deterministic trajectory, not independent optimization trials.
5. No full finite-suite candidate or checked UNSAT certificate was
   found; **both destination orbits remain UNKNOWN**.

**Next:** test *actual solver-trajectory diversification* while keeping
the complete necessary-clause semantics and independent auditing:
alternate legal phase preferences, an independent SAT backend,
or genuinely different solver-variable/order heuristics. Require
policy-hash divergence on a shared frozen suite **before** using
multiple runs as independent evidence. Use best-quality monitoring
at interval 1 when short budgets permit to score every raw policy.

The exact source, build flags, pinned dependencies, source and
destination CNFs, witness JSONL, selector maps, mask sets, phase
policies, scoring histories, policy hashes, best-policy certificates,
independent audit outputs and seed progress are preserved in the
linked artifact. Reproduce using
[BEST_OBSERVED_POLICY.md](BEST_OBSERVED_POLICY.md) and
`.github/workflows/k11122-best-observed.yml`.

A genuine positive still requires an independently verified legal
policy for **both destination orbits over all 524,288 residual masks**
and all connected nonself sources. A negative still requires a sound
complete reduction and independently checked UNSAT refutations of
both exhaustive first-hop branches of one orbit. Neither exists.
No recurring automation or unbounded computation was created.
