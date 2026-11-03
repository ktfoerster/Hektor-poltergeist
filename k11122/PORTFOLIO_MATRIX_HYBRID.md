# K11122 — shorter-budget hybrid-witness four-case cross-check

**Research status:** perfect resilience with one mutable packet bit remains
**UNKNOWN** for both destination orbits on \(K_{1,1,1,2,2}\). The
established upper/lower packet-state bound remains 2–3 states.
A raw SAT assignment, a better historical finite-suite score, solver
timeout, or uncertified UNSAT is **not** a proof.

## Scientific purpose

The earlier target-0/branch-0 portfolio pilot combined necessary
source-reachable failing-walk clauses from actual divergent CaDiCaL195
and MapleChrono trajectories, and the pooled continuation found a
historical sampled policy failing fewer masks than either source-only
continuation. It was one target/branch case. The present experiment
repeats that controlled design across **all four original partitions**:

| Destination orbit | Source-first-hop branch | Strict target-specific residuals |
| --- | --- | ---: |
| 0 (singleton) | 0 | 2,701 |
| 0 (singleton) | 1 | 2,701 |
| 3 (doubleton) | 0 | 2,181 |
| 3 (doubleton) | 1 | 2,181 |

Within *each* case, two bounded source searches use identical graph,
target, branch, frozen masks, one-bit packet-state transition
semantics and exactly-one legal global policy selectors. CaDiCaL195
and MapleChrono supply different SAT search backends, but this alone
does not establish independent exploration. The experiment compares
the **complete SHA-256 of actual routing tables** at identical
source raw-model indices, and reports whether their first observed
model truly diverged. No independence is inferred from different
backend labels or integer seeds.

## Sound clause union

