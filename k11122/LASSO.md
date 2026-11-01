# K11122 rank-free lasso learner (1 November 2026)

This is a new representation, not a relaxation or new routing model.
The old `sat_search.py`, `verify.cpp`, `proof_cnf.py`, and adaptive
benchmark are unchanged. Both destination orbits remain UNKNOWN.

## Clause correctness

One GLOBAL one-hot selector chooses a legal outgoing neighbor and emitted bit
for each normalized local observation (vertex, local live ports, incoming port,
packet bit). Injection rows use incoming port -1 and initial packet bit zero.
Transit rows depend neither on the source identity nor on remote failures.
The immediate-target-edge delivery normalization is retained. No mutable
router state, TTL, hidden phase, monotonic bit, arbitrary arrival obligation,
or unreachable-cycle prohibition is introduced.

For a connected source and fixed residual, any failing deterministic walk
has a source injection followed by a finite reachable prefix and a first
repeated FULL arrival state (vertex, incoming port, packet bit). Collect
every selector actually followed, from the source injection to the closing
edge. The blocking clause is the disjunction of their negations. Any policy
that retains all these actions repeats exactly the same execution by
induction on the steps and thus fails to deliver. Consequently the clause
is necessary for every successful policy. Prefixes and injection MUST NOT
be omitted; otherwise an unreachable loop would be falsely excluded.
A transient source revisit with a changed arrival configuration is legal.

Because the policy domain is finite, a complete SAT solver, with no resource
limits, together with exhaustive finite-suite walk replay will eventually
return finite-suite SAT or UNSAT. The implemented solver is bounded and may
return UNKNOWN. A finite-suite candidate requires scanning ALL masks and
connected nonself sources. Full graph positivity additionally needs the
unchanged C++ verifier to pass all 524288 residual masks for BOTH target
orbits. A raw solver UNSAT is explicitly UNCERTIFIED. For an impossibility
claim, individually audited lasso clauses and an independently checked proof
of UNSAT of the exact exported CNF are needed for both exhaustive branches
of at least one destination orbit. No such proof is claimed here.

## Independent audit and reproducibility

`lasso_witness.py` imports no SAT/synthesis code. It independently rebuilds
graph geometry, connectivity, selectors, first-hop branch, each path, and
the first closing full-state cycle. It independently reconstructs EVERY
exactly-one clause, branch clause, and witness clause in the exported CNF,
checks exact order, metadata and artifact digests. The new tests also compare
literal walks, reference rank CNF under frozen policy assumptions, and
learner traces on a complete small policy family. They include successful
source revisits, disconnected/vacuous cases, corruption, both target orbits,
and branch coverage.

Resumption imports only independently rechecked witness clauses on the exact
same target, branch, masks, and source-code dependencies. It does not claim
to preserve SAT solver learned clauses across processes. A per-run manifest,
formula, policy, full witness JSONL, hashes, seed, backend, progress and
individual bounded-slice logs are preserved. A disconnected source is not a
witness; failure observations are never gathered from arbitrary arrivals.

## Commands

From the repo root, install Python 3.12 and pinned
`python-sat==1.8.dev24`, `z3-solver==4.13.3.0`.
Then:

```bash
python -m unittest discover -s k11122 -v
g++ -O3 -std=c++17 k11122/verify.cpp -o verify
python k11122/merge_checkpoints.py --target 0 --output frozen-t0.json
python k11122/lasso_search.py run --target 0 --branch 0 --seconds 75 \
  --verify "$PWD/verify" --output lasso-t0-b0
python k11122/lasso_search.py audit --output lasso-t0-b0
python k11122/lasso_search.py run --target 0 --branch 0 --seconds 75 \
  --resume lasso-t0-b0 --verify "$PWD/verify" --output lasso-resumed
python k11122/proof_cnf.py export --target 0 --branch 0 \
  --checkpoint frozen-t0.json --output rank-t0-b0
```

The hosted workflow compares the FULL **2701** merged target-0 masks,
branch 0, by measuring rank-CNF construction and rank-free construction,
formula counts and rank-free bounded search on that same suite. Formula
size alone is **not** a solver speedup measurement; rank-export time is
not solver time. In particular the preceding 2648-mask adaptive pilot
is not the same frozen benchmark. No other branch or orbit conclusion
is implied.

Review the full Actions logs/artifact before interpreting outcomes.
Scientific status must remain UNKNOWN without independent evidence.
