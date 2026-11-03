"""Independently certified cross-branch K11122 failing-walk reuse.

A source-reachable lasso clause is necessary for *any* legal policy with the
same graph, target and residual. Branch labels are NOT part of its soundness
argument. Audit the exact source CNF and every witness before import. Never
import source first-hop restrictions or solver conclusions.
"""
import json
from pathlib import Path
from lasso_witness import audit, branch_clause, checked_clause, selector_rows, sha


def transfer(source_bundle, n, target, destination_branch, masks, insert, record,
             expected_source_hashes=None, allow_audited_migration=False):
    """Stream certified opposite-branch clauses and retain exact provenance.

    insert(clause) and record(witness_item) must append to the destination CNF
    and witness journal respectively. The destination caller is responsible
    for constructing its own exactly-one selectors and branch assertion.
    """
    if type(destination_branch) is not int or destination_branch not in (0, 1):
        raise ValueError("destination must have an exhaustive first-hop branch")
    if (not isinstance(masks, list) or not masks or masks != sorted(set(masks)) or
            any(type(x) is not int for x in masks)):
        raise ValueError("destination suite must be strictly sorted")
    bundle = Path(source_bundle)
    if (bundle / "current").is_symlink():
        bundle = (bundle / "current").resolve(strict=True)
    # Complete byte-exact semantic audit before permitting one insertion.
    check = audit(bundle)
    meta = json.loads((bundle / "manifest.json").read_text())
    if ((meta["n"], meta["target"]) != (n, target) or
            type(meta["branch"]) is not int or meta["branch"] != 1 - destination_branch):
        raise ValueError("source is not the opposite branch of this destination orbit")
    migrated = (expected_source_hashes is not None and
                meta.get("source_sha256") != expected_source_hashes)
    if migrated and not allow_audited_migration:
        raise ValueError("source dependencies changed; require explicit audited migration")
    old_masks = json.loads((bundle / "masks.json").read_text())
    if old_masks != masks:
        raise ValueError("source masks differ from the exact frozen destination suite")
    rows = selector_rows(n, target)
    allowed = set(branch_clause(n, target, destination_branch, rows))
    affected_rows = [choices for choices in rows.values()
                     if allowed.issubset({var for _, var in choices})]
    if len(affected_rows) != 1:
        raise RuntimeError("could not independently reconstruct branch row")
    forbidden = {var for _, var in affected_rows[0] if var not in allowed}
    counts = {"source_witnesses": 0, "transferred": 0, "branch_vacuous": 0,
              "duplicate": 0, "clause_literals": 0,
              "min_clause_literals": None, "max_clause_literals": 0}
    seen = set()
    with (bundle / "witnesses.jsonl").open() as stream:
        for line in stream:
            item = json.loads(line)
            clause = checked_clause(item["witness"], n, target, rows)
            if clause != item["clause"]:
                raise ValueError("source witness mismatch after source audit")
            counts["source_witnesses"] += 1
            if any(-lit in forbidden for lit in clause):
                # Such a source-selected action is forbidden by the *other*
                # branch. Its negative literal already holds in that branch.
                counts["branch_vacuous"] += 1
                continue
            key = tuple(clause)
            if key in seen:
                counts["duplicate"] += 1
                continue
            seen.add(key)
            insert(clause)
            record(item)
            counts["transferred"] += 1
            counts["clause_literals"] += len(clause)
            counts["min_clause_literals"] = (
                len(clause) if counts["min_clause_literals"] is None else
                min(counts["min_clause_literals"], len(clause)))
            counts["max_clause_literals"] = max(counts["max_clause_literals"], len(clause))
    # Fail closed if a concurrently altered source was used during transfer.
    if sha(bundle / "witnesses.jsonl") != meta["sha256"]["witnesses.jsonl"]:
        raise ValueError("source witness file changed during transfer")
    if (counts["source_witnesses"] != check["witnesses"] or
            sum(counts[x] for x in ("transferred", "branch_vacuous", "duplicate")) !=
            check["witnesses"]):
        raise ValueError("incomplete witness transfer")
    return {"source_branch": meta["branch"], "destination_branch": destination_branch,
            "source_manifest_sha256": sha(bundle / "manifest.json"),
            "source_formula_sha256": check["cnf_sha256"],
            "source_witnesses_sha256": sha(bundle / "witnesses.jsonl"),
            "source_dependency_hashes": meta["source_sha256"],
            "source_audit": check,
            "migration": ("explicit independent full-CNF and witness recheck"
                          if migrated else "same source dependency hashes or unspecified"),
            **counts}