Each complete source CNF and all of its witnessed necessary clauses
are independently audited **before any portfolio output is written**.
The \`lasso_portfolio.py\` builder independently reconstructs each
source-reachable failing walk and canonical negative-selector clause.
It rejects source bundles unless graph, target, branch and **entire**
strict mask family match. It deduplicates only identical logically
necessary clauses and reconstructs a fresh CNF:

\[
  F_{\text{portfolio}} =
  F_{\text{one-hot legal selectors}} \land
  F_{\text{same first-hop branch}} \land
  \bigwedge_{C\in C_1\cup C_2} C.
\]

The base clause family, normalized immediate destination delivery,
source-injection observation, local live-port information and
full repeated arrival configuration are unchanged. No second mutable
bit, packet source identity, persistent router state, arbitrary-arrival
delivery, rank assumption, remote failure oracle or forbidden
unreachable cycle is introduced.

**Do not pool different first-hop branches in the same portfolio.**
Although individually verified lasso clauses can be necessary
across branches, cross-branch reuse is a different separately
tested operation. Here each case is self-contained and exactly
matches its branch to avoid introducing that extra dimension.

No backend-internal learned clauses, solver conclusions, preferred
actions, source solver states or uncertified UNSAT results enter the
new CNF. The newly reconstructed portfolio is independently
re-audited byte-for-byte. Every continuation uses the existing
\`lasso_search.py run --resume\` path to import the *entire*
audited starting witness CNF, not a live solver state.

## Matched bounded continuation

After the two source searches and complete portfolio construction,
the experiment runs three continuations on the **same** target and
branch:

1. Start from the CaDiCaL source CNF.
2. Start from the MapleChrono source CNF.
3. Start from the deduplicated CaDiCaL+MapleChrono portfolio CNF.

Each continuation uses CaDiCaL195 with identical integer seed
20261103, the same hybrid lasso-witness mode (every eighth model
short/diverse), a maximum of 96 independently checked necessary
clauses per SAT assignment, and **8 seconds of active search**.
The two original source searches are **6 seconds each**. Import,
source CNF checking, portfolio creation and first durable checkpoint
publication are *outside* the active search budget and their costs
are independently measured. Their full costs are never concealed
as a speedup. The GitHub job itself has a hard **20-minute**
execution limit; no job is scheduled recursively or indefinitely.

For each continuation the benchmark records both raw SAT assignments
and the independently replayed *best historically sampled* routing
table, on the complete target-specific frozen residuals. The best
diagnostic scores the first raw assignment and every eighth thereafter;
the score is explicitly **not the minimum across all assignments**.
The preserved original final raw-policy score is also checked.
No historical policy is assumed to satisfy the terminal CNF after
further necessary clauses are learned.

The primary within-case measure is reduction in the number of
residual masks on which at least one connected nonself source
fails to deliver, under the **same target and branch**. Scores
between different target orbits, different source branches or
different mask-family sizes are **not** interpreted as direct
statistical evidence. The four cases are not four independent
random samples; they cover four mathematically defined partitions
under a single chosen solver seed and time budget.

## Full independent audit

\`lasso_portfolio_matrix.py\` independently verifies:

- Each source complete terminal CNF and witnessed lasso stream,
  including full target/branch and mask-family agreement.
- The exact source policy hash record sequence and whether
  the two backends *actually* produced different complete tables.
- Portfolio source provenance, clause deduplication, rebuilt CNF,
  and all source/portfolio SHA-256 fingerprints.
- Each resumed continuation's exact source manifest and formula
  hashes, retained witness count, journal prefix and final complete CNF.
- The best historical raw policy's source file/hash and independent
  Python literal-walk replay across all connected source obligations.
- Honest total preparation time, source generation, deduplication,
  active search, and the final retained research artifacts.

The new \`test_lasso_portfolio_matrix.py\` tests input bounds and
corruption handling, exact policy hash indices, best-score
interpretation, and portfolio construction under **branch 1**
as well as the previously tested branch 0. All prior
semantic/compilation/regression tests remain mandatory in CI.

## Reproduce

Python 3.12, pinned \`python-sat==1.8.dev24\` and
\`z3-solver==4.13.3.0\`, Ubuntu 24.04 runner:

\`\`\`sh
python -m pip install python-sat==1.8.dev24 z3-solver==4.13.3.0
python -m unittest discover -s k11122 -p 'test_*.py' -v
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_batch.cpp -o lasso_batch
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_quality.cpp -o lasso_quality
g++ -O3 -std=c++17 k11122/verify.cpp -o verify

python k11122/lasso_portfolio_matrix.py \
  --output /path/to/new-evidence-folder \
  --scanner "$PWD/lasso_batch" --scorer "$PWD/lasso_quality" \
  --verifier "$PWD/verify" \
  --source-seconds 6 --search-seconds 8 \
  --seed 20261103 --best-interval 8
\`\`\`

The output directory must not exist. The wrapper has strict
per-run and whole-hosted-job time bounds and writes
\`latest-matrix.json\` after each fully audited case, then
\`portfolio-matrix-summary.json\` after all four. Complete
source and portfolio CNFs, source-reachable witnessed
certificate streams, exact failure masks, best-policy tables,
replay results, untrusted C++ scorer checks, raw-model
SHA-256 histories, seed/backend configuration, time
accounting, and provenance are retained for independent
reproduction.

**Classification endpoints remain unchanged.** A mathematical
positive needs an independently verified, legal one-bit
policy for both target orbits, replayed on all **524,288**
residual masks and every connected nonself source.
A negative needs a sound complete reduction and
independently checked UNSAT proof for both exhaustive
first-hop branches of at least one orbit. No ordinary
search score can replace these requirements.

## Completed cross-check and interpretation

This script is the **distinct six-second-source / eight-second-continuation**
experiment with the **hybrid witness selector** used in all three
continuations, independently validated by GitHub Actions run
[41624732089](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41624732089).
It was compared with a concurrent **seven/nine-second** matrix experiment
whose continuations used the fast first-witness selector. Different budgets
and witness-selection methods mean the two runs are **not controlled
replicates**. The complete comparative results and both independently
SHA-256-checked evidence archives are documented in
[PORTFOLIO_MATRIX_COMPARATIVE_RESULTS_20261103.md](PORTFOLIO_MATRIX_COMPARATIVE_RESULTS_20261103.md).

This workflow is manual-dispatch only, to avoid launching another duplicate
research search on merge. The already completed CI run validates its original
execution code, and the trigger/file-name changes above do not affect any
computation, proof or checker.
