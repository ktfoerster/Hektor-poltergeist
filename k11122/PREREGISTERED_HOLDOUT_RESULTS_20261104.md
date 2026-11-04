# K11122 — pre-registered backend-aware clause-selection holdout

**Completed 4 November 2026. Mathematical status: UNKNOWN for both
destination orbits of \(K_{1,1,1,2,2}\).** The established one-bit/two-state
question is unresolved between the previously established 2–3-state
bounds. No complete finite-suite candidate, legal full-graph
positive policy, or independently checked UNSAT refutation resulted.

## 1. Executive findings

This is the first **pre-registered transfer test** of the preceding
backend-specific selective-portfolio training run rather than another
post-hoc choice of the best clause subset.

- The *training-fixed* selector beat complete pooling on **5/8**
  held-out case/backend comparisons, lost on **2/8**, and tied
  on **1/8**, the case in which the preselected strategy was
  itself the full pool. Thus the proposed backend-aware rule
  **does not consistently generalize** to genuinely new
  legal phase-search trajectories.
- Both static half-pool controls, evaluated *after* the fixed
  choices had been registered, beat full pooling in **7/8**
  held-out comparisons each. **These are exploratory post-hoc
  observations**, not another pre-registered success measure.
  The training-selected rule underperformed even a
  simpler fixed half strategy on some test cases.
- For all four cells, the new source phase changed the
  CaDiCaL195 complete routing-policy hash trajectory relative
  to a phase-free same-seed control, and the two source
  SAT backends actually diverged. Divergence was observed in
  the **first model** for each phase control, and by **model
  2** for the source-backend pair. Distinct phase/seed labels
  alone were not used as evidence of diversification.
- **Every complete raw SAT assignment** in each continuation
  was evaluated for failure-mask quality. This corrects the
  previous experiment's every-eighth-model sampling limitation.
