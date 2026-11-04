# K11122: certified selective necessary-lasso portfolios

**Mathematical classification remains UNKNOWN for both destination orbits.**
No finite-suite passing candidate, graph-positive policy or independently
checked UNSAT refutation has been obtained from these experiments.

## Why selective pooling?

Two independently audited four-case matrix experiments on the same one-bit
routing semantics found that the complete union of CaDiCaL195 and
MapleChrono necessary lasso clauses gave the best periodically sampled
invalid policy in three of four cells in one configuration, but only two
of four in another. More sound constraints do **not** automatically
improve short-budget SAT search.

This module tests clause selection while controlling for every original
source checkpoint. Within each of the four cells, generate exactly one
divergent CaDiCaL/Maple source pair. The pair, same graph, target, first-hop
branch and strict frozen residual masks, feeds all selected variants.

## Mathematical safety, exact policies and equivalence

Every source has a complete independently audited CNF with canonical one-hot
legal routing actions, the target's first-hop branch, and source-reachable
deterministic failing walks. The original \`lasso_portfolio.build\` audits
each source CNF **before creating a new output**. It reconstructs each
necessary negative-selector clause independently from source injection
through a reachable prefix and the first repeated complete arrival state.
Only canonical duplicated or logically subsumed clauses can be removed
without changing the full portfolio's Boolean solution set.

The optional \`--selection\` argument is purely about which independently
necessary lasso clauses to **retain**. It never adds any routing selector,
source identity, local-state restriction, extra bit, rank variable,
arbitrary-arrival delivery obligation or solver-internal conflict.

Available modes:

- \`all\` (default): unmodified complete union, deduplicated exactly.
- \`lossless\`: remove a clause \(C\) **only** when an already retained
  shorter clause \(D\) satisfies \(D\subseteq C\). Since \(D\) subsumes
  \(C\), the resulting CNF is logically equivalent to the complete union.
  The exact discarded clause index and retained dominator index are
  written to \`dominance.jsonl\`; the complete clauses and indices are
  independently reproducible from the full original portfolio.
- \`shortest-half\`: begin with the lossless minimal family and retain at
  most \(\lceil N/2\rceil\) unique clauses, prioritized by number of
  distinct selected selectors and deterministic lexical tie-breaking.
- \`balanced-half\`: begin with the lossless minimal family, retain at
  most \(\lceil N/2\rceil\) clauses, allocate quotas evenly between the
  two independently divergent source backends, and prioritize one short
  witness per **static residual mask** before filling each source's
  remaining quota. Fill any leftover slots with globally shorter clauses.

In the half-size modes, all retained constraints are independently
necessary for every correct policy, but some necessary constraints
are omitted. They are logically **weaker** than the full portfolio;
no equivalence claim is made. The exact selection algorithm records
the number of input-unique clauses, exact duplicate removals,
subsumed clauses, other omitted clauses, selected witnesses,
complete mask families and both source provenance records.

Every generated portfolio is a new standalone
\`source-reachable-lasso-v1\` checkpoint. The existing independent
\`lasso_witness.audit\` byte-reconstructs the entire CNF from its
witnesses, selectors and branch constraint; the existing search
runner independently audits the starting portfolio again upon resume.
SAT backend conclusions and solver memory are **never** imported.

## Reproducible four-case comparison

Use the four exhaustive cells t0-b0, t0-b1, t3-b0, t3-b1. The target-0
frozen suite contains **2,701** residual masks; target 3 contains
**2,181**. Within each cell the source CaDiCaL and MapleChrono
searches use the same seed, legal routing domain, normalized first-hop
branch, and bounded active time. The complete source policy hash
trajectories are compared to verify actual diversification, rather than
treating backend labels or integers as independent observations.

For a matched experiment:

\`\`\`bash
python -m pip install python-sat==1.8.dev24 z3-solver==4.13.3.0
python -m unittest discover -s k11122 -p 'test_*.py' -v
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_batch.cpp -o lasso_batch
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_quality.cpp -o lasso_quality
g++ -O3 -std=c++17 k11122/verify.cpp -o verify
python k11122/portfolio_matrix.py \
  --output evidence-selective --cases all --selective-modes \
  --scanner "$PWD/lasso_batch" --scorer "$PWD/lasso_quality" \
  --verifier "$PWD/verify" \
  --source-seconds 5 --continuation-seconds 7 --seed 20261103
\`\`\`

One unchanged CaDiCaL source and four starting portfolio variants are
available for controlled continuation (CaDiCaL only; full union;
shortest-half; balanced-half), plus a MapleChrono-only baseline.
The complete \`lossless\` alternative is structurally checked without
wasting an additional identical solver continuation unless its CNF
actually differs from full. All continuations use the same CaDiCaL
backend/seed, the same fast first-witness refinement method, exactly the
same active-search budget, and the same sampled-historical-policy
evaluation schedule. Source-search, portfolio-construction, audit,
resume and candidate-evaluation overhead are reported separately.

The historical-best score is the count of frozen failure masks
with at least one target-connected nonself source failing delivery,
as independently rechecked in Python, sampled on model 1 and every
eighth model. This is **not** a model of the final strengthened CNF
or a complete positive routing table. Different bounded runs and
heuristics need multiple genuinely divergent trajectories before
statistical conclusions; the four graph partitions are **not**
random independent samples. Every terminal solver state remains
UNKNOWN unless independently certified.

The GitHub workflow runs with a strict hosted job timeout, never
retries indefinitely, and retains source code, source certificates,
every selected witness, full CNFs, exact source/selection hashes,
policy quality, compilation and regression logs, and a SHA-256 index.
No recurring task, payment or new compute service is created.

A graph-positive claim still needs a valid legal policy for **both
target orbits**, independently replayed over all **524,288** residual
masks and all connected sources. A negative claim still needs a
verified complete reduction and independently checked UNSAT proofs
for **both exhaustive first-hop branches of one destination orbit**.
Neither may be inferred from a timeout, a smaller CNF or better
historical raw-policy quality.
