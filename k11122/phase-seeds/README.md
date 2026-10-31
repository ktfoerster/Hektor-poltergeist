# Phase-hint policies

These four complete legal tables are invalid candidates retained only as SAT
branching-phase hints. `sat_search.py` validates every row and records the
table SHA-256, but adds no clause or assumption from a hint. Every selector
remains free, so this does not restrict the semantic search space.

| table | source run/artifact | exhaustive failures |
|---|---|---:|
| `t0-b0.tsv` | 41168770051 / 13030766546 | 90,269 / 2,979,236 |
| `t0-b1.tsv` | 41170473396 / 13031138748 | 48,912 / 2,979,236 |
| `t3-b0.tsv` | 41168770051 / 13031225368 | 234,653 / 2,937,186 |
| `t3-b1.tsv` | 41170473396 / 13031407324 | 150,813 / 2,937,186 |

Fresh builds of the unchanged verifier and the independent counterexample
miner reproduced the exact obligation and failure counts for all four files
before they were committed. `SHA256SUMS` is checked by the hosted workflow.