- All **24 held-out continuation searches** ended
  \`UNKNOWN\`, with **zero complete finite-suite candidates**.
  A raw policy generated before later necessary-clause learning
  is not a satisfying model of the terminal CNF.

## 2. Provenance and independent verification

- **Training data:** original independently audited cross-backend
  report \`SELECTIVE_CROSS_BACKEND_RESULTS_20261104.json\`,
  pinned to Git blob SHA-1
  \`8c56fffbefb2d8c8117db65a0ffc45dc0ba91454\`,
  byte-exact SHA-256
  \`06046ad17386a81656b2f44c653503ff1caf0639ab99b3bbd89661a7d4872864\`.
  The training run was [41811555234](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41811555234),
  source commit
  \`172f039767657c5f83ffff8bd9e36bface2f5ce3\`.
- **Tested holdout code commit:**
  \`b7a6a50fe46174bccdc30a040cfa186aeaa039a0\`.
- **Successful Actions run:**
  https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41815045982
- **Full immutable reproducibility artifact:**
  https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41815045982/artifacts/13314726995
- **Downloaded ZIP SHA-256:**
  \`50640e3665cee09486e59847e1ebb051ce363555ae86920ff7ce7d7e152ee9d0\`.
  The exact archive matched the GitHub-supplied digest. Independent
  streaming decompression read and CRC-checked **all 7,220 ZIP
  entries**; independently recomputed SHA-256 checks matched
  **all 7,219 manifest-indexed files**, with no duplicates, missing
  members or unexpected extra files. The remaining entry was the
  \`SHA256SUMS\` manifest itself.
- **113 regression tests passed**, including exact routing
  semantics, branch restriction, lasso certificate corruption,
  independent source-reachable traces, phase-only legal hints,
  cached and ordinary audit, checkpoint recovery,
  deduplicated and subsumed portfolios, and the new
  immutable-training/pre-committed-decision tests.
- The hosted second audit independently reconstructed all **48
  saved bundles** per case: four phase-free control sources, eight
  phase-guided source checkpoints, twelve selected portfolio
  CNFs, and twenty-four terminal continuation CNFs. Every
  source lasso witness and final CNF was verified independently;
  all 24 best raw policies were independently replayed in Python.
  The unchanged full-graph \`verify.cpp\` was rebuilt.
  No actual positive full-graph replay was triggered because no
  complete finite-suite candidate was obtained.

## 3. Holdout design and pre-registration

The training report was checked **byte-for-byte** to its pinned Git
blob before output creation. Its 8 case/backend decisions were
chosen by minimum training *sampled* historical failure-mask
score, with a fixed tie-breaking order: shortest-half, then
balanced-half, then all. The file
\`holdout/precommitted-selection-plan.json\`, containing these
choices, the training SHA-256, fixed seed, phase salts and source
commit, was written **before any holdout search**.

All holdout source/continuation policies used new *legal
phase-only preferences*, not new constraints:
- Source phase: hash salt **20261104**.
- Continuation phase: hash salt **20261105**.
- Solver seed: **20261104**, versus 20261103 in training.
- A phase-free **same-seed** CaDiCaL control was run separately
  to test actual phase-induced divergence.

There were four exact graph cells: t0-b0 and t0-b1
(target 0, **2,701** strict frozen masks); t3-b0 and
t3-b1 (target 3, **2,181** strict frozen masks). For each
cell, one CaDiCaL195 and one MapleChrono source search
ran for **4 seconds active time** on the same legal phase
hint and the same graph/masks/branch. Each was
independently audited.

Three fresh portfolios (full, globally shortest-half,
source/mask-balanced-half) were derived from **that same
source pair**, never chosen using holdout outcomes.
All of their clauses are independently necessary
source-reachable complete failing-walk clauses; half
portfolios simply omit some of them. No rank variables,
extra packet memory, arbitrary-arrival guarantee,
source-aware transit, or backend-internal solver
conflict clauses were introduced.

Each of the three portfolios was independently
continued with CaDiCaL195 and MapleChrono:
**4 cells × 3 portfolios × 2 backends = 24 held-out
continuations**. Each received **5 seconds active
SAT/walk search time**, the same legal continuation
phase hint and numerical seed within the cell, and
the same fast first-witness learner with a 96-new-lasso
bound per SAT model. Source construction and full
source/portfolio audit/import costs are additional
and separately recorded. The experiment is bounded
by a GitHub job limit of 20 minutes.

In contrast to training, \`best_interval=1\` evaluated
**all** raw SAT assignments, and independently verified
the best *historically observed* routing table against
every connected nonself source on every frozen mask.
These are **not terminal satisfying assignments**, and
the test still uses the *same* frozen failure-mask
family as training; it tests unseen solver trajectories,
**not unseen graph failures**.

## 4. Primary held-out comparison

The primary score is the number of static residual masks
for which at least one connected nonself source loops.
**Lower is better.** The strategy selection was fixed from
training, but no preference may be inferred for the
mathematical K11122 classification.

| Cell | Backend | Preselected mode | Full pool failure masks | Preselected failure masks | Change: selected minus full |
| --- | --- | --- | ---: | ---: | ---: |
| t0-b0 | CaDiCaL195 | balanced-half | 754 | **693** | −61 |
| t0-b0 | MapleChrono | shortest-half | **551** | 617 | +66 |
| t0-b1 | CaDiCaL195 | shortest-half | 688 | **626** | −62 |
| t0-b1 | MapleChrono | shortest-half | 562 | **491** | −71 |
| t3-b0 | CaDiCaL195 | shortest-half | 533 | **483** | −50 |
| t3-b0 | MapleChrono | all | 437 | 437 | 0 |
| t3-b1 | CaDiCaL195 | balanced-half | **517** | 524 | +7 |
| t3-b1 | MapleChrono | shortest-half | 363 | **301** | −62 |

**Pre-registered outcomes:** 5 improvements, 2 regressions,
1 trivial tie (the selected arm was \`all\`). Of the **seven
nontrivial preselected half strategies**, **5 improved**
the holdout score and **2 regressed**. This is an
engineering signal but insufficient to claim a generally
optimal backend-aware strategy.

The most striking failure is t3-b0/MapleChrono:
training selected the full pool, which had beaten
the half variants in the original training run;
on the new phase trajectory the full pool scored
437 while shortest-half scored 321 and balanced-half
375. This directly exposes training-set dependence.
At t0-b0/MapleChrono, the preselected shortest-half
performed worse than the full baseline (617 vs 551).

## 5. Secondary, explicitly post-hoc table

Because all three fixed arms were run, we can examine
their observed heldout quality. **Do not interpret the
best of these as an independently validated policy
selector.** It is a diagnostic for future hypotheses.

| Cell | Backend | All | Shortest-half | Balanced-half |
| --- | --- | ---: | ---: | ---: |
| t0-b0 | CaDiCaL195 | 754 | 695 | **693** |
| t0-b0 | MapleChrono | 551 | 617 | **535** |
| t0-b1 | CaDiCaL195 | 688 | **626** | 670 |
| t0-b1 | MapleChrono | 562 | **491** | 541 |
| t3-b0 | CaDiCaL195 | 533 | **483** | 527 |
| t3-b0 | MapleChrono | 437 | **321** | 375 |
| t3-b1 | CaDiCaL195 | 517 | **514** | 524 |
| t3-b1 | MapleChrono | 363 | **301** | 338 |

In this single holdout, **both** static half-pool
strategies improved on full pooling in **7/8**
case/backend comparisons. The exceptional cases
differ: shortest-half regressed at t0-b0/MapleChrono,
whereas balanced-half regressed at t3-b1/CaDiCaL.
The pre-registered *backend-aware* selector did not
reproduce those improved counts. This motivates a
**new, independently pre-registered future test**
of fixed short portfolios rather than a retroactive
claim of generalization.

## 6. Clause sizes, computation and audit overhead

| Case | Full unique certified clauses | Shortest half | Balanced half |
| --- | ---: | ---: | ---: |
| t0-b0 | 35,474 | 17,737 | 17,737 |
| t0-b1 | 37,033 | 18,517 | 18,517 |
| t3-b0 | 33,198 | 16,599 | 16,599 |
| t3-b1 | 34,317 | 17,159 | 17,159 |

On the observed runner, per-continuation preparation
(including independent portfolio re-auditing and initial
SAT setup, excluding both upstream source searches and
portfolio construction) took approximately
**3.30–3.81 seconds** with full pools versus
**1.51–1.71 seconds** with half pools.
The new source searches, phase controls, 3 portfolio
constructions per cell, and all independent audits
still represent additional computation, not a free
speedup. Active solver budgets were equal nominal
five-second windows, not matched CPU instructions.

The trained and holdout historical policy-quality
metrics are also **not directly interchangeable**:
training evaluated every eighth model, holdout every
model, which is intentionally a stricter evaluation.

The full artifact preserves all raw-model quality
sample streams, complete policy hashes, source and
continuation phase hints, globally normalized legal
action rows, sorted frozen mask lists, every necessary
source-reachable lasso witness, complete CNFs,
original + newly acquired independent audit results,
raw SAT conflict/propagation counters, resource
measurements and SHA-256 provenance.

## 7. Conclusions and next research steps

This is an informative **negative generalization
result** for the specific preselected selector,
not a mathematical impossibility result about the
underlying K11122 problem. The backend-aware winner
from one short training run is not a reliable automatic
portfolio choice when the SAT search trajectory changes.
On the other hand, both static half-selection rules
were promising across this new set of trajectories,
with some regressions and real import-cost benefits.

Any further experiment should use genuinely new source
trajectories, pre-register the hypotheses *before
seeing those results*, and optimize for actually
obtaining a **complete finite-suite candidate or
independently checkable refutation**, not merely
historical invalid-policy failure counts.
The most relevant next controlled experiment is
a pre-registered static shortest-half versus full
comparison on new legal phase salts and an independent
synthesis backend. Do not claim statistical
significance from the four mathematically defined
cells and one held-out seed.

A genuine **positive** requires a complete legal
one-bit policy for **both** destination orbits,
independently verified across **all 524,288
failure masks** and all target-connected nonself
sources. A genuine **negative** requires a sound
complete reduction and independently checked
UNSAT refutations of **both** exhaustive
first-hop branches of at least one orbit.
Neither was obtained here.

The exact commands, pinned selection rule and
semantics are documented in
[PREREGISTERED_HOLDOUT.md](PREREGISTERED_HOLDOUT.md).
The tested bounded workflow is
\`.github/workflows/k11122-preregistered-holdout.yml\`.
No recurring automation, unbounded solver run, or
self-hosted compute deployment was created.
