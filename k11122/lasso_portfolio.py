"""Build a self-contained, independently audited rank-free witness portfolio.

Only source-reachable necessary lasso clauses can cross SAT backend / phase
boundaries. These sources MUST use the same graph, target, physical-first-hop
branch, sorted residual suite and global selector numbering. Never import
backend-internal learned clauses, assumptions, phase choices or solver verdicts.

The portfolio is a NEW, standalone compatible checkpoint. Its complete CNF
is reconstructed afresh, including only base exactly-one+branch clauses and
independently checked, deduplicated necessary lasso witnesses.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

from lasso_witness import audit, base_clauses, checked_clause, selector_rows, sha
from lasso_clause_selector import select_clauses


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n"


def build(output, sources, expected_target=None, expected_branch=None, selection="all"):
    if type(selection) is not str or selection not in ("all", "lossless", "shortest-half", "balanced-half"):
        raise ValueError("unsupported portfolio selection mode")
    if not isinstance(sources, (list, tuple)) or len(sources) < 2 or len(sources) > 12:
        raise ValueError("portfolio needs between 2 and 12 independent checkpoint paths")
    if len({str(Path(x).resolve(strict=True)) for x in sources}) != len(sources):
        raise ValueError("duplicate portfolio source directory")
    root = Path(output)
    if root.exists():
        raise ValueError("refusing to overwrite existing portfolio output")
    # Audit and validate ALL sources before creating any output, so even
    # missing/malformed/cross-target sources cannot leave a misleading bundle.
    checked = []
    fixed = None
    for item in sources:
        path = Path(item).resolve(strict=True)
        if (path / "current").is_symlink():
            path = (path / "current").resolve(strict=True)
        evidence = audit(path)
        meta = json.loads((path / "manifest.json").read_text())
        masks = json.loads((path / "masks.json").read_text())
        signature = (meta["n"], meta["target"], meta["branch"], tuple(masks))
        if fixed is None:
            fixed = signature
        elif signature != fixed:
            raise ValueError("source graph, target, branch or frozen mask family differ")
        if expected_target is not None and meta["target"] != expected_target:
            raise ValueError("unexpected portfolio destination orbit")
        if expected_branch is not None and meta["branch"] != expected_branch:
            raise ValueError("unexpected portfolio first-hop branch")
        checked.append(dict(path=path, meta=meta, audit=evidence,
                            manifest_sha256=sha(path / "manifest.json"),
                            witness_sha256=sha(path / "witnesses.jsonl"),
                            formula_sha256=sha(path / "formula.cnf")))
    n, target, branch, frozen = fixed
    rows = selector_rows(n, target)
    clauses = list(base_clauses(n, target, branch, rows))
    nvars = sum(len(x) for x in rows.values())
    # Build into an independent temporary root, never replace existing files.
    root.mkdir(parents=True)
    (root / "masks.json").write_text(json.dumps(list(frozen)) + "\n")
    (root / "masks.txt").write_text("".join(f"{mask}\n" for mask in frozen))
    (root / "selectors.json").write_text(json.dumps(
        [[*key, [[action, var] for action, var in choices]]
         for key, choices in rows.items()]) + "\n")
    selected, per_source = set(), []
    pending = []
    subsumed = {}
    selected_mask_count = None
    hashes = hashlib.sha256()
    count = len(clauses)
    selected_count = 0
    body = root / "clauses.body"
    with body.open("wb") as formula, (root / "witnesses.jsonl").open("w") as saved:
        def append_clause(clause):
            nonlocal count
            raw = (" ".join(map(str, clause)) + " 0\n").encode()
            formula.write(raw)
            hashes.update(raw)
            count += 1
        for clause in clauses:
            raw = (" ".join(map(str, clause)) + " 0\n").encode()
            formula.write(raw)
            hashes.update(raw)
        for source_index, source in enumerate(checked):
            records = duplicated = 0
            with (source["path"] / "witnesses.jsonl").open() as f:
                for line in f:
                    item = json.loads(line)
                    clause = checked_clause(item["witness"], n, target, rows)
                    if clause != item["clause"]:
                        raise ValueError("source clause/witness changed after audit")
                    records += 1
                    key = tuple(clause)
                    if key in selected:
                        duplicated += 1
                        continue
                    selected.add(key)
                    if selection == "all":
                        append_clause(clause)
                        saved.write(canonical(item))
                        selected_count += 1
                    else:
                        pending.append(dict(clause=tuple(clause), item=item,
                                            source=source_index,
                                            mask=item["witness"]["mask"]))
            if (records != source["audit"]["witnesses"] or
                    sha(source["path"] / "witnesses.jsonl") != source["witness_sha256"] or
                    sha(source["path"] / "manifest.json") != source["manifest_sha256"] or
                    sha(source["path"] / "formula.cnf") != source["formula_sha256"]):
                raise RuntimeError("source altered or witness stream incomplete during portfolio construction")
            per_source.append(dict(
                source_manifest_sha256=source["manifest_sha256"],
                source_formula_sha256=source["formula_sha256"],
                source_witnesses_sha256=source["witness_sha256"],
                backend=source["meta"].get("backend"),
                seed=source["meta"].get("seed"),
                phase_policy_sha256=source["meta"].get("sha256", {}).get("phase-policy.tsv"),
                original_checked_witnesses=records,
                newly_contributed_necessary_clauses=records - duplicated,
                duplicate_clauses=duplicated,
                independently_checked_source_audit=source["audit"],
            ))
        if selection != "all":
            original_unique = sum(item["newly_contributed_necessary_clauses"]
                                  for item in per_source)
            if len(pending) != original_unique:
                raise RuntimeError("incomplete selectable witness stream")
            kept, subsumed = select_clauses(pending, selection, len(checked))
            for index, item in enumerate(pending):
                if index in kept:
                    append_clause(item["clause"])
                    saved.write(canonical(item["item"]))
                    selected_count += 1
            selected_mask_count = len({pending[i]["mask"] for i in kept})
        formula.flush()
        os.fsync(formula.fileno())
        saved.flush()
        os.fsync(saved.fileno())
    with (root / "formula.cnf").open("wb") as dst, body.open("rb") as src:
        dst.write(f"p cnf {nvars} {count}\n".encode())
        shutil.copyfileobj(src, dst)
        dst.flush()
        os.fsync(dst.fileno())
    unique_before_selection = sum(x["newly_contributed_necessary_clauses"]
                                  for x in per_source)
    if selection == "all" and selected_count != unique_before_selection:
        raise RuntimeError("full portfolio unexpectedly omitted certificates")
    if selection != "all":
        with (root / "dominance.jsonl").open("w") as proof:
            for discarded, dominating in sorted(subsumed.items()):
                proof.write(canonical({"discarded_index": discarded,
                                       "retained_dominator_index": dominating}))
    imported = {
        "portfolio": dict(schema=1, source_count=len(checked), sources=per_source,
                          selection=selection, unique_before_selection=unique_before_selection,
                          selected_witnesses=selected_count,
                          subsumed_clauses=len(subsumed),
                          other_selective_omissions=unique_before_selection-selected_count-len(subsumed),
                          exact_equivalence_to_full=(selection in ("all", "lossless")),
                          builder_sha256=sha(Path(__file__).with_name("lasso_clause_selector.py")),
                          deduplicated_witnesses=selected_count,
                          raw_input_witnesses=sum(x["original_checked_witnesses"] for x in per_source),
                          semantic_scope="same target/branch/masks, independently necessary source-reachable lassos only",
                          source_solver_results_inherited=False)
    }
    # The checkpoint is compatible with existing independently audited resume.
    # No source solver search state is inherited. One fixed backend is only a
    # manifest provenance placeholder and is not an imported solver state.
    from lasso_search import source_hashes
    meta = dict(
        schema=1, encoding="source-reachable-lasso-v1", n=n, target=target,
        branch=branch, variables=nvars, clauses=count, witnesses=selected_count,
        masks=len(frozen), clause_body_sha256=hashes.hexdigest(),
        source_sha256=source_hashes(), imported=imported,
        backend="cadical195", seed=20261103,
        scope="new independently reconstructed portfolio on frozen finite suite",
        progress=dict(status="UNKNOWN", raw_models=0,
                      selection_model_offset=0, inherited_witnesses=selected_count,
                      portfolio_source_count=len(checked)),
        commit=os.environ.get("GITHUB_SHA"))
    meta["sha256"] = {name: sha(root / name) for name in
                      (("formula.cnf", "selectors.json", "masks.json",
                       "masks.txt", "witnesses.jsonl") +
                       (("dominance.jsonl",) if selection != "all" else ()))}
    (root / "manifest.json").write_text(json.dumps(meta, sort_keys=True, indent=2) + "\n")
    result = audit(root)
    if (result["status"] != "CHECKED" or
            result["witnesses"] != selected_count or
            result["cnf_sha256"] != meta["sha256"]["formula.cnf"]):
        raise RuntimeError("new portfolio failed complete independent reconstruction")
    (root / "audit.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    report = dict(
        status="INDEPENDENTLY_AUDITED_PORTFOLIO",
        target=target, branch=branch, n=n, residuals=len(frozen),
        source_count=len(checked), source_details=per_source,
        input_witnesses=imported["portfolio"]["raw_input_witnesses"],
        deduplicated_witnesses=selected_count,
        duplicates_eliminated=imported["portfolio"]["raw_input_witnesses"]-unique_before_selection,
        selection=selection, unique_before_selection=unique_before_selection,
        subsumed_clauses=len(subsumed),
        other_selective_omissions=unique_before_selection-selected_count-len(subsumed),
        exact_equivalence_to_full=(selection in ("all", "lossless")),
        selected_mask_coverage=selected_mask_count,
        variables=nvars, clauses=count, formula_sha256=result["cnf_sha256"],
        scope="necessary source-reachable lasso clauses, no positive or negative graph claim")
    (root / "portfolio-summary.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--sources", nargs="+", required=True, type=Path)
    p.add_argument("--target", type=int, choices=(0, 3), required=True)
    p.add_argument("--branch", type=int, choices=(0, 1), required=True)
    p.add_argument("--selection", choices=("all", "lossless", "shortest-half", "balanced-half"),
                   default="all")
    args = p.parse_args()
    print(json.dumps(build(args.output, args.sources, args.target, args.branch,
                           selection=args.selection),
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
