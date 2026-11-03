"""Independent finite-suite evaluation of the LAST raw SAT routing table.

This is a descriptive diagnostic, not evidence that the last raw policy is
best, not a graph-positive certificate, and never an UNSAT proof.
"""
import argparse
import json
from pathlib import Path
from lasso_witness import audit, geometry, selector_rows, sha, trace, checked_clause


def read_policy(path, n, target, rows):
    lines = Path(path).read_text().splitlines()
    if not lines or lines[0] != f"{n} {target}":
        raise ValueError("policy graph/target header mismatch")
    policy = {}
    for line in lines[1:]:
        vals = line.split()
        if len(vals) != 5:
            raise ValueError("malformed policy row")
        fields = [int(v) for v in vals]
        key, action = tuple(fields[:4]), fields[4]
        if key in policy or action not in dict(rows.get(key, [])):
            raise ValueError("duplicated or illegal policy action")
        policy[key] = action
    if set(policy) != set(rows):
        raise ValueError("incomplete or unexpected observation")
    return policy


def score(directory):
    root = Path(directory)
    certified = audit(root)
    meta = json.loads((root / "manifest.json").read_text())
    n, target = meta["n"], meta["target"]
    masks = json.loads((root / "masks.json").read_text())
    if masks != sorted(set(masks)) or not masks:
        raise ValueError("noncanonical frozen suite")
    filename = root / "last-policy.tsv"
    result = {
        "status": "NO_RAW_POLICY",
        "scope": "last SAT assignment on this frozen finite suite; not best-so-far or full graph",
        "n": n, "target": target, "branch": meta["branch"],
        "residuals": len(masks), "formula_sha256": certified["cnf_sha256"],
    }
    if not filename.is_file():
        return result
    rows = selector_rows(n, target)
    policy = read_policy(filename, n, target, rows)
    obligations, failures, failed_masks = 0, 0, 0
    first_bad = None
    for mask in masks:
        _, connected = geometry(n, target, mask)
        failed = False
        for source in sorted(connected):
            if source == target:
                continue
            obligations += 1
            witness = trace(policy, n, target, mask, source)
            if witness is not None:
                failures += 1
                failed = True
                if first_bad is None:
                    clause = checked_clause(witness, n, target, rows)
                    first_bad = {"mask": mask, "source": source, "clause_length": len(clause)}
        failed_masks += int(failed)
    result.update(
        status="EVALUATED_RAW_POLICY",
        policy_sha256=sha(filename),
        connected_source_obligations=obligations,
        failed_connected_sources=failures,
        failing_residual_masks=failed_masks,
        first_failing_obligation=first_bad,
    )
    if failures == 0:
        result["status"] = "FINITE_SUITE_PASS_ONLY"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    answer = score(args.bundle)
    args.output.write_text(json.dumps(answer, indent=2, sort_keys=True) + "\n")
    print(json.dumps(answer, sort_keys=True))


if __name__ == "__main__":
    main()
