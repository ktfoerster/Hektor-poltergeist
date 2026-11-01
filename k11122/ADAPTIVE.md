# Adaptive CNF pilot (1 November 2026)

This extends the fixed four-case pilot with a bounded, resumable queue. It does
not change the routing encoding, the common-source model, or the C++ verifier.
No full-size solving improvement or classification result is claimed here.

## Coverage and scope

The root is the exact retained target-0, branch-0 CNF. Its four initial children
are the same exactly-one source-action partition as the previous pilot.
A timed-out leaf can then be split on a selector literal `v` into `v` and `-v`.
The negative child allows ALL other actions of that row, not one chosen alternative.
This Boolean identity gives disjoint, exhaustive coverage without any symmetry
assumption. It is valid for source and transit action selectors. Every child is
reconstructed as the pinned original parent plus its entire assumption path.

The ledger publishes both children in one atomic replacement. A nonblocking
exclusive lock permits only one runner/auditor per work directory. Uncommitted
split directories are moved to `orphans/`, preserved, and reconstructed. An
interrupted solve has no committed result; resume retains that trial and uses a
new directory. Checkpoints are formulas and decisions, not solver-memory images.
The source hashes are pinned: changed code requires an explicit migration or a
new work directory. Do not edit the ledger to bypass a source mismatch.

## Probe and scheduling policy

Pending leaves are solved breadth-first. When none remain, the shallowest eligible
UNKNOWN leaf is considered for refinement. A separate bounded worker loads its
formula and probes at most 16 deterministic action selectors spread across source
and transit rows. It measures propagation in both polarities and prefers a large
minimum closure, breaking ties by total closure and variable ID. Explicit path
decisions are excluded. Variables with an inconsistent polarity are excluded to
avoid counting trivial forced branches as useful splitting progress. Probes do not
emit certificates or close cases. These are unit-propagation probes, not short
complete SAT searches; their score has no measured runtime-prediction guarantee.
If loading/probing times out or finds no suitable candidate, the leaf stays UNKNOWN.
A completed unsuccessful probe is not retried automatically on resume.

The pilot uses one hosted job, at most eight solve attempts, 120 seconds per
solve/check/replay phase, 45 seconds per probe, maximum assumption depth three,
and a 1,200-second queue budget. The queue deadline caps each phase. Initialization,
structural validation, and artifact upload are outside that queue budget; the
whole GitHub job has a 35-minute hard limit. Audit has a separate 120-second cap.
This is one bounded run, with no recurring resubmission or paid provisioning.

## Result acceptance

Every solver, checker, decoder and probe worker runs in an owned process group;
timeout kills that group and joins the worker. Attempt logs, models, proofs,
certifications, timings and file hashes are retained. Invalid SAT candidates remain
FINITE_SAT_GLOBALLY_INVALID in their replay records. Such finite-SAT leaves are
retained and not automatically refined; adding their counterexamples to a new
parent is future work, not implemented here.

An UNSAT result requires the existing independent RUP checker. For bootstrap unit
contradictions Glucose3 can return an empty proof; the new wrapper proposes the
single empty-clause step and the checker must independently justify it. A failed
check remains UNKNOWN. Raw solver status never closes a node.

`validate` checks coverage, source/input hashes, exact child reconstruction and
attempt-file associations, but DOES NOT replay proofs. `audit` additionally reruns
the independent proof checker on every closed leaf. Only if every leaf is checked
UNSAT does it report `finite_parent_unsat: true`. This is a finite-family refutation
of the original target-0 branch-0 only, subject to encoding correctness. It is NOT
a graph classification: branch 1 remains outside this pilot. An orbit-positive
claim still requires full replay; both destination orbits are needed for a graph
positive. K11122 remains UNKNOWN until sufficient evidence is independently verified.

## Commands (new output directory)

```sh
python -m unittest discover -s k11122 -v
python k11122/proof_cnf.py export --target 0 --branch 0 --checkpoint k11122/checkpoints/run-41180021309/t0-b0.json --output parent
python k11122/adaptive_cnf.py init --parent parent --work adaptive
python k11122/adaptive_cnf.py run --work adaptive --seconds 1200 --node-seconds 120 --probe-seconds 45 --attempts 8 --max-depth 3
python k11122/adaptive_cnf.py validate --work adaptive
python k11122/adaptive_cnf.py audit --work adaptive --seconds 120
```

To resume, use `run` on the same directory with an explicitly bounded new budget;
do not call `init` over it. Resume checks all recorded hashes first. An expired
outer CI job may leave uncommitted trial directories: their files are evidence of
an interruption, not accepted results.

Tests cover multilevel exhaustive coverage and pairwise disjointness via a separate
SAT query, actual finite-SAT decoding/full small-graph replay, deliberate Boolean
UNSAT fixtures with proof rechecking, missing siblings, wrong-child proof rejection,
stale parent metadata, altered child formulas, orphan recovery, and queue resumption.
The deliberately contradictory fixture is a test, never a routing impossibility.
Review `summary.json`, `ledger.json`, `audit.json`, and each trial's replay before
claiming progress. Comparisons must account for the different budgets and cases;
closed leaves alone are not a coverage-weighted speedup measurement.
