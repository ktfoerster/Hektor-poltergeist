# K11122: exact search with exhaustive failure checking

K11122 is the seven-vertex graph with all edges except 34 and 56.
Targets 0 and 3 represent its two destination orbits. Two packet states mean
one bit. This is actual routing synthesis, separate from the repository's
colouring infrastructure demo. No existing unpublished manuscript or seed
policy is uploaded by this implementation.

## Launch
The dedicated workflow runs automatically on changes to `k11122/` on main,
and manually via **Actions → K11122 Boolean SAT search → Run workflow**.
The current continuation uses the Boolean encoding documented in
[`BOOLEAN_CNF.md`](BOOLEAN_CNF.md). It launches four jobs, two disjoint
branches per orbit, each with a 20-minute search budget and a 30-minute hard
job limit. It does not recur indefinitely. Download the `k11122-cnf-target-*`
Actions artifacts. Each contains checkpoints,
progress, latest policy, full replay counts, hashes and solver diagnostics.

Local: install Python 3.12, g++, `z3-solver==4.13.3.0`, and
`python-sat==1.8.dev24`, then:
```
python -m unittest discover -s k11122 -v
python k11122/sat_search.py --target 0 --seconds 1200 --output results/t0
python k11122/sat_search.py --target 3 --seconds 1200 --output results/t3
```
Resume by adding `--resume results/t0/checkpoint.json` and using a NEW output
directory. This rebuilds the accumulated exact constraints; it is not a
solver-memory snapshot. UNKNOWN can recur without new search settings.

## Model and completeness
A single action variable is shared for each (vertex, local live-neighbor
bitmask, incoming port, packet bit). Separate common injection actions depend
only on source and its local live set. All actions choose a live port and a
next bit. There is no hidden source identity, router memory or remote oracle.
Source equals destination and disconnected pairs are vacuous.

The only normalization is immediate delivery when the destination edge is
live: any successful policy can deliver there sooner, with no effect on any
other packet. Header on delivery is irrelevant and fixed to zero.

For each selected residual, nonterminal arrival configurations have integer
ranks from zero through the number of configurations. Positive rank implies
that the chosen step delivers or moves to a strictly smaller positive rank.
Every connected source's injection must deliver or reach positive rank.
Unreachable configurations may have rank zero: successful transient paths
are allowed, and arbitrary-arrival success is NOT required.

Soundness follows by descent. Completeness follows by assigning the remaining
delivery distance to every successful configuration and zero to failing ones.
A successful deterministic walk repeats no full configuration before delivery,
so the rank bound suffices. Source injection variables are shared across all
residuals. No symmetry, frozen palette, rotation or trace-preservation assumption.

This is symbolic exhaustive search (SMT plus counterexamples), not a practical
promise to enumerate every table. Every SAT candidate is independently
simulated by C++ on ALL 524,288 live-edge masks and every connected source.
Up to 16 failed residuals are added jointly, excluding that candidate.
With unlimited terminating solver calls this finite process is complete;
with the actual resource limits it may end UNKNOWN. The C++ verifier constructs
connectivity independently and detects repeated (vertex,incoming port,bit).

## Interpreting outputs
- VERIFIED_POSITIVE: full independent residual/source replay passed for ONE
  destination orbit. Both orbits must pass to settle the graph positively.
- UNKNOWN: timeout/budget exhaustion; no negative conclusion.
- UNSAT_UNCERTIFIED: solver reports unsatisfiable for the selected exact family,
  but no independently checked refutation is produced. NOT a publishable
  impossibility certificate. No lower bound is upgraded by this status.
- Job failure: inspect logs; never interpret crashes as UNSAT.

All current scientific bounds remain 2–3 states until verified results warrant
an update. `max_successful_hops` of an invalid policy is not a guarantee.
Ranks are auxiliary proof variables, not packet state. Counterexamples are
LIVE masks with lexicographically ordered edges, excluding 34 and 56.

