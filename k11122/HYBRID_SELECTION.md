# K11122: deterministic hybrid necessary-witness selection (3 November 2026)

**Research status:** one-bit perfect resilience on K_{1,1,1,2,2} is
unresolved for both target orbits (0 singleton, 3 doubleton). The
established 2–3-state bound remains unchanged. All four original first-hop
branches remain open. This change is solely a clause-selection heuristic,
not a new theorem, a routing restriction, or an impossibility certificate.

## Exact behavior

Use \`--witness-selection hybrid --hybrid-every 8 --walker cpp\`. For each
**SAT assignment** (not solver conflict slice and not elapsed time), select:

- Models 1–7: legacy \`first\` C++ sampler, which stops after finding up to 96
  distinct source-reachable necessary lasso clauses.
- Model 8: the existing \`short-diverse\` C++ sampler, which checks the complete
  frozen mask family and all connected sources, chooses shorter selector sets,
  discards locally subsumed clauses and diversifies failure-mask observations.
- Repeat the same pattern every eight SAT assignments.

The schedule is pure and deterministic: \`effective_selection(strategy,
hybrid_every, selection_model_offset + raw_models)\`. The default period is
eight. The exposed interval is validated to be an exact integer in [2,1024],
with booleans, floats and malformed inputs rejected before constructing any
output. The period and each actual per-model scanner mode and global model
index are recorded in the solver's progress/checkpoints and
\`cpp-batches.jsonl\`. The default \`first\` and prior \`short-diverse\` modes
remain available and unchanged.

When resuming, the previous complete CNF and each witness are independently
audited *before* the inherited scheduler counter is read. The recovered offset
is the prior audited \`selection_model_offset + raw_models\`. Thus resuming
a search does not silently restart the eight-model cycle. Previously
committed clauses and exact residuals remain required; no SAT backend learned
state is claimed to survive a restart. A source-version mismatch still
requires explicit \`--allow-audited-migration\`, complete independent audit,
and a new output directory.

The three supported checkpoint implementations are \`journal\`, \`full\`, and
\`generations\`. Both duplicated entry points (normal and generation
checkpointing) use **the same pure schedule**. The C++ scanner itself does
not need changes: it is invoked with either its already-tested \`first\` or
\`short-diverse\` mode. A shorter witness is not assumed stronger in every
SAT search; the comparison must measure useful progress against overhead.

## Scientific safety

The global exactly-one source/transit routing selectors and first-hop
partition clauses are **unchanged**. Each learned clause still comes from a
complete deterministic failing execution, including the injection and
reachable prefix through the first repeated full arrival configuration.
There is no requirement to deliver from arbitrary arrivals, no hidden bit or
router memory, no source-dependent transit, and no prohibition of unreachable
loops. Only which **necessary** independently checked clauses are learned
changes; other candidate policies remain legal.

Every C++ witness is independently replayed and translated by
\`lasso_witness.checked_clause\` in Python before it is streamed to SAT.
The final CNF is independently reconstructed and audited. Positive graph
classification requires the *unchanged* C++ verifier to replay all 524,288
residual masks and all connected nonself sources for **both destination
orbits**. Negative graph classification requires independently checked
UNSAT refutations for **both exhaustive first-hop branches of at least one
orbit**, together with a verified complete encoding. Timeout, raw UNSAT,
invalid complete policy, or finite-suite SAT never proves this.

## Reproduction

Python 3.12 with \`python-sat==1.8.dev24\` and
\`z3-solver==4.13.3.0\`; compile the scanner and original verifier:

\`\`\`bash
python -m pip install python-sat==1.8.dev24 z3-solver==4.13.3.0
python -m unittest discover -s k11122 -p 'test_*.py' -v
g++ -O3 -std=c++17 -Wall -Wextra -Werror k11122/lasso_batch.cpp -o lasso_batch
g++ -O3 -std=c++17 k11122/verify.cpp -o verify
python k11122/merge_checkpoints.py --target 0 --output merged-t0.json
python k11122/lasso_search.py run --target 0 --branch 0 \
  --walker cpp --batch-binary "$PWD/lasso_batch" --verify "$PWD/verify" \
  --seed 20261103 --seconds 20 --max-new-per-round 96 \
  --witness-selection hybrid --hybrid-every 8 --checkpoint-mode journal \
  --output hybrid-run
python k11122/lasso_search.py audit --output hybrid-run
\`\`\`

The separate GitHub-hosted comparison uses the **same 2,701 target-0
merged unconditional masks**, target 0, branch 0, CaDiCaL195 and seed
20261103 across \`first\`, \`short-diverse\` and \`hybrid\`, each with a
bounded 20-second search budget and identical 96-witness cap. Only the
necessary-clause choice changes. A separate ten-second target-3 smoke
uses its 2,181 strictly merged masks. Compare raw models, verified new
clauses, clause length, solver/walk times, memory, checkpoint and final
CNF sizes, and independently checked full-suite candidates—not merely
file size or timeout count. The models diverge across heuristics, so
single-run differences do not establish statistical superiority.

No recurring workflow, self-hosted compute, or uncontrolled retry is
introduced. Preserve artifact SHA-256 checksums, complete code, model
inputs, source and dependency hashes, and checker logs.
