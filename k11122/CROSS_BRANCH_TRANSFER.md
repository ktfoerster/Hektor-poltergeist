# Reuse independently certified failing-walk clauses across first-hop branches

**Purpose:** transfer valid *unconditional* counterexamples between the
two exhaustive physical-first-hop branches of the **same destination orbit**.
This does not change any routing policy, model, or graph classification.
The one-bit problem remains UNKNOWN for both target orbits.

## Semantic justification

The global Boolean routing policy uses exactly-one legal
(outgoing port, emitted bit) choice per source-injection or transit
observation. An independently reconstructed failing walk specifies
the source, a connected residual mask, the common injection, the
entire source-reachable prefix and a closing cycle of complete
(vertex, incoming port, bit) arrival configurations. A policy
retaining every selected action on that trace necessarily repeats
that execution and fails. Therefore its negative-selector clause
is a **necessary condition independent of which first-hop branch
originally generated the policy**.

The branch restriction is used only to partition candidate policies.
**Never transfer the branch assertion itself**, a solver conflict
clause, an UNSAT status, a source policy, or an inferred symmetry.
No source-specific transit, extra state, TTL, arbitrary-arrival
delivery or forbidden unreachable cycle is introduced.

For the destination branch, the opposite physical first-hop selectors
of the distinguished injection row are forbidden by that branch's
exactly-one and branch assertion. A transferred failing-walk clause
that contains a negative literal of such a forbidden selector is
already true for every destination-branch policy; it can be dropped
without weakening any necessary condition. All other clauses are
independently replayed and transferred, with exact duplicates removed.

## Strict audit and provenance

\`lasso_transfer.py\` accepts ONLY a complete independently audited
source \`formula.cnf\`, \`manifest.json\`, \`masks.json\`,
\`selectors.json\` and \`witnesses.jsonl\`. The existing
\`lasso_witness.audit\` reconstructs the **entire source CNF**
including exactly-one policy selectors, the source branch assertion,
and each source-reachable witness. The importer separately rechecks
each transferred witness and its canonical negative-selector clause.
The frozen sorted mask family must match **exactly**; source and
destination must have the same graph and target and opposite branch
0/1. Disconnected or malformed witnesses and cross-target inputs
are rejected. Recompute the source witness-file hash after streaming
to detect unexpected concurrent modification.

The destination solver independently constructs its own selector
rows and *destination* branch assertion; it imports no solver
conclusion. Each transferred witness is appended to the destination's
crash-safe journal, then the full destination CNF is independently
reconstructed and audited. The committed journal and manifest record:
source manifest/CNF/witness hashes, all source code dependencies,
source/destination branches, scanned certificate counts, selected
and branch-vacuous clauses, and explicit migration details. New
source versions require \`--allow-audited-migration\`, not silent
acceptance.

The transfer is supported in \`journal\` and \`generations\`
checkpoint modes; \`--resume\` and
\`--transfer-opposite-bundle\` cannot be combined in one run.
Once a transferred checkpoint is committed, normal audited \`--resume\`
works and retains the already imported necessary clauses.

## Verified local preflight

The original hosted target-0 branch-0 20-second artifact contained
**84,576 fully audited failing-walk clauses**. Pure independent
analysis on the exact **2,701-mask** suite found that, for target-0
**branch 1**, **83,329** clauses remain nonvacuous, **1,247** are
already true due to the opposite first-hop restriction, and no
duplicate clause was present. This is evidence of transferable
necessary constraints, **not a mathematical classification**.

The bounded hosted workflow uses preserved run
[41550722195](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41550722195)
as the independent input. A separate target-3 branch-0 source
bundle has 40,608 certified clauses over its own **2,181 masks**.
The workflow rebuilds the unchanged independent \`verify.cpp\`,
compares a cold target-0 branch-1 search against one importing those
necessary constraints, and attempts a bounded target-3 branch-1
transfer. Results are not comparable unless audit, hashes, exact
mask families and source constraints are all verified.

## Reproduction

With Python 3.12, pinned \`python-sat==1.8.dev24\` and
\`z3-solver==4.13.3.0\`, and the original preserved source bundle
extracted to \`/path/to/source-run/first\`:

\`\`\`bash
python -m unittest discover -s k11122 -p 'test_*.py' -v
g++ -O3 -std=c++17 k11122/verify.cpp -o verify
g++ -O3 -std=c++17 k11122/lasso_batch.cpp -o lasso_batch
python k11122/lasso_search.py audit --output /path/to/source-run/first
python k11122/lasso_search.py run --target 0 --branch 1 \
  --seconds 25 --walker cpp --seed 20261103 \
  --batch-binary "$PWD/lasso_batch" --verify "$PWD/verify" \
  --witness-selection hybrid --hybrid-every 8 \
  --transfer-opposite-bundle /path/to/source-run/first \
  --allow-audited-migration --output /tmp/branch1-imported
python k11122/lasso_search.py audit --output /tmp/branch1-imported
\`\`\`

The duration includes independent source auditing and import; it is
**not** 25 seconds of fresh SAT solving after import. Any SAT or
UNSAT response before independent full-graph replay/proof checking
remains finite-suite or uncertified. To establish graph positivity,
both target orbits need a legal table passing the independent C++
replay of all 524,288 residuals and all connected sources. To
establish graph impossibility, independently checked refutations of
both exhaustive branches of at least one destination orbit are
required, along with a sound complete translation.
