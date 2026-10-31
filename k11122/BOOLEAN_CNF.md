# Boolean CNF encoding

`sat_search.py` is a direct Boolean encoding of the same unrestricted finite
residual suite as `search.py`. It changes the solver representation, not the
routing model.

## Policy variables

For every common row `(u,L,p,b)`, where `L` is the complete local live-port
set, the encoding creates one selector for every legal `(v,b')`. Exactly one
selector is true. Injection rows use `p=-1,b=0`; transit rows use the real
incoming live port and packet bit. The selectors are global, so residuals with
the same local observation share the same action. When the target port is
live, the sole selector is immediate delivery with output bit zero. This is
the same justified normalization as the SMT implementation.

The two branch jobs constrain one injection observation by physical next hop.
Both output-bit selectors for that hop remain available. The two next-hop
sets are disjoint and cover the row's complete legal domain; no symmetry or
equivalence assumption is used.

## Per-residual certificate

For a residual mask, let `Q` contain every nonterminal arrival configuration
`(u,p,b)` in the target component. Thus `Q` counts live incoming ports and
both packet bits, rather than vertices. Each `q in Q` receives a Boolean
`good(q)` and `ceil(log2(|Q|+1))` rank bits. The clauses are:

1. `good(q)` implies a nonzero rank.
2. If `good(q)` and its global selector chooses a non-delivery successor
   `q'`, then `good(q')` holds and `rank(q') < rank(q)`.
3. Each connected source's selected injection either delivers immediately or
   enters a good successor.

Selector implications also multiplex the selected successor rank into one
rank vector per current state. A Tseitin binary comparator is guarded by
`good(q)`. Bad or unused states therefore impose neither delivery nor
acyclicity. Direct-delivery states need no successor constraint. Comparator
auxiliaries and ranks are proof variables, never packet-header state.

Soundness follows from strict descent through positive ranks. A good walk
cannot repeat a full arrival configuration and must reach delivery.
Completeness follows by marking exactly the successful configurations good
and assigning their remaining delivery distances. A deterministic successful
walk has at most `|Q|` nonterminal configurations, which fits the chosen rank
width. Source revisits, arbitrary behavior at unreachable arrivals, and
disconnected source-target pairs are all retained.

## Reproducibility and interpretation

The pinned package is `python-sat==1.8.dev24`. The supported backends are
`Cadical195` and `MapleChrono`; both receive the identical clause stream.
CaDiCaL uses seed `20261031`. MapleChrono exposes no seed through PySAT and is
deterministic for fixed clause order. Checkpoints record whether the seed is
effective, the backend, and the
variable count, clause count, exact clause-stream SHA-256, source hashes,
resume hash, branch, dependency version, and solver outcome. The backend runs in
an owned persistent worker. Each `solve_limited` call has a deterministic
conflict budget; an UNKNOWN worker stays alive so its learned clauses survive
the next slice, and clauses for newly found counterexamples are streamed to
that same worker. The parent also enforces the declared wall bound. If the
worker misses it, only that worker is terminated; the exact parent formula is
retained and a fresh worker can be forked, though the killed worker's learned
clauses are lost. A SAT worker returns a complete legal table, which the
unchanged C++ program replays on all 524,288 residuals and all connected
nonself sources. Rejected candidates are also replayed by
`counterexample_miner.cpp`. After the measured all-hash experiment, the miner
keeps eight early failures plus eight residuals selected across the full scan
by fixed SplitMix64 priorities. The runner aborts unless its exact obligation
and failure counts agree with the unchanged verifier. These masks are only
CEGIS obligations and do not replace the verifier or constitute a negative
certificate.

An optional complete prior policy may be supplied as branching phases. The
reader validates the graph, target, every legal row, exact completeness, and
the table hash. It then calls the backend's phase-preference API for all global
selector literals. This adds no clause or assumption: a test forces a selector
away from its preferred phase and confirms that an alternative model remains
SAT. Phase hints are therefore a search heuristic, not packet state, a frozen
row, or a restriction of the policy space.

An `UNSAT_UNCERTIFIED` result is not an impossibility result: this campaign
does not emit and independently check DRAT/LRAT. Likewise, timeout, OOM, or an
invalid exhaustive-replay candidate leaves the unrestricted problem open.

Run locally:

```sh
python -m pip install z3-solver==4.13.3.0 python-sat==1.8.dev24
python -m unittest discover -s k11122 -p 'test_*.py' -v
python k11122/merge_checkpoints.py --target 0 --output merged-t0.json
python k11122/sat_search.py --target 0 --branch 0 --seconds 1200 \
  --solve-seconds 1200 --conflicts 200000 --resume merged-t0.json \
  --output results/t0-b0
```

The tests exhaust all 64 normalized triangle bit policies and compare CNF,
the prior SMT encoding, and literal walks. They also cover exact-one selectors,
all guarded-comparator boundary values through three bits, shared injection,
disconnected cases, both target orbits, transient source revisits, unreachable
loops, branch coverage/disjointness with both emitted bits, checkpoint
corruption, the independent verifier's malformed-policy rejection, and exact
verifier/miner agreement with literal replay of every selected residual on a
failing four-vertex policy.

