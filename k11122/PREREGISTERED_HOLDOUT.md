# K11122 — pre-registered backend-aware portfolio holdout

**Mathematical classification:** UNKNOWN for both target orbits. This is a
bounded engineering experiment on the same frozen finite residual suites,
not a proof of the existence or impossibility of one-bit perfect resilience
on K11122.

## Hypothesis and separation of training from holdout

The previous independently audited GitHub Actions run
[41811555234](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41811555234)
compared complete, shortest-half and balanced-half necessary-clause
portfolios with CaDiCaL195 and MapleChrono, across all four
target/first-hop cells. Its source JSON is **pinned byte-for-byte**
to Git blob SHA-1
\`8c56fffbefb2d8c8117db65a0ffc45dc0ba91454\`.
The holdout runner checks this exact Git blob hash before creating
any output. It selects the lowest training historical failing-mask
score for each of the eight case/backend combinations, breaking ties
in a fixed order: shortest-half, balanced-half, all.

These eight choices are written, with training data SHA-256 and
workflow provenance, into \`precommitted-selection-plan.json\`
**before** any new source-search or continuation starts. The rule
never reads new holdout scores. Three portfolios are nevertheless
generated in the holdout for a fair comparison: full, shortest-half,
and balanced-half. The preselected arm is the **primary** test
against full, while post-hoc best-of-three is reported only as
a diagnostic upper bound, not as validation.

The fixed training choices are:

| Orbit / first-hop branch | CaDiCaL195 preselected | MapleChrono preselected |
| --- | --- | --- |
| t0-b0 | balanced-half | shortest-half |
| t0-b1 | shortest-half | shortest-half |
| t3-b0 | shortest-half | all |
| t3-b1 | balanced-half | shortest-half |

Thus **7 of the 8** preselected arms use a half-size portfolio,
and the t3-b0/MapleChrono case deliberately keeps full pooling.
Any previously observed training advantage might disappear.

## New independent search trajectories

The holdout uses numerical seed **20261104**, rather than the
training run's 20261103. However seed alone did not create
independent SAT policies in earlier experiments. Therefore the
holdout also uses complete *legal* phase-only preferences generated
deterministically with hash salt **20261104** for sources and salt
**20261105** for continuations. Both phase inputs are checked
against the global legal one-hot table and are **not clauses,
routing restrictions, assumptions, hidden state, or source-specific
transit rules**. Each of the two source backends receives exactly
the same new source-phase file in a given cell.

A separate 1-second CaDiCaL phase-free control checks whether
the source phase actually changes complete policy SHA-256 traces.
CaDiCaL195 versus MapleChrono source traces are independently
compared, as are the continuation-backend traces for each
frozen portfolio. No independence is claimed unless the
**actual policy hashes diverge**. This tests transfer to
new search trajectories, **not to unseen failure masks**:
the source and holdout use the same 2,701 (target 0) or 2,181
(target 3) independently pinned residuals. The four graph
partitions and two backends do not constitute random
statistical samples.

## Strict matched conditions

For each t0-b0, t0-b1, t3-b0, t3-b1, generate:

- One legal phase-free control: 1 second active search;
- One CaDiCaL and one MapleChrono source checkpoint, using
  *identical new phase preference* and 4 seconds active time each;
- Three separately reconstructed and fully audited portfolios
  from that **exact same source pair**, using the original
  independently checked source-reachable failing-walk clauses;
- Two continuation backends × three fixed portfolios =
  **six** 5-second active search continuations using the same
  seed and same continuation-phase file per case.

The SAT learner uses the unchanged fast first-witness
C++ oracle with up to 96 necessary source-reachable
lasso clauses per raw model. All *complete* raw SAT policies
are scored (\`--best-interval 1\`), not merely model 1
and every eighth as in training. The best historical table
is independently replayed over **every connected nonself source
and every frozen failure mask** using the separate Python
checker. Every source, portfolio and terminal CNF is
independently reconstructed and audited, including complete
source injection, reachable prefix and first repeated
full arrival state, and the exact first-hop branch.

The priority order of scientific endpoints is:

1. A complete finite-suite candidate, independently verified;
2. Best historical raw policy's zero/nonzero failed mask and
   failed connected-source counts, checked across the *entire*
   frozen residual suite, considering **all** raw policies;
3. Actual policy-hash divergence;
4. Measured SAT effort, raw models, source generation,
   full CNF audit/import preparation and active search times.

A sampled or all-model **historical best** is a candidate
from an *earlier* CNF, not necessarily a satisfying assignment
of the final refined CNF. A finite-suite SAT or raw UNSAT
would still need independent graph replay or proof checking,
respectively. No backend/selection mode is assumed to win
simply because it won the training run.

## Reproduce the bounded hosted pilot

Ubuntu 24.04, Python 3.12 and pinned
\`python-sat==1.8.dev24\` and \`z3-solver==4.13.3.0\`.

\`\`\`bash
python -m pip install python-sat==1.8.dev24 z3-solver==4.13.3.0
python -m unittest discover -s k11122 -p 'test_*.py' -v
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_batch.cpp -o lasso_batch
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_quality.cpp -o lasso_quality
g++ -O3 -std=c++17 k11122/verify.cpp -o verify
python k11122/holdout_backend_selection.py \
  --output independent-holdout-evidence \
  --scanner "$PWD/lasso_batch" --scorer "$PWD/lasso_quality" \
  --verifier "$PWD/verify" \
  --cases t0-b0,t0-b1,t3-b0,t3-b1 \
  --source-seconds 4 --continue-seconds 5 --control-seconds 1
\`\`\`

The precommitted plan, every phase hint, source and portfolio
checkpoint, exact terminal CNF, SHA-256 provenance, independently
checked lasso witness, full-policy score and certificate audit
remain in the new evidence directory. The GitHub CI job runs
a second independent 48-bundle audit and records
\`independent-holdout-summary.json\`, even if the preselected
heuristic performs poorly. A 20-minute hosted job limit, strict
per-search active budgets and finite subprocess bounds prohibit
uncontrolled compute. No recurring automation is created.

**Mathematical status requirements remain unchanged.**
A positive requires a legal policy for **both target orbits**
passing the unchanged full-graph C++ verifier on all
524,288 failure masks and every connected nonself source.
A negative requires independently verified complete encoding
and checked UNSAT refutations of **both exhaustive first-hop
branches** for at least one destination orbit. Neither is
entailed by this holdout or its historical policy quality.
