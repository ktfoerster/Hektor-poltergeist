# Graph/SAT compute smoke test

This repository provides a small, reproducible GitHub Actions computation
pipeline. It enumerates **labelled simple graphs** and tests their
3-colourability via a genuine external SAT solver (MiniSat).

This is an **infrastructure demonstration**, not an encoding of perfect
resilience, touring, or any result for a paper. In particular, a 3-colourability
certificate says nothing about the existence of resilient forwarding rules.

## What runs

The workflow `.github/workflows/graph-sat.yml` starts four independent Linux
jobs. Each job builds DIMACS CNF instances, runs MiniSat, checks SAT assignments
against the graph, and cross-checks the outcome using an independent
backtracking 3-colouring implementation. It saves one JSON Lines results file
and a summary JSON per shard as downloadable GitHub Actions artifacts.

The initial configuration (`experiment.json`) checks all 1,024 labelled
simple graphs on five vertices. It is intentionally small so that the first
run can establish that the pipeline works.

## Launch and monitor

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

## Configuration and limits

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
timeout. For expensive research instances, we would replace the example
enumerator with the project's actual formal encoding and adjust sharding,
timeouts, checkpoints, and independent certificate verification. GitHub-hosted
jobs have a platform execution limit and should not be treated as durable
multi-day processes.

## Local reproduction

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

## Interpretation and security

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
