# Exporting and checking the exact Boolean formula

This addition changes no routing constraints, checkpoints, or search defaults.
It supplies deterministic DIMACS export and a conservative proof path. It does
not establish a new K11122 result.

## Reproduce

Install `python-sat==1.8.dev24`. From the repository root:

```sh
python k11122/proof_cnf.py export --target 0 --branch 0 \
  --checkpoint k11122/checkpoints/run-41180021309/t0-b0.json --output cnf-t0-b0
python k11122/proof_cnf.py certify --output cnf-t0-b0 --seconds 60
```

The export directory must be new. Masks are deduplicated and sorted. The
existing encoder generates every clause; a streaming subclass replaces only
the solver's clause sink. Export includes the exact DIMACS, selector-to-action
map, ordered masks, explicit branch restriction, and SHA256 hashes of the
formula, clause body, mapping, encoder, and exporter. No phase preferences,
learned clauses, or candidate tables constrain this export. Branch `-1` omits
the source partition. A checkpoint supplies masks only, not branch constraints;
select the intended branch explicitly.

`certify` runs a fresh proof-producing Glucose3 backend through pinned PySAT,
then runs the independent checker in a separate process. Each phase has its own
wall limit (1–3600 seconds); timed-out children are killed and joined. Logs and
`certification.json` record the outcome. This proof backend is separate from
the existing search portfolio. Glucose42 proof extraction failed locally with
a bad-file-descriptor error, so it is deliberately not used here.

## What the status means

| Status | Meaning |
|---|---|
| `SAT_FINITE_CNF` | This finite formula is satisfiable; no full routing claim. |
| `CNF_UNSAT_RUP_VERIFIED` | Independent unit propagation checked every retained proof addition and the final empty clause for the hashed CNF. |
| `UNKNOWN` | Timeout or solver/checker failure; inspect logs. |

The checker imports no SAT library. Each addition must be reverse-unit-propagation
(RUP) redundant: assuming its negation must produce a contradiction by Boolean
unit propagation. Deletion lines are ignored, retaining only original and
already proved clauses; this is sound but can cost memory/time. RAT-only steps
are rejected. The default checker uses persistent two-watched-literal propagation, fresh
assignments per RUP query, and streaming DIMACS/proof parsing. Use
`--checker reference` to select the original full-scan implementation.
Both are independent of the SAT solver. Large-instance proof throughput and
peak memory are not yet established; retained deletion clauses can still
consume substantial memory. RAT/LRAT support remains outside this implementation. There is no
fallback that converts an unverified solver answer into a proof claim.

A checked CNF refutation still depends on the correctness of the documented
routing-to-CNF translation. It is not a formal proof of that translation.
For an orbit refutation with the current exhaustive source split, both branches
must be certified (or use a branch-free formula); a single branch is insufficient.
A positive graph result still requires independent full residual/source replay
for both destination orbits. No such new graph result is claimed.

## Validation

Tests compare deterministic exports with the existing encoder's exact clause
fingerprint and counts, solve a small routing export, check a nontrivial UNSAT
proof, reject truncated/incorrect proofs and malformed DIMACS, and retain the
existing semantic and corruption regression suite. The separate bounded GitHub
workflow runs these tests and a solver-to-checker UNSAT smoke test. That fixture
is a pipeline test, not a routing impossibility certificate.

## Watched-literal validation

The optimized propagator is compared against the reference on all 512 formulas
over the nine non-tautological clauses on two variables, with ten candidate
clauses per formula (5,120 queries), plus 10,000 seeded incremental queries over
12 variables. Incremental tests retain proven additions and exercise persistent
watch movement. Both engines check an actual Glucose3 pigeonhole refutation.
Malformed deletion lines are rejected. The complete regression suite has
24 tests. These checks provide implementation evidence, not a formal verification.

The bounded pipeline clears stale certification/proof output before starting;
the checker hashes inputs before and after verification and rejects changes.
Results include the selected engine and the propagator source hash. Formula
and proof parsing stream from disk, although clauses still reside in memory.
