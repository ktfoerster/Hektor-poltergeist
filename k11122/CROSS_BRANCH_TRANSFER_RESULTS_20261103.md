# K11122 — certified cross-branch constraint reuse: completed experiment

**3 November 2026.** Mathematical status: **UNKNOWN for target 0 and
target 3**; every original exhaustive first-hop branch remains open.
The one-bit classification of \(K_{1,1,1,2,2}\) is unresolved, with
established bounds 2–3 packet states.

## Exact provenance

- Initial implementation commit:
  \`7a7b67105aa98b9828c218d6d402e4ae78282dc7\`.
- Self-contained, tested workflow revision:
  \`dec52846ae6189967d6a3e9f758a3128867ba599\`.
- **Successful GitHub Actions** run:
  https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41557986717
- Downloadable **complete source/checkpoint/verification artifact**:
  https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41557986717/artifacts/13195740800
- Artifact ZIP SHA-256:
  \`87dd21019488bf80a0e9ccd28316e167197d9a854ab82a57facceecdd9cb6171\`.
- The downloaded ZIP has **3,822 entries**, its CRC check passed, and
  **all 3,821 indexed file SHA-256 checks passed**. The one extra entry
  is the \`SHA256SUMS\` manifest itself. Paths inside that manifest are
  repository-root-relative (\`evidence/\`), whereas ZIP member paths are
  relative to the evidence folder.
- Python 3.12 with pinned \`python-sat==1.8.dev24\`,
  \`z3-solver==4.13.3.0\`. CaDiCaL195 and deterministic seed
  **20261103** throughout. Unmodified \`verify.cpp\` rebuilt and hashed.
- **All 73 regression tests passed**, including source-injection,
  literal-vs-SAT, witness and full-CNF corruption, reachable-prefix
  validity, disconnected-source cases, both target orbits, source
  version mismatch, cross-target/branch rejection, and recovery under
  both journal and immutable-generation checkpoint implementations.
- Both original source formulae and **all three final destination
  formulae** passed fresh full independent reconstruction and committed
  journal checks. No successful finite-suite candidate appeared, so
  no new full 524,288-mask positive replay was performed. No
  independently checked UNSAT proof was obtained.

## Self-contained construction and transfer

The first attempt to download an older GitHub Actions archive inside
a new job failed due to rejected GitHub token credentials. The
experiment was made **fully self-contained**, with no extra account
authorization or credential provisioning: the same successful hosted
run generates fresh 18-second target-0/branch-0 and 10-second
target-3/branch-0 source certificates, audits both, and transfers
only their necessary source-reachable failing-walk clauses to the
opposite branch. These are meaningful new conditions and **not**
solver conclusions, branch assertions or new restrictions.

The source and destination have **exactly the same frozen strict mask
union** per orbit (target 0: **2,701 masks**; target 3:
**2,181 masks**) and globally identical legal policy selector
numbering. The imported clauses include source injection,
reachability prefix and first repeated full arrival state, as
independently checked by \`lasso_witness\`. A clause already satisfied
by the opposite first-hop restriction is identified and not imported.

| Scope | Source branch 0 certified witnesses | Transferred useful clauses to branch 1 | Already satisfied by opposite branch |
| --- | ---: | ---: | ---: |
| Target 0, 2,701 masks | **82,464** | **81,360** | 1,104 |
| Target 3, 2,181 masks | **44,928** | **44,793** | 135 |

No clause was duplicated during transfer. The retained share is
**98.66%** and **99.70%** respectively. The source CNFs and
input manifest digests are recorded in each destination's
\`imported.opposite_branch_certificates\` provenance record.

## Bounded search, honest comparison

Target 0, branch 1: one cold run and one transferred run, each
**25 seconds end-to-end**, with the same hybrid interval 8,
96-necessary-witness cap, frozen masks, solver/seed and hardware.
The transferred run's budget **includes 8.503 seconds spent
independently auditing and importing source clauses**. These are
one-run, divergent CNF trajectories; raw-model throughput is NOT
a clean speedup measure for imported constraints.

| Measurement | Cold branch 1 | Transferred branch 1 |
| --- | ---: | ---: |
| Imported independently certified lasso clauses | 0 | **81,360** |
| Newly independently checked lasso clauses | 112,534 | 72,890 |
| Total independently certified lasso clauses | **112,534** | **154,250** |
| Raw SAT assignments examined | 1,173 | 760 |
| Independent audit/import time | 0 s | 8.503 s |
| SAT worker wall time | 5.259 s | 3.420 s |
| Walk/independent-check wall time | 11.863 s | 7.937 s |
| Final CNF variables | 4,736 | 4,736 |
| Final CNF clauses | 123,889 | 165,605 |
| Peak RSS (KiB) | 90,780 | 111,140 |
| Finite-suite candidates | 0 | 0 |
| Status | **UNKNOWN** | **UNKNOWN** |

The transferred run ended with **41,716 more independently certified
necessary clauses (37.1% above cold)**, but processed fewer SAT
assignments because imports consume budget and the formulas diverge.
This is a verified useful transfer, **not** evidence of faster
end-to-end convergence, and not an impossibility certificate.

Target 3, branch 1: a separate bounded **15-second** transfer
experiment imported **44,793** verified clauses, learned **45,139**
more, and ended with **89,932** certified lasso clauses,
**106,055** total CNF clauses and **6,240** selector variables. It
evaluated **471** SAT assignments, spent **4.525 s** auditing/
importing, produced no finite-suite candidate, and remains
**UNKNOWN**.

## Exact final CNF fingerprints

| Scope | SHA-256 of complete, independently reconstructed CNF |
| --- | --- |
| Source target0/branch0 | \`53d2dae95e2c39eb1fdae185222b79e8aded358c0a19167b7f9c46343a904396\` |
| Source target3/branch0 | \`7eed0e1e8375d5c41da0ec5525cc1aec961f98bb3198f752a79a25441868b451\` |
| Cold target0/branch1 | \`48413b7fa7b2cee3eb964c093a14993fbc5fa0926e2fe680720720397f817367\` |
| Transferred target0/branch1 | \`3802ed6a4db16b170da091d125255c261782dae65d5430a479946e78d1074de3\` |
| Transferred target3/branch1 | \`fc0f2dc1efa7ced22232dd37115b7ddb44c0b12cef88df562a6aed5c55c053d0\` |

## Reproduction and next work

Full commands, soundness argument, and explicit migration semantics are
in [CROSS_BRANCH_TRANSFER.md](CROSS_BRANCH_TRANSFER.md). The
successful workflow \`.github/workflows/k11122-branch-transfer.yml\`
contains all exact parameters and generates both source bundles
within the same run. Its artifact retains the entire committed
checkpoint, manifest, JSONL witnesses, masks, policy mapping,
independent audits, source hashes, verifier binary hash, timing and
dependency versions. No recurring automation or unbounded retry
was started.

**Next meaningful research step:** compare opposite-branch clause
transfer using a reusable audited *fixed source* across several solver
seeds and budgets where import overhead is reported separately.
Investigate incremental independent audit/certificate streaming so
source re-use can be amortized. A verified graph positive still needs
one complete legal policy for **both** destination orbits passing
unchanged exhaustive replay; a graph negative needs sound complete
translation plus independently checked refutations for **both**
exhaustive first-hop branches of at least one orbit. The current
work demonstrates neither.
