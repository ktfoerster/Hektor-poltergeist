# K11122 — matched selective portfolio continuation across SAT backends

**Scientific classification remains UNKNOWN for both destination orbits.**
This experiment is an independently audited finite-suite SAT search
comparison, not a proof of one-bit resilience or impossibility.

## Motivation

The completed four-case selective portfolio pilot (GitHub Actions run
41776143667) found that a shortest-half pool of independently certified
source-reachable failing-walk clauses improved the *historically sampled*
raw-policy failure score relative to a full union in all four cells at one
short search budget. Earlier experiments produced inconsistent outcomes.
The next question is whether the observation generalizes when the
**continuation backend** changes while the **starting source CNFs do not**.

## Factorial design

For each of t0-b0, t0-b1, t3-b0 and t3-b1:

1. Fix the same graph, target, physical-first-hop branch and exact
   frozen strict residual family: **2,701** for target 0 and **2,181**
   for target 3. Preserve the normalized one-bit packet-state semantics:
   source injection, local live ports, incoming port, emitted bit,
   and first repeated full arrival configuration.
2. Generate exactly one CaDiCaL195 and one MapleChrono
   source certificate, with identical numerical seed 20261103,
   **4 seconds active-search time each**, common one-in-eight
   necessary lasso learner and no solver-state reuse. Independently
   reconstruct their complete CNFs and verify every reachable failing
   source trace.
3. Confirm whether their *actual full routing-policy SHA-256 traces*
   diverge at matching SAT model indices. Distinct backend names
   or integer seeds alone do not count as experimental independence.
4. Build exactly **three** new portfolios from the *same two audited
   source checkpoints*: complete deduplicated union (\`all\`),
   globally \`shortest-half\` and \`balanced-half\` with per-source
   mask coverage. Re-audit each complete portfolio CNF.
   The only intended selection change is which independently necessary
   source-reachable lasso clauses are retained. No SAT-learned conflict
   clauses, preferences, rank variables or branch assertions from
   another source are imported.
5. Continue each fixed portfolio with **both CaDiCaL195 and
   MapleChrono**, yielding six matched arms per graph case,
   **5 seconds active search each**, identical seed 20261103,
   fast first-witness C++ oracle, 96 new necessary clauses per
   SAT assignment and historical quality sampling on model 1 and
   every eighth model thereafter. Measure preparation, audit/import
   and full wall time separately rather than concealing it as
   free additional search.
6. Independently reconstruct **all** terminal CNFs, witness streams
   and journal prefixes, and replay each sampled best historical
   invalid policy against every connected nonself source on every
   frozen residual mask using Python (independent of C++ scoring).

**Control structure:** same starting source pair within a case;
same portfolio CNF across both continuation backends; same
continuation backend and seed across all three portfolio selections.
This removes the source-generation confound from clause-selection
comparisons. The two backend trajectories are individually checked
for actual divergence. It still does **not** turn backends or the
four mathematically defined partitions into independent random
statistical samples.

## Limits and endpoints

All 24 continuations have strict process timeouts, and the hosted
workflow has a **19-minute** job cap. The tested program refuses
to overwrite an existing evidence directory and preserves individual
source, portfolio and terminal bundles, exact CNF digests, policies,
witness JSONL, source provenance and independent audit logs.
An interrupted run leaves a \`latest-results.json\` checkpoint after
each complete case.

A historical sampled raw policy is neither guaranteed to satisfy
the final stronger CNF nor best among all raw SAT assignments; an
intermediate unsampled raw table may be better. Fewer failing masks
is an engineering quality metric, **not a mathematical positive**.
A verified graph positive requires a legal policy for **both target
orbits** passing the independent unchanged C++ verifier on all
**524,288** residual masks and every connected nonself source.
An impossibility result requires checked UNSAT refutations for both
exhaustive first-hop branches of at least one orbit, together with
a sound complete reduction. An unproven finite-suite SAT, timeout
or raw UNSAT does not meet either standard.

## Exact reproduction

Ubuntu 24.04, Python 3.12:

\`\`\`bash
python -m pip install python-sat==1.8.dev24 z3-solver==4.13.3.0
python -m unittest discover -s k11122 -p 'test_*.py' -v
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_batch.cpp -o lasso_batch
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_quality.cpp -o lasso_quality
g++ -O3 -std=c++17 k11122/verify.cpp -o verify

python k11122/selective_backend_robustness.py \
    --output evidence-matched-cross-backend \
    --scanner "$PWD/lasso_batch" --scorer "$PWD/lasso_quality" \
    --verifier "$PWD/verify" \
    --cases t0-b0,t0-b1,t3-b0,t3-b1 \
    --source-seconds 4 --continuation-seconds 5 --seed 20261103
\`\`\`

\`matched-backend-summary.json\` contains explicit source divergence,
portfolio source/selected-clause counts, each backend's historical
failure counts, per-case/backend policy-hash divergence, terminal
statuses, and exact replay-provenance references. The independent
CI audit adds \`independent-cross-backend-summary.json\`.
No recurring task or additional cloud compute provider is created.
