# K11122: exact search with exhaustive failure checking

K11122 is the seven-vertex graph with all edges except 34 and 56.
Targets 0 and 3 represent its two destination orbits. Two packet states mean
one bit. This is actual routing synthesis, separate from the repository's
colouring infrastructure demo. No existing unpublished manuscript or seed
policy is uploaded by this implementation.

## Launch
The dedicated workflow runs automatically on changes to `k11122/` on main,
and manually via **Actions → K11122 exact search → Run workflow**.
The initial run launches two jobs, one per orbit, each with a 20-minute
search budget and a 30-minute hard job limit. It does not recur indefinitely.
Download the `k11122-target-*` Actions artifacts. Each contains checkpoints,
progress, latest policy, full replay counts, hashes and solver diagnostics.

Local: install Python 3.12, g++ and `z3-solver==4.13.3.0`, then:
```
python -m unittest discover -s k11122 -v
python k11122/search.py --target 0 --seconds 1200 --output results/t0
python k11122/search.py --target 3 --seconds 1200 --output results/t3
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
replace mathematical review of the encoder. Initial jobs are independent
orbit tasks, not disjoint partitions of the policy space. No external secrets,
self-hosted runners, paid machine provisioning or infinite resubmission.
