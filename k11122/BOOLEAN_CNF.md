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

The pinned backend is `python-sat==1.8.dev24` with `Cadical195`. Clauses are
emitted in deterministic order with seed `20261031`; checkpoints record the
variable count, clause count, exact clause-stream SHA-256, source hashes,
resume hash, branch, dependency version, and solver outcome. CaDiCaL runs in
an owned fork because PySAT's CaDiCaL wrapper does not provide a reliable
wall-clock interrupt. The parent terminates and joins only that child at the
declared bound. A SAT child returns a complete legal table, which the unchanged
C++ program replays on all 524,288 residuals and all connected nonself sources.

An `UNSAT_UNCERTIFIED` result is not an impossibility result: this campaign
does not emit and independently check DRAT/LRAT. Likewise, timeout, OOM, or an
invalid exhaustive-replay candidate leaves the unrestricted problem open.

Run locally:

```sh
python -m pip install z3-solver==4.13.3.0 python-sat==1.8.dev24
python -m unittest discover -s k11122 -p 'test_*.py' -v
python k11122/merge_checkpoints.py --target 0 --output merged-t0.json
python k11122/sat_search.py --target 0 --branch 0 --seconds 1200 \
  --solve-seconds 1200 --resume merged-t0.json --output results/t0-b0
```

The tests exhaust all 64 normalized triangle bit policies and compare CNF,
the prior SMT encoding, and literal walks. They also cover exact-one selectors,
all guarded-comparator boundary values through three bits, shared injection,
disconnected cases, both target orbits, transient source revisits, unreachable
loops, branch coverage/disjointness with both emitted bits, checkpoint
corruption, and the independent verifier's malformed-policy rejection.
