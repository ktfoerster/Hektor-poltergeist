# K11122 — independently checked shortest/diverse failing-walk selection

**Scope:** a search heuristic, not a new routing model or a classification
result. The two destination orbits and their two exhaustive first-hop branches
remain UNKNOWN unless new independently certified evidence changes this.

## Exact heuristic and why it is sound

The original \`lasso_batch.cpp\` first-witness mode remains the exact default
(\`--witness-selection first\`). Its output is byte-identical with the historic
four-argument scanner. No rank encoding, graph, verifier, policy selector,
injection condition or legal action changes.

The optional \`--witness-selection short-diverse\` does the following for
one completely specified SAT routing policy and one frozen family of residuals:

1. Scan **every** supplied static undirected failure mask, and **every
   connected nonself source** in that mask. Each source has the same local
   injection row and deterministic transit rows as the original model.
2. For each failing mask, keep the failure trace with the fewest **distinct
   global action selectors**; break ties by length of the complete execution,
   then by the deterministic source order. Its certificate includes injection,
   entire reachable prefix, and first repeated full
   \`(vertex, incoming-port, packet-bit)\` arrival configuration. Successful
   source revisits and unreachable loops remain legal.
3. Deduplicate identical selector sets. Remove a candidate if another
   candidate's selector set is a subset; the corresponding disjunction of
   negative selectors is already logically stronger. These removals are
   optimizations **of the batch**, not restrictions on the space of policies.
4. Of the remaining necessary clauses, select the shorter half first; fill
   the remainder greedily to maximize minimum Hamming distance between
   **static failure masks** in the selected batch. Ties prefer shorter clauses
   and deterministic mask/source order. The final batch remains bounded by
   the existing \`--max-new-per-round\` limit (default 96).

The necessary-clause argument has **not changed**. If the selected actions
on a finite failing execution remain fixed under the same residual mask,
the packet follows the same injection, reachable prefix and cycle and never
reaches the target. Thus a successful policy must change at least one
selector; the disjunction of their negations is logically necessary.
Selecting a subset of independently justified clauses cannot create an
unproved impossibility result or exclude a valid routing policy.

The C++ program is explicitly untrusted. Every emitted witness is replayed
and translated by the separate \`lasso_witness.checked_clause\` Python code
before entering SAT. The complete CNF is independently reconstructed at the
end and at every imported checkpoint. The unchanged independent \`verify.cpp\`
remains authoritative for full-graph positive verification.

## Correctness and benchmarking

The new differential suite checks the full generated witness against
independent literal walks, checks the per-mask shortest-source property,
strictly non-subsumed outputs, reproducible deterministic selection, legacy
four-argument output compatibility, target 0 and target 3, disconnected
sources, illegal selection modes, and integration with the journal SAT solver.
All original regressions remain mandatory.

The bounded CI experiment uses the same sorted strict **2,701-mask target-0**
family, target 0, physical-first-hop branch 0, seed 20261103, CaDiCaL195 and
25-second end-to-end search budgets, first vs short-diverse.
A separate 12-second target-3 branch-0 trial uses its own **2,181-mask**
family. The fixed-policy benchmark replays two previously rejected complete
routing tables over each target's exact masks, measuring clause length and
failure-mask diversity with a separate independent Python checker. It is a
structural comparison, not a SAT speedup claim. A full residual scan may be
slower than stopping at the first 96 failing masks, so throughput **must be
measured**, not assumed to improve.

All new outputs retain complete source hashes, exact masks, selected policy,
solver seed/backend, selector table, checked witness JSONL, final CNF, atomic
journal, independent reconstruction report, and hashed Actions artifacts.
Source changes require explicit audited migration for checkpoint resumption.
No solver-memory restoration, WLOG source restriction, extra packet bit,
arbitrary-arrival delivery, or certified negative status is claimed.

## Reproduce

\`\`\`sh
python -m pip install python-sat==1.8.dev24 z3-solver==4.13.3.0
python -m unittest discover -s k11122 -p 'test_*.py' -v
g++ -std=c++17 -O3 -Wall -Wextra -Werror k11122/lasso_batch.cpp -o lasso_batch
g++ -std=c++17 -O3 k11122/verify.cpp -o verify
python k11122/merge_checkpoints.py --target 0 --output merged-t0.json
python k11122/lasso_search.py run --target 0 --branch 0 --walker cpp \
  --batch-binary "$PWD/lasso_batch" --verify "$PWD/verify" \
  --seed 20261103 --seconds 25 --witness-selection first \
  --checkpoint-mode journal --output first-run
python k11122/lasso_search.py run --target 0 --branch 0 --walker cpp \
  --batch-binary "$PWD/lasso_batch" --verify "$PWD/verify" \
  --seed 20261103 --seconds 25 --witness-selection short-diverse \
  --checkpoint-mode journal --output short-diverse-run
python k11122/lasso_search.py audit --output first-run
python k11122/lasso_search.py audit --output short-diverse-run
\`\`\`

An independent proof-producing SAT solver and a checked refutation of
both complete first-hop branches of at least one orbit would be needed for
a mathematical negative. A positive needs a verified policy for **both**
destination orbits over all 524,288 residual masks and all connected
nonself sources. An UNKNOWN, invalid policy or finite-suite SAT is not proof.
