# Hektor-poltergeist: K11122 research and Graph/SAT demo

This repository contains two separate computations:

- **[K11122 research](k11122/README.md):** SAT-based synthesis of one-bit
  forwarding policies for the seven-vertex graph K_{1,1,1,2,2}, relevant to
  the SAND 2027 touring-model research and its reproducibility artifacts.
  The implemented model is destination-based delivery under link failures;
  read its precise obligations before relating results to other touring models.
- **[Graph-colourability demonstration](#graph-colourability-demonstration):**
  a small MiniSat/GitHub Actions infrastructure example. Its colouring
  certificates establish no routing or perfect-resilience result.

## K11122: start here

K11122 is K7 without edges 34 and 56. Targets 0 and 3 represent the two
destination orbits; two packet states mean one bit.

| Purpose | Documentation and implementation |
|---|---|
| Mathematical model, completeness, destination orbits and result meanings | [Research README](k11122/README.md) |
| Boolean encoding, dependencies and local search commands | [BOOLEAN_CNF.md](k11122/BOOLEAN_CNF.md), [SAT runner](k11122/sat_search.py) |
| Deterministic DIMACS export, hashes and independent proof checking | [PROOF_CNF.md](k11122/PROOF_CNF.md), [exporter and reference RUP checker](k11122/proof_cnf.py), [watched-literal RUP engine](k11122/rup_watch.py) |
| Independent exhaustive policy replay and counterexample checking | [C++ verifier](k11122/verify.cpp), [counterexample miner](k11122/counterexample_miner.cpp) |
| Fixed four-case experiment | [SPLITTING.md](k11122/SPLITTING.md), [split/model replay program](k11122/split_cnf.py) |
| Bounded adaptive follow-up, coverage ledger and proof audit | [ADAPTIVE.md](k11122/ADAPTIVE.md) |
| Campaign outcomes and retained evidence | [Campaign log](k11122/CAMPAIGN_20261031.md), [campaign report](K11122_BOOLEAN_SAT_CAMPAIGN_REPORT_20261031.md), [checkpoints and provenance](k11122/checkpoints/), [proof validation](k11122/PROOF_VALIDATION_20261031.json), [adaptive validation](k11122/ADAPTIVE_VALIDATION_20261101.json), [full-size smoke record](k11122/ADAPTIVE_FULLSIZE_SMOKE_20261101.json) |

### Reproduce and inspect

From the repository root, use Python 3.12 and g++:

```sh
python -m pip install z3-solver==4.13.3.0 python-sat==1.8.dev24
python -m unittest discover -s k11122 -v
```

Then follow the linked encoding/export documentation for bounded local runs,
using new output directories as specified there. The exact hosted commands,
solver settings, budgets and artifact names are maintained in these workflows:
[Boolean SAT search](.github/workflows/k11122.yml),
[proof pipeline validation](.github/workflows/k11122-proof.yml),
[retained-CNF long proof run](.github/workflows/k11122-proof-long.yml),
[four-case pilot](.github/workflows/k11122-split.yml), and
[adaptive pilot](.github/workflows/k11122-adaptive.yml).
The Boolean search is manual-only; other workflow triggers are documented in
their YAML files. A root-README-only change does not trigger these workflows.

### Evidence and open question (1 November 2026)

The [31 October four-case run 41235267137](https://github.com/ktfoerster/Hektor-poltergeist/actions/runs/41235267137)
completed all four jobs successfully, including 25 regression tests per job.
**All four solves returned `UNKNOWN` with `solve timed out` after their
1,200-second budgets.** This verifies execution of the experiment, not SAT,
UNSAT, or a new mathematical classification. The four cases exhaust only the
retained target-0, branch-0 parent; branch 1 and target 3 are outside this pilot.

That run provides `split-input-0` through `split-input-3` and corresponding
`split-result-*` artifacts, including formula metadata, hashes, logs and
`certification.json`. They were available on 1 November, with 30-day retention
(expiry 30 November 2026); download them from the run page while available.
Committed checkpoints/provenance and validation records above remain available
independently of Actions artifact retention. Small-instance regression and
proof-pipeline checks are implementation evidence, not K11122 impossibility
certificates; rejected candidate policies likewise prove only their own failure.

The one-bit question remains unresolved for both destination orbits in the
reported campaign; its stated 2–3-state bounds are unchanged. Interpret outputs
as follows (full definitions and caveats remain in the research documentation):

- `SAT_FINITE_CNF` satisfies only the selected residual constraints. A positive
  graph result needs independent replay on all 524,288 live-edge masks and all
  connected nonself sources for **both** destination orbits.
- `CNF_UNSAT_RUP_VERIFIED` certifies the hashed CNF, subject to correctness of
  the routing encoding. Refuting an orbit needs both exhaustive source branches
  (or a branch-free refutation); four child refutations here would cover only
  branch 0. The checker does not formally verify the encoding itself.
- `UNKNOWN`, `UNSAT_UNCERTIFIED`, crashes and failed replay do not establish
  impossibility. A green Actions run alone is never a mathematical certificate.

## Graph-colourability demonstration

This demonstration provides a small, reproducible GitHub Actions computation
pipeline. It enumerates **labelled simple graphs** and tests their
3-colourability via a genuine external SAT solver (MiniSat).

This is an **infrastructure demonstration**, not an encoding of perfect
resilience, touring, or any result for a paper. In particular, a 3-colourability
certificate says nothing about the existence of resilient forwarding rules.

### What runs

The workflow `.github/workflows/graph-sat.yml` starts four independent Linux
jobs. Each job builds DIMACS CNF instances, runs MiniSat, checks SAT assignments
against the graph, and cross-checks the outcome using an independent
backtracking 3-colouring implementation. It saves one JSON Lines results file
and a summary JSON per shard as downloadable GitHub Actions artifacts.

The initial configuration (`experiment.json`) checks all 1,024 labelled
simple graphs on five vertices. It is intentionally small so that the first
run can establish that the pipeline works.

### Launch and monitor

1. Open the repository's **Actions** tab and select **Graph SAT smoke test**.
2. Choose **Run workflow** to launch a run, or modify `experiment.json` on
   `main` to trigger one automatically.
3. Follow the four matrix jobs in Actions. After completion, download the
   `graph-sat-shard-*` artifacts. If your ChatGPT GitHub connection permits
   these actions, it can inspect the run, logs, and artifacts as well.
4. Keep `experiment.json` changes on a separate branch if you want review
   before starting jobs. The workflow triggers on changes to that file on
   `main`.

The connection currently supports reading workflow jobs/logs and downloading
artifacts. Direct workflow dispatch is not assumed to be available: modifying
the configuration through a GitHub commit is another triggering mechanism.

### Configuration and limits

`experiment.json` contains:

```json
{
  "experiment": "graph-3colourability-demo",
  "vertices": 5,
  "start_mask": 0,
  "graph_count": 1024,
  "shard_count": 4
}
```

- `vertices`: 1 through 7; no claim is made about general larger graphs.
- `start_mask`: first labelled-graph bit mask to inspect.
- `graph_count`: consecutive masks to inspect, at most 32,768 per run.
- `shard_count`: fixed at 4 to match the workflow matrix.

The program checks that the interval lies within the full labelled-graph
space of `2^(vertices choose 2)` masks. Every interval index is assigned to
exactly one shard using its relative index modulo four.

Each hosted job has a 60-minute timeout and each MiniSat invocation a 30-second
timeout. The separate K11122 implementation above supplies its own formal encoding,
search budgets, checkpoints, and independent verification. GitHub-hosted
jobs have a platform execution limit and should not be treated as durable
multi-day processes.

### Local reproduction

On Ubuntu 24.04 with Python 3 and MiniSat installed:

```sh
sudo apt-get update
sudo apt-get install -y minisat
python3 -m unittest discover -s tests -v
python3 scripts/graph_sat.py --config experiment.json --shard 0 --output results/shard0
```

The runner needs only Python standard-library modules, plus the external
`minisat` binary. The workflow uses `ubuntu-24.04` and installs MiniSat through
the Ubuntu package manager. The resulting `summary.json` records the solver
banner, Python version, Git commit, and run ID; the JSON Lines file includes
all cases and their SAT witnesses when applicable.

### Interpretation and security

- Do not infer results about fast failover or perfect resilience from this
  smoke test.
- For real UNSAT research claims, use a proof-producing SAT solver and verify
  its proof with an independent checker. The independent small-graph colouring
  backtracker in this demo is a correctness check, not a general SAT proof.
- The workflow uses read-only repository permissions, no repository secrets,
  bounded input settings, and no arbitrary shell commands sourced from the
  configuration.
- Public repositories disclose committed code, inputs, and logs. Do not put
  unpublished sensitive research data in this repository unless publication
  is intentional.
