# K11122 equal-active-time certified transfer — verified three-seed pilot

**Date: 3 November 2026.** Both target-0 and target-3 one-bit
routing-orbit classifications remain **UNKNOWN**. There is no
independently verified full-graph positive policy and no checked
impossibility refutation. The established packet-state bound is 2–3.

## Provenance and integrity

- Tested implementation commit:
  \`e5f58c71066fa4f80c14c9e593b36db017cd2bbe\`.
- Successful GitHub Actions run:
  https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41571722545
- Full downloadable exact checkpoint / verifier / audit artifact:
  https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41571722545/artifacts/13201846928
- ZIP file size **57,638,534 bytes**, SHA-256:
  \`c3409a6d1efc2900914bdb82cf950375684ce6814484b7b7faf2a45c9f44e9c8\`.
- The downloaded archive exactly matched GitHub's digest, passed full
  ZIP CRC checking, and **every one of its 5,271 SHA256SUMS-indexed files**
  passed SHA-256 verification. There are 5,272 ZIP entries in total,
  the additional entry being SHA256SUMS itself.
- **78 tests passed** with pinned Python-SAT 1.8.dev24, Z3 4.13.3.0 and
  CaDiCaL195, including model semantics, rank and independent literal
  replay, corruption rejection, crash-safe journal and immutable-generation
  recovery, interval logic, certificate transfer, equal active-search
  clock, and observed solver-counter accounting.
- Full source and destination CNFs, each global selector row and first-hop
  branch, every lasso clause and source-reachable witness, and each
  committed journal prefix were independently reconstructed and audited.
  The unchanged full-graph C++ \`verify.cpp\` was rebuilt and hashed.

The original run used the branch with the corrected immutable-generation
timing implementation. The previous CI attempt caught an integration
error in the generation checkpoint path; it was fixed before the
above successful run. No ambiguous earlier failed test is counted as
successful evidence.

## Experimental design: distinguish search versus import

The existing \`--seconds\` default continues to include setup,
auditing, import, and search (\`--budget-scope total\`).
Only for this explicit experiment, \`--budget-scope search\` begins
the \`--seconds\` countdown **after** complete certified source audit,
opposite-branch import and initial crash-safe checkpoint publication.
Search then includes SAT solving, candidate replay, independent lasso
checking and ongoing checkpoints. Every source setup and repeated warm
import is **fully billed separately**; there is no claim that this
overhead vanishes or that the work was free.

The experiment constructs and audits one independent branch-0
source bundle per destination orbit, each with the strict frozen
unconditional residual family:

| Source | Budget | Independently audited source lasso clauses | Clauses transferred to branch 1 | Branch-vacuous |
| --- | ---: | ---: | ---: | ---: |
| Target 0, 2,701 residuals | 12 sec | 55,940 | **55,196** | 744 |
| Target 3, 2,181 residuals | 8 sec | 34,176 | **34,078** | 98 |

Each source bundle is reused in the benchmark, but **each warm trial
re-audits the entire original source CNF and every witness before import**.
Exactly the original local-availability semantics are preserved. The
transferred constraints are necessary negated-selector lasso clauses,
never branch restrictions, arbitrary-arrival obligations or solver verdicts.

## Main three-seed comparison — target 0, branch 1

For each of seeds **20261103, 20261104, and 20261105**, compare one
cold run against one independently audited, clause-transferred run.
Both use 12 seconds of active SAT/walk search, target 0, branch 1,
the same 2,701 masks, pinned CaDiCaL195, and the deterministic
one-in-eight shortest/diverse hybrid with at most 96 new independent
witnesses per complete SAT assignment.

The table evaluates **only the last raw SAT policy** after the run,
on every connected nonself source in all frozen residual masks.
The last policy is not best-so-far, and the score is not an exhaustive
full-graph positive verification.

| Seed | Cold raw models | Warm raw models | Cold last-policy failing masks | Warm last-policy failing masks | Cold failing source obligations | Warm failing source obligations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 20261103 | 557 | 564 | 568 | 580 | 1,445 | 1,555 |
| 20261104 | 585 | 561 | 595 | 545 | 1,568 | 1,481 |
| 20261105 | 573 | 558 | 617 | 526 | 1,687 | 1,525 |
| **Mean** | **571.7** | **561.0** | **593.3** | **550.3** | **1,566.7** | **1,520.3** |

In two of three seeds the warm final raw policy fails fewer residual
masks. In the third it fails more. Mean distinct failing residuals
decrease by **7.25%** and mean failing connected source obligations
decrease by **2.96%**. These are *descriptive outcomes on three
last raw policies*, not statistically sound evidence of improved
solver convergence or graph resilience.

Equal-active-budget mean raw assignments are **1.87% lower** with
transfer (561.0 versus 571.7). The respective mean independently
observed SAT conflicts are **2,258.3** with transfer versus
**2,132.3** cold (+5.91%). Those cumulative values are collected
from worker-generation-aware monotone SAT samples and may
underestimate work lost at externally bounded timeouts. More
conflicts and fewer raw models do not by themselves establish a
stronger or weaker mathematical result.

The cold search learned 53,380 / 56,064 / 55,008 necessary witnesses.
The warm search imported **55,196** audited clauses on each seed
and learned 54,048 / 53,786 / 53,472 further clauses, with
no missing, duplicate or unjustified imported witness.
All six target-0 searches remained **UNKNOWN**; zero finite-suite
candidates were verified.

### The actual amortization tradeoff

Per-run average preparation:

- Cold branch 1: **0.046 seconds**.
- Independently audited transfer: **5.796 seconds**, including
  source CNF/witness checking, import and initial checkpoint.
- The exact source itself required a separate 12-second bounded
  source search plus audit; it was reused for all warm seeds.

Measured full per-run wall time, including final audit/export,
was approximately **14.23 seconds cold** versus **22.07 seconds
with transfer**; the full source-construction cost is additional.
Therefore this three-seed experiment does **not** show an
end-to-end computational speedup or that the source cost is
fully amortized. Separating setup from search was essential
to make the solver-window comparison valid, not to conceal
preparation time.

## Independent target-3 cross-orbit control

One target-3/branch-1 matched pair (seed 20261103, 8 seconds of
active search; 2,181 masks) produced:

| Diagnostic | Cold | With transferred constraints |
| --- | ---: | ---: |
| Raw SAT assignments | 375 | 370 |
| Independently audited transferred clauses | 0 | **34,078** |
| New independent lasso clauses | 35,904 | 35,424 |
| Last-policy failing masks | 414 | 396 |
| Last-policy failing connected sources | 1,141 | 1,106 |
| Mean per-run preparation | 0.061 s | 3.457 s |

Both statuses remain **UNKNOWN**. One seed is only a sanity check,
not robust evidence for target-3 convergence.

## What the experiment actually establishes

1. Sound cross-branch constraints are reusable on two distinct
   destination orbits, and destination CNFs continue to pass
   independent reconstruction.
2. The new explicit search-only clock makes comparisons fair in
   **active search time** while preserving all true setup costs.
3. The cross-branch import changes solver trajectories, but
   **no complete finite-suite policy emerged**, and no certifiable
   impossibility result was obtained.
4. The last-policy failure score suggests a *possible* benefit
   worth further investigation, but is neither monotone progress
   nor statistically supported proof.
5. The current costly per-trial independent audit is an important
   remaining scalability bottleneck. A **content-addressed,
   independently verified immutable transfer cache**, with
   inexpensive hash checking on reuse and strict original witness
   provenance, could make larger multi-seed campaigns practical
   without trusting unverified external clauses.

All commands, source files, binary hashes, mask lists, SAT solver
samples, candidate policies, witness files and crash-safe
checkpoints are in the successful Actions artifact. The complete
reference setup and command-line reproduction instructions are in
[AMORTIZED_TRANSFER.md](AMORTIZED_TRANSFER.md).

A positive still needs independently verified legal policies for
**both** destination orbits across all 524,288 residual masks,
including every connected nonself source. A negative still needs
complete model-sound encoding and independently checked UNSAT
refutations for both exhaustive first-hop branches of one orbit.
None of these conditions is satisfied in this experiment.

No recurring automation, indefinite search, or uncontrolled retries
were created.
