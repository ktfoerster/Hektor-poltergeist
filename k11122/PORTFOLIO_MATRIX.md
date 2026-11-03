# K11122: matched portfolio matrix across both targets and first-hop branches

**Scientific status remains UNKNOWN.** This is a bounded, independently
audited engineering experiment on the one-bit source-reachable failover model,
not a certificate of feasibility or impossibility.

## Research question

The original pooled-source experiment used target 0, branch 0 and found a
better sampled *historical raw SAT policy* than either single-source
continuation. Does this observation repeat for all four exhaustive cells?

| Destination orbit | First-hop branch 0 | First-hop branch 1 |
| --- | --- | --- |
| Target 0 (singleton orbit) | t0-b0 | t0-b1 |
| Target 3 (doubleton orbit) | t3-b0 | t3-b1 |

The exact frozen residual families remain 2,701 masks (target 0) and
2,181 masks (target 3), formed by the existing strict merger of the
pinned proof-search checkpoint sources.

## Controlled source construction

For each of the four cells, \`portfolio_matrix.py\` generates a
CaDiCaL195 source certificate and a MapleChrono source certificate,
each from the same legal normalized one-bit routing-selector CNF,
same distinguished physical-first-hop constraint, same mask family,
same numeric seed 20261103, same necessary-witness hybrid selection
period eight, and **seven seconds of active SAT/walk search**.

The program independently audits each complete CNF and its every
source-reachable failing-walk witness. It compares complete policy
SHA-256 traces at every shared SAT model index using
\`lasso_divergence.first_divergence\`. Merely changing the SAT backend
does **not** count as diversification unless a genuine model hash
difference is observed.

If the first two source traces do not actually diverge, a bounded
third source search with a legal, deterministic hash-based
phase preference is attempted. Its preferences are not constraints.
A cell with no verified divergence is flagged as such and may
still be pooled safely, but is **not reported as independently
diversified search evidence**.

## Pooling and correctness

\`lasso_portfolio.build\` audits both selected source checkpoints before
creating any portfolio files. It requires identical graph, target,
physical first-hop branch, sorted residual masks and global
one-hot selector numbering. Every imported clause is independently
reconstructed from a full source-injected failing trace, prefix
and first repeated complete arrival state.

Only necessary, canonical, negative-selector lasso clauses are
deduplicated and retained. The resulting standalone checkpoint
contains independently rebuilt base selector clauses and exactly
one new branch assertion, not source-solver internal conflicts,
UNSAT verdicts, phase hints, policy restrictions, rank variables
or any additional packet memory. The full resulting portfolio
CNF is independently audited before use.

## Three controlled continuation arms per cell

Each of the four cells compares *CaDiCaL-only*, *second divergent
source only*, and *pooled portfolio* checkpoints. **All three**
continuations use CaDiCaL195, seed 20261103 and a common
**nine-second active-search budget**. Preparation, independent
source auditing, portfolio construction and checkpoint import are
reported separately.

Importantly, continuation uses the **same fast first-witness
selection mode for all three arms**. This neutralizes the inherited
hybrid modulo-clock difference that can otherwise confound
comparisons between source checkpoints containing different
numbers of prior raw SAT models. The source-creation searches
may use the hybrid mode to discover distinct certificates.

Best observed historical raw policies are scored at the first SAT
model and every eighth model thereafter. The C++ scorer is
untrusted; every published best is independently replayed in
Python on *every connected source in every frozen mask*.
Historical raw policies may fail clauses learned later; their scores
are **not SAT certificates for the terminal CNF** and are not full
graph-positive policies. This is explicitly a best-among-sampled
score, not best among all raw SAT assignments.

## Reproduction and strict limits

Hosted on Ubuntu 24.04 with Python 3.12, pinned
\`python-sat==1.8.dev24\` and \`z3-solver==4.13.3.0\`.
One-time exact setup:

\`\`\`sh
python -m pip install python-sat==1.8.dev24 z3-solver==4.13.3.0
python -m unittest discover -s k11122 -p 'test_*.py' -v
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_batch.cpp -o lasso_batch
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_quality.cpp -o lasso_quality
g++ -O3 -std=c++17 k11122/verify.cpp -o verify
python k11122/portfolio_matrix.py \
  --output results-four-cells \
  --scanner "$PWD/lasso_batch" --scorer "$PWD/lasso_quality" \
  --verifier "$PWD/verify" \
  --source-seconds 7 --continuation-seconds 9 \
  --seed 20261103 --cases all
\`\`\`

To inspect or debug one case, specify
\`--cases t0-b0\`, \`t0-b1\`, \`t3-b0\` or \`t3-b1\` with a
new output directory. The Python wrapper adds a bounded
external process timeout beyond each bounded internal search.
The hosted GitHub Actions job additionally has a hard
20-minute limit. No recurring automation is created.

The output \`matrix-results.json\` reports the four audited
cell-level comparisons, full policy-hash divergence, source
certificate counts, portfolio deduplication, imported and new
necessary-clause counts, search-only and preparation time,
observed solver conflicts, terminal CNF hashes, and best
independently checked historical policy scores. The workflow
rechecks every complete CNF, journal and best-policy file again
before uploading the complete immutable evidence and a
SHA-256 index. The frozen mask inputs and complete test/solver
source remain in the artifact.

## Interpretation limitations

A single seed and one short budget per arm are not enough to
establish a robust convergence advantage. A better sampled
historical raw policy is evidence of a different invalid search
trajectory, **not** a routing solution. Portfolios require the
up-front cost of two source searches and repeated audits; this
cost is recorded and must be weighed against any improvement
in continuing from the union.

Mathematical positive: a legal policy for **both destination
orbits**, checked independently over all **524,288** residual
masks and every connected nonself source. Mathematical negative:
a complete sound SAT reduction with independently checked
refutations of **both exhaustive physical-first-hop branches of
at least one destination orbit**. Neither may be inferred from
a finite-suite candidate, raw solver SAT, an UNKNOWN timeout,
a best sampled score, or an uncertified UNSAT response.
