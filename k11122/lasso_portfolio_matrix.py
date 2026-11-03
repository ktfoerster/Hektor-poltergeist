"""Four-case K11122 portfolio matrix: two target orbits x two first-hop branches.

Each independent source is a separately audited CaDiCaL or MapleChrono
search. A portfolio contains ONLY canonical, necessary, source-reachable
lasso clauses, never solver-internal learning or solver conclusions.

All searches are bounded and their active-search budgets are matched
*within* each target/branch comparison. The script preserves every CNF,
witness, provenance manifest, source trajectory and independent audit.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from lasso_best import independently_check_best
from lasso_divergence import first_divergence
from lasso_journal import check_committed
from lasso_policy_quality import score
from lasso_portfolio import build
from lasso_witness import audit, sha
from merge_checkpoints import LATEST, merge

HERE = Path(__file__).resolve().parent
TARGET_MASK_COUNTS = {0: 2701, 3: 2181}
BACKENDS = ("cadical195", "maplechrono")
ARMS = ("cadical195", "maplechrono", "portfolio")
VALID_STATUSES = {
    "UNKNOWN", "UNSAT_UNCERTIFIED", "FINITE_SUITE_SAT_UNVERIFIED",
    "FINITE_SAT_GLOBALLY_INVALID", "VERIFIED_POSITIVE_ONE_ORBIT",
}


def validate_options(source_seconds, continuation_seconds, seed, best_interval):
    for label, value in (("source", source_seconds),
                         ("continuation", continuation_seconds)):
        if type(value) not in (int, float) or not 0 < value <= 45:
            raise ValueError(label + " time must be in (0,45] seconds")
    if type(seed) is not int or not 1 <= seed <= 2147483647:
        raise ValueError("seed must be a valid deterministic SAT integer")
    if type(best_interval) is not int or not 1 <= best_interval <= 64:
        raise ValueError("best interval must be an integer in [1,64]")


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def checked_bundle(path, target, branch, expected_masks):
    """Independently audit a full terminal CNF and its crash-safe ledger."""
    directory = Path(path)
    verified = audit(directory)
    journal = check_committed(directory)
    meta = json.loads((directory / "manifest.json").read_text())
    stats = json.loads((directory / "summary.json").read_text())
    if (verified["status"] != "CHECKED" or
            journal["verified_witnesses"] != meta["witnesses"] or
            journal["verified_clauses"] != meta["clauses"] or
            (meta["n"], meta["target"], meta["branch"], meta["masks"]) !=
            (7, target, branch, expected_masks) or
            verified["cnf_sha256"] != meta["sha256"]["formula.cnf"]):
        raise RuntimeError("CNF, proof-journal, branch or frozen-mask audit failed")
    if stats["status"] not in VALID_STATUSES or stats["budget_scope"] != "search":
        raise RuntimeError("unrecognized search state or nonmatching budget scope")
    return meta, stats, verified


def run_checked(root, name, target, branch, backend, seed, seconds,
                scanner, scorer, verifier, resume=None, best_interval=0):
    dest = root / name
    args = [sys.executable, str(HERE / "lasso_search.py"), "run",
            "--output", str(dest),
            "--target", str(target), "--branch", str(branch),
            "--backend", backend, "--seed", str(seed),
            "--seconds", str(seconds), "--budget-scope", "search",
            "--walker", "cpp", "--batch-binary", str(scanner),
            "--verify", str(verifier),
            "--witness-selection", "hybrid", "--hybrid-every", "8",
            "--max-new-per-round", "96", "--checkpoint-mode", "journal"]
    if resume is not None:
        args.extend(["--resume", str(resume),
                     "--best-interval", str(best_interval),
                     "--quality-binary", str(scorer)])
    started = time.monotonic()
    try:
        done = subprocess.run(args, capture_output=True, text=True,
                              timeout=seconds + 150)
    except subprocess.TimeoutExpired as exc:
        write_json(root / (name + "-external-timeout.json"),
                   {"status": "EXTERNAL_TIMEOUT",
                    "wall_elapsed": time.monotonic() - started,
                    "args": args})
        raise RuntimeError("bounded search exceeded external wall limit") from exc
    (root / (name + "-stdout.json")).write_text(done.stdout)
    (root / (name + "-stderr.log")).write_text(done.stderr)
    if done.returncode:
        raise RuntimeError(name + " search failed: " + done.stderr[-3000:])
    meta, stats, verified = checked_bundle(
        dest, target, branch, TARGET_MASK_COUNTS[target])
    if (meta["backend"] != backend or meta["seed"] != seed or
            not (0 < stats["elapsed_seconds"] <= seconds + 3)):
        raise RuntimeError("SAT backend, seed or active search time mismatch")
    if stats["inherited_witnesses"] != (
            json.loads((Path(resume) / "manifest.json").read_text())["witnesses"]
            if resume is not None else 0):
        raise RuntimeError("unexpected initial certificate count")
    if resume is not None:
        provenance = meta["imported"].get("resumed_from")
        if (not provenance or provenance.get("manifest_sha256") !=
                sha(Path(resume) / "manifest.json") or
                provenance.get("formula_sha256") !=
                sha(Path(resume) / "formula.cnf")):
            raise RuntimeError("resumed from a different source CNF")
    best = independently_check_best(dest)
    if resume is not None:
        if (stats["raw_models"] and
                (best["status"] != "INDEPENDENTLY_REPLAYED_HISTORICAL_BEST" or
                 stats["best_observed_raw_quality"] != best["quality"])):
            raise RuntimeError("historical best raw policy not independently replayed")
    last = score(dest) if resume is not None else None
    result = {
        "name": name, "target": target, "branch": branch,
        "seed": seed, "backend": backend,
        "scope": "frozen finite suite, neither graph proof nor terminal SAT model",
        "frozen_residual_masks": TARGET_MASK_COUNTS[target],
        "input_checkpoint_manifest_sha256":
            sha(Path(resume) / "manifest.json") if resume is not None else None,
        "input_checkpoint_formula_sha256":
            sha(Path(resume) / "formula.cnf") if resume is not None else None,
        "terminal_formula_sha256": verified["cnf_sha256"],
        "terminal_manifest_sha256": sha(dest / "manifest.json"),
        "preparation_seconds": stats["preparation_seconds"],
        "active_search_seconds": stats["elapsed_seconds"],
        "total_wall_seconds": stats["total_wall_seconds"],
        "external_wall_seconds": time.monotonic() - started,
        "inherited_certified_clauses": stats["inherited_witnesses"],
        "new_certified_clauses": stats["new_witnesses"],
        "total_certified_clauses": meta["witnesses"],
        "raw_models": stats["raw_models"],
        "observed_solver_effort": stats["observed_solver_effort"],
        "sampled_historical_best": best,
        "last_raw_policy_score": last,
        "finite_suite_candidates": stats["finite_suite_candidates"],
        "status": stats["status"],
    }
    write_json(root / (name + "-metrics.json"), result)
    return result


def policy_hashes(directory):
    records = Path(directory) / "cpp-batches.jsonl"
    if not records.is_file():
        return []
    result = []
    previous = 0
    for line in records.read_text().splitlines():
        row = json.loads(line)
        idx, digest = row["global_model_index"], row["policy_sha256"]
        if type(idx) is not int or idx != previous + 1:
            raise RuntimeError("malformed or incomplete source policy index")
        if type(digest) is not str or len(digest) != 64 or any(
                c not in "0123456789abcdef" for c in digest):
            raise RuntimeError("invalid source-policy SHA-256 record")
        result.append(digest)
        previous = idx
    return result


def compare_arms(arms):
    """Report within-case comparisons without equating assignments with progress."""
    values = {name: arm["sampled_historical_best"] for name, arm in arms.items()}
    failure_counts = {}
    for name, score in values.items():
        if score["status"] == "INDEPENDENTLY_REPLAYED_HISTORICAL_BEST":
            failure_counts[name] = score["quality"]["failing_residual_masks"]
        elif score["status"] == "NO_SCORED_POLICY":
            failure_counts[name] = None
        else:
            raise RuntimeError("unverified historical policy in comparison")
    baseline = [failure_counts[name] for name in BACKENDS]
    combined = failure_counts["portfolio"]
    return {
        "best_sampled_failing_masks": failure_counts,
        "portfolio_improvement_vs_best_single_masks": (
            min(baseline) - combined
            if combined is not None and all(v is not None for v in baseline)
            else None),
        "active_search_seconds": {
            name: arm["active_search_seconds"] for name, arm in arms.items()},
        "new_independently_verified_clauses": {
            name: arm["new_certified_clauses"] for name, arm in arms.items()},
        "raw_SAT_assignments": {name: arm["raw_models"] for name, arm in arms.items()},
        "interpretation": (
            "One fixed seed; best of periodically sampled historical raw "
            "SAT policies, not a solution of terminal CNF or the full graph."),
    }


def case(root, target, branch, scanner, scorer, verifier,
         source_seconds, continuation_seconds, seed, best_interval):
    prefix = "t" + str(target) + "-b" + str(branch)
    sources, bundles = {}, {}
    for backend in BACKENDS:
        name = prefix + "-source-" + backend
        sources[backend] = run_checked(
            root, name, target, branch, backend, seed, source_seconds,
            scanner, scorer, verifier)
        bundles[backend] = root / name
        if sources[backend]["total_certified_clauses"] <= 0:
            raise RuntimeError("source did not produce independently certified clauses")
    paths = [bundles[backend] for backend in BACKENDS]
    traces = [policy_hashes(path) for path in paths]
    divergence = first_divergence(*traces)
    portfolio_dir = root / (prefix + "-portfolio")
    stamp = time.monotonic()
    portfolio = build(portfolio_dir, paths, target, branch)
    portfolio_creation = time.monotonic() - stamp
    # The existing builder audits every source before creating the CNF,
    # then independently reconstructs the complete portfolio afterward.
    audit_again = audit(portfolio_dir)
    if (audit_again["status"] != "CHECKED" or
            audit_again["witnesses"] != portfolio["deduplicated_witnesses"] or
            portfolio["deduplicated_witnesses"] > portfolio["input_witnesses"] or
            portfolio["variables"] != (4736 if target == 0 else 6240)):
        raise RuntimeError("incorrect or incomplete portfolio CNF")
    write_json(root / (prefix + "-portfolio-metrics.json"), {
        "creation_audit_and_deduplication_seconds": portfolio_creation,
        "portfolio_summary": portfolio,
        "source_trajectory_divergence": divergence,
        "source_policy_hash_counts": [len(seq) for seq in traces],
    })
    arms = {}
    for arm in ARMS:
        initial = portfolio_dir if arm == "portfolio" else bundles[arm]
        name = prefix + "-continue-" + arm
        arms[arm] = run_checked(
            root, name, target, branch, "cadical195", seed,
            continuation_seconds, scanner, scorer, verifier,
            resume=initial, best_interval=best_interval)
        if (arms[arm]["inherited_certified_clauses"] !=
                (portfolio["deduplicated_witnesses"]
                 if arm == "portfolio" else sources[arm]["total_certified_clauses"])):
            raise RuntimeError("unexpected inherited CNF or witness count")
    return {
        "target": target, "branch": branch,
        "input_frozen_masks": TARGET_MASK_COUNTS[target],
        "divergence": divergence,
        "actually_divergent_source_trajectories": divergence["actually_divergent"],
        "source_checkpoints": sources,
        "portfolio": portfolio,
        "portfolio_creation_audit_and_deduplication_seconds": portfolio_creation,
        "continuations": arms,
        "comparison": compare_arms(arms),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--scanner", type=Path, required=True)
    p.add_argument("--scorer", type=Path, required=True)
    p.add_argument("--verifier", type=Path, required=True)
    p.add_argument("--source-seconds", type=float, default=6)
    p.add_argument("--search-seconds", type=float, default=8)
    p.add_argument("--seed", type=int, default=20261103)
    p.add_argument("--best-interval", type=int, default=8)
    args = p.parse_args()
    try:
        validate_options(args.source_seconds, args.search_seconds,
                         args.seed, args.best_interval)
    except ValueError as exc:
        p.error(str(exc))
    root = args.output.resolve()
    if root.exists():
        p.error("refusing to overwrite evidence directory")
    binaries = [path.resolve(strict=True)
                for path in (args.scanner, args.scorer, args.verifier)]
    root.mkdir(parents=True)
    report = {
        "schema": 1, "scope": (
            "2 target orbits times 2 exhaustive first-hop branches; "
            "independently audited necessary certificate pools, no theorem"),
        "seed": args.seed, "source_seconds": args.source_seconds,
        "search_seconds_each": args.search_seconds,
        "sampled_historical_best_interval": args.best_interval,
        "CAUTION": (
            "Cross-case scores are not directly comparable; within-case "
            "single-backend vs pooled historical raw-policy outcomes are "
            "one-run descriptive statistics only."),
        "cases": {},
    }
    frozen = {target: merge(LATEST, target)["masks"] for target in (0, 3)}
    for target, count in TARGET_MASK_COUNTS.items():
        if (len(frozen[target]) != count or
                frozen[target] != sorted(set(frozen[target]))):
            raise RuntimeError("the strict frozen source residual suite changed")
    start = time.monotonic()
    for target in (0, 3):
        for branch in (0, 1):
            name = "t" + str(target) + "-b" + str(branch)
            report["cases"][name] = case(
                root, target, branch, *binaries,
                args.source_seconds, args.search_seconds,
                args.seed, args.best_interval)
            write_json(root / "latest-matrix.json", report)
    report["total_elapsed_wall_seconds"] = time.monotonic() - start
    report["mathematical_classification"] = (
        "NOT ESTABLISHED: no proof of both complete orbit-positive policies "
        "or of both certified negative branches of one orbit")
    write_json(root / "portfolio-matrix-summary.json", report)
    print(json.dumps({
        name: {
            "actual_source_trajectory_divergence":
                case_data["actually_divergent_source_trajectories"],
            "initial_unique_portfolio_clauses":
                case_data["portfolio"]["deduplicated_witnesses"],
            "initial_duplicate_clauses":
                case_data["portfolio"]["duplicates_eliminated"],
            "best_sampled_failing_masks":
                case_data["comparison"]["best_sampled_failing_masks"],
            "improvement_against_best_single":
                case_data["comparison"]["portfolio_improvement_vs_best_single_masks"],
            "terminal_statuses": {
                arm: value["status"]
                for arm, value in case_data["continuations"].items()},
        } for name, case_data in report["cases"].items()},
        sort_keys=True))


if __name__ == "__main__":
    main()
