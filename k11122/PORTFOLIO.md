# K11122: multi-solver necessary-lasso certificate portfolio

**Scientific status: UNKNOWN for both destination orbits**, one-bit perfect
resilience on K11122 unresolved with the established 2–3-state bounds.

## Idea and safety

Multiple independently verified SAT trajectories from CaDiCaL195 and
MapleChrono discover different invalid routing policies. Each source-reachable
failing execution yields a logically necessary negative-selector lasso clause.
Unlike the solver's learned conflict clauses, these certificates are valid
for **every legal routing policy** of the same graph/target and frozen residual
under the same normalized one-bit routing semantics.

\`lasso_portfolio.py\` imports **only** independently certified source-reachable
failing-walk clauses from 2–12 completed source checkpoints with **identical
graph, destination orbit, physical first-hop branch, sorted failure-mask
family, and selector numbering**. It calls \`lasso_witness.audit\` on the
**complete source CNF and every source witness before any output is
created**. It then rechecks every witness against the independent
\`checked_clause\` interpreter, deduplicates exact negative-selector clauses
and verifies source hashes again after streaming. No solver verdict, source
phase policy, old branch constraint beyond the common newly constructed
destination branch, solver internal clause, rank variable or private
packet state is imported.

The resulting **new** complete, byte-exact CNF consists of the independently
reconstructed one-hot base and common physical-first-hop branch assertion,
followed by unique necessary lasso clauses. Its manifest contains each
source CNF SHA-256, manifest SHA-256, witness SHA-256, backend, seed, phase
hash if present, source witness counts, deduplication counts, and a complete
independent source audit result. The new portfolio is independently audited
again as a standard \`source-reachable-lasso-v1\` checkpoint. Its
\`progress.raw_models\` and scheduling offset are zero; no solver-memory
restoration or source-trajectory continuation is claimed.

The current normal \`lasso_search.py run --resume <portfolio>\` pipeline
can then restart from the portfolio. It independently rechecks and imports
the complete CNF, reconstructs every witness, and learns fresh necessary
clauses. Source-version changes still require explicit audited migration.

## Controlled pilot

The bounded GitHub workflow \`.github/workflows/k11122-portfolio.yml\` first
runs the full regression suite. It constructs two different initial
target-0, branch-0 source checkpoints, one using CaDiCaL195 and the other
MapleChrono, each with nine seconds of active search on the identical
**2,701-mask** target-0 frozen residual family. It checks actual model
divergence via complete policy hashes, not backend names alone.

Three **12-second active-search** comparisons use the same seed,
CaDiCaL195 continuation backend, 96-witness hybrid batch bound,
and best historical-policy evaluation every eighth raw SAT assignment:
from the CaDiCaL source, from MapleChrono source, and from the union.
A repeated standalone source run is not mislabeled as an independent
policy trajectory. Every final CNF is independently reconstructed and
the sampled best historical policy replayed in Python on every connected
source of every frozen mask. Portfolio preparation, audit time, source
generation and search time are recorded separately.

**These are necessary clauses, not a mathematical proof**. A complete
positive requires independent full replay of a legal table for both
target orbits across all **524,288** residual masks and all connected
nonself sources. A negative requires verified complete encoding and
independently checked refutations of both disjoint physical-first-hop
branches for at least one orbit. A finite-suite raw SAT policy, short
lasso clauses, terminal UNKNOWN or uncertified UNSAT establish neither.

## Reproduce

Python 3.12, \`python-sat==1.8.dev24\`, \`z3-solver==4.13.3.0\`:

\`\`\`sh
python -m pip install python-sat==1.8.dev24 z3-solver==4.13.3.0
python -m unittest discover -s k11122 -p 'test_*.py' -v
g++ -O3 -std=c++17 k11122/lasso_batch.cpp -o lasso_batch
g++ -O3 -std=c++17 k11122/lasso_quality.cpp -o lasso_quality
g++ -O3 -std=c++17 k11122/verify.cpp -o verify
python k11122/lasso_portfolio.py --target 0 --branch 0 \
  --sources /path/to/validated-cadical /path/to/validated-maple \
  --output /path/to/new-portfolio
python k11122/lasso_search.py audit --output /path/to/new-portfolio
python k11122/lasso_search.py run --target 0 --branch 0 \
  --seconds 12 --budget-scope search --walker cpp \
  --batch-binary "$PWD/lasso_batch" --verify "$PWD/verify" \
  --witness-selection hybrid --resume /path/to/new-portfolio \
  --output /path/to/new-run
\`\`\`

The new portfolio output must not exist. It is **not** a newly proved
impossibility certificate. All artifact source files and hashes, inputs,
complete C++ and Python checker source, exact CNFs, witnesses, frozen masks,
best historical policies and independent audit outputs are retained.

No recurring automation, unbounded solver run or self-hosted compute is used.
