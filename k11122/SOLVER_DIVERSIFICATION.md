# K11122: deliberate SAT search-trajectory diversification

**Research classification: UNKNOWN for both target orbits.** One mutable
packet bit may or may not suffice on K_{1,1,1,2,2}. The established
2–3-state bound does not change because a solver explores more assignments
or returns a different invalid routing policy.

## Why seed-only repetitions were misleading

The previously audited best-observed-policy pilot observed *identical*
SHA-256 fingerprints for every common sampled SAT policy across three
different CaDiCaL seed values. Full-source-audit and cached-search
treatments also traversed identical common policy-hash prefixes.
Consequently, the three seed runs were not independent solver
trajectories. Best-policy differences were explained by one run
reaching a later model index, not by different search choices.

## The new, nonbinding search dimensions

The rank-free lasso SAT runner now supports
\`--phase-policy PATH\`. This must be a complete legal routing table
covering every source-injection and transit observation, with a
legal live next hop and emitted packet bit in every row. It is
validated **before opening the output directory** and copied as
\`phase-policy.tsv\`, with its exact SHA-256, row count and
selector-literal count preserved in the audited result manifest.
The table is used only by the existing PySAT
\`solver.set_phases()\` polarity-preference API. It adds **no**
unit clauses, assumptions, frozen actions, extra state, or
source-dependent transit observations. The same exact global
one-hot policy selector CNF and physical-first-hop partition
remain in force.

The reproducible generator \`lasso_phase_preferences.py\` creates
three deterministic, complete and legal preference tables:
\`first\`, \`last\`, and keyed \`hash\`. All are compatible with the
chosen physical first-hop branch, though even those preference
choices are *not* constrained in SAT. For hash mode, a fixed
SHA-256 digest of the salt and observation determines the
preferred action; it does not rely on Python randomized hashing.
Immediate delivery remains the only normalization.
A test forces a preference away from the chosen first-hop bit
and confirms a different model remains SAT with an identical CNF
fingerprint.

As a separate search dimension, the underlying policy encoding
already supports \`cadical195\`, \`glucose42\`, and
\`maplechrono\`. The experiment changes the solver implementation
but not the SAT formula or legal routing semantics.

## Controlled hosted experiment

The workflow \`.github/workflows/k11122-diversification.yml\`
builds the independent C++ graph verifier and complete
rank-free scanner, and runs the whole regression suite with
Python 3.12, \`python-sat==1.8.dev24\` and
\`z3-solver==4.13.3.0\`. It generates and audits *one common
branch-0 source checkpoint per target orbit*, with the original
strict frozen residual-mask families:

- Target 0: 2,701 masks.
- Target 3: 2,181 masks.

Each target-0 variant resumes from the exact same immutable
source \`manifest.json\`/CNF and receives **12 seconds active
search**, with the same seed 20261103, 96 necessary clauses
per SAT assignment, the same one-in-eight hybrid walker,
identical branch 0, and the same best-observed policy
evaluation interval 8. Preparation/audit costs are reported
separately.

The five target-0 variants are: CaDiCaL no preference,
CaDiCaL \`first\` preference, CaDiCaL \`hash\` preference,
Glucose42 no preference, and MapleChrono no preference.
Three target-3 controls use CaDiCaL without preference,
CaDiCaL \`hash\`, and MapleChrono, each with 9 seconds active
search. All run from the *same target-specific starting CNF*
and use exactly the same selector rows and necessary-clause
soundness model.

Every emitted failure lasso is independently replayed in Python;
every destination terminal CNF is independently rebuilt and
audited. The \`--best-interval 8\` historical best policy
is independently checked over **every connected source in
every frozen mask**. It is explicitly a historical raw
candidate, not a SAT model of the final CNF and not a
verified perfect-resilience algorithm.

## Genuine divergence criterion

\`lasso_divergence.py\` reads the complete
\`cpp-batches.jsonl\` scanner records. It compares the exact
64-character SHA-256 of the **complete legal routing table**
for every *common model index* in a pair of runs. It reports
the first observed differing model index, lengths of matching
prefixes, and a flag distinguishing "actually diverged" from
"same shared prefix, perhaps just different length". This
addresses the false appearance of three independent trials
when all policy traces were identical. A solver may fail to
diversify despite different preference tables or a different
backend: such results must be reported as *no observed
divergence*, not manufactured success.

The comparison additionally checks that every run imported
the same source checkpoint manifest hash and exact count
of independently checked necessary clauses, that target,
branch and residual suite match, and that any phase policy
was captured with its exact provenance and checksum.

**No proof is inferred from different model hashes, lower
failure counts, timeouts, or uncertified UNSAT.** A positive
still requires the unchanged exhaustive C++ verifier to
check legal policies for *both* destination orbits on all
524,288 residual masks and every connected source. A
negative still needs a complete proof-producing CNF
encoding and independently checked UNSAT proofs for
both exhaustive branches of at least one orbit.

## Reproduce

\`\`\`sh
python -m pip install python-sat==1.8.dev24 z3-solver==4.13.3.0
python -m unittest discover -s k11122 -p 'test_*.py' -v
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_batch.cpp -o lasso_batch
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_quality.cpp -o lasso_quality
g++ -O3 -std=c++17 k11122/verify.cpp -o verify
python k11122/diversification_pilot.py \
  --output ./evidence-diversification \
  --scanner ./lasso_batch --scorer ./lasso_quality \
  --verifier ./verify --source-seconds 9 \
  --search-seconds 12 --target3-seconds 9 --seed 20261103
\`\`\`

The experiment has a hard 14-minute GitHub job cap.
It uses no self-hosted runner or unmanaged recurring compute.
Every output retains its complete source CNF,
source-input provenance, exact policy-selection hashes,
untrusted ranking scores, independently checked best
historical policy, complete witnessed necessary-clause
journal, and exact manifest/SHA-256 evidence.