Tests cover complete small graphs and rejection of malformed policies.
The full checker is used on every candidate, but correctness testing does not
replace mathematical review of the encoder. Within each orbit the two jobs partition one source action by its physical
first hop. Both emitted bit values remain free in each branch. The union is
exhaustive and the branches disjoint; no equivalence or symmetry is assumed. No external secrets,
self-hosted runners, paid machine provisioning or infinite resubmission.



## Continuation version (31 October 2026)
The workflow merges both branch checkpoints from run 41170473396 separately
for each destination orbit. The four original checkpoint files and their
artifact provenance are retained in `checkpoints/run-41170473396/`, so this
continuation does not depend on expiring Actions downloads. Original ZIPs
passed their GitHub SHA-256 digests, all CRC checks and all per-file hashes
before checkpoint extraction. The merger rechecks checkpoint hashes, model,
target, branch, backend, workflow provenance and mask domains before taking a
deterministic sorted union.
Only unconditional residual obligations are imported; no branch assertions,
solver statuses or candidate policies are combined. Each new branch starts
from the same union for its destination orbit.

Reproduce the merge with:
```
python k11122/merge_checkpoints.py --target 0 --output merged-t0.json
python k11122/merge_checkpoints.py --target 3 --output merged-t3.json
```
The output file must be new. The workflow is pinned to this input run and does
not chain indefinitely. New result artifacts still expire after 30 days.

A timeout now triggers another bounded solver call with progressively longer
limits (60,120,240,480,600 seconds) and deterministic recorded seeds, capped
by the remaining search budget. It preserves the solver and its constraints.
Other UNKNOWN reasons stop with diagnostics. This is a heuristic retry policy,
not a guarantee that different seeds yield independent search trajectories.
Formula construction and final export can extend beyond the search-call
budget; the 30-minute Actions job limit is the outer bound. Four jobs imply
at most 120 runner-minutes. No self-hosted machine is used.

The preceding retry paragraph describes the retained SMT baseline in
`search.py`. The active CNF runner uses deterministic conflict-bounded slices
in one owned persistent SAT worker. `--backend cadical195` retains the seeded
CaDiCaL path; `--backend maplechrono` runs a second solver implementation on
the byte-identical CNF. MapleChrono has no PySAT-exposed seed and is
deterministic for fixed clause order. Learned clauses survive an ordinary
conflict-slice UNKNOWN and new counterexample clauses are streamed into the
same process. A separate parent wall bound can still terminate a stuck worker;
a replacement then inherits the exact formula but not the killed process's
learned clauses. If SAT produces an invalid exhaustive-replay candidate, the
unchanged verifier remains authoritative. A separate deterministic miner must
agree with its exact obligation and failure counts, then contributes a hybrid
batch of eight early and eight hash-diversified failing residuals. The next
solve uses a strictly stronger formula. See `BOOLEAN_CNF.md` for the exact
clauses and differential tests.

The current follow-up also accepts `--phase-policy` with a complete legal
table. It validates the table strictly and uses all selector values only as
solver branching preferences. No clause or assumption is added, so every row
can change. The committed `phase-seeds/` tables are independently replayed
invalid candidates with hashes and source-artifact provenance; they are not
claimed solutions or restrictions.

`--branch 0` and `--branch 1` divide the same selected two-neighbor source
observation by outgoing neighbor; `--branch -1` leaves the space unpartitioned.
Only unconditional residual masks are imported across branches, never a
restricted UNSAT conclusion. A positive from either branch solves that orbit;
negative claims need checked proofs for BOTH branches of an orbit. Raw solver
UNSAT is still uncertified. No candidate invalidity proves nonexistence.

Checkpoints now record branch definition, input hash, inherited count, retry
reason and last candidate hash/failure count. Output directories must be empty.
Every candidate must pass all already-enforced residuals or the runner fails
with an encoder/checker disagreement. Tests additionally compare every
normalized triangle policy against literal execution and check transient
source revisits with unreachable cycles plus partition coverage/disjointness.

