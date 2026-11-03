"""Reproducible multi-seed, equal-ACTIVE-search K11122 transfer comparison.

Sources are generated inside the same run, audited without privilege, and
reused across seeds. Every destination independently audits its source once
per run. Preparation is NEVER hidden: it is reported separately from the
search-only budget. This script does not run indefinitely or infer a theorem.
"""
import argparse
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time

from lasso_journal import check_committed
from lasso_best import independently_check_best
from lasso_policy_quality import score
from lasso_witness import audit, sha

HERE = Path(__file__).resolve().parent


def write_json(path, obj):
    path.write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n")


def run_one(root, name, target, branch, seconds, seed, scanner, verifier,
            transfer=None, search_budget=False,
            best_interval=0, quality_binary=None):
    path = root / name
    args = [sys.executable, str(HERE / "lasso_search.py"), "run",
            "--target", str(target), "--branch", str(branch),
            "--seconds", str(seconds), "--seed", str(seed),
            "--walker", "cpp", "--batch-binary", str(scanner),
            "--verify", str(verifier), "--witness-selection", "hybrid",
            "--hybrid-every", "8", "--max-new-per-round", "96",
            "--checkpoint-mode", "journal", "--output", str(path)]
    if best_interval:
        args += ["--best-interval", str(best_interval), "--quality-binary", str(quality_binary)]
    if search_budget:
        args += ["--budget-scope", "search"]
    if transfer is not None:
        args += ["--transfer-opposite-bundle", str(transfer)]
    t = time.monotonic()
    try:
        process = subprocess.run(args, capture_output=True, text=True,
                                 timeout=seconds + 160)
    except subprocess.TimeoutExpired as exc:
        write_json(root / (name + "-timeout.json"),
                   {"status": "EXTERNAL_WALL_TIMEOUT", "args": args,
                    "duration_wall_seconds": time.monotonic() - t})
        raise RuntimeError("bounded K11122 worker exceeded external timeout") from exc
    (root / (name + "-stdout.json")).write_text(process.stdout)
    (root / (name + "-stderr.log")).write_text(process.stderr)
    if process.returncode != 0:
        raise RuntimeError(f"{name} failed with exit {process.returncode}: " +
                           process.stderr[-2000:])
    wall = time.monotonic() - t
    full_audit = audit(path)
    committed = check_committed(path)
    meta = json.loads((path / "manifest.json").read_text())
    stats = json.loads((path / "summary.json").read_text())
    quality = score(path)
    best = independently_check_best(path)
    if best_interval and (best["status"] != "INDEPENDENTLY_REPLAYED_HISTORICAL_BEST" or
                          stats["quality_scored_raw_models"] <= 0 or
                          best["quality"] != stats["best_observed_raw_quality"]):
        raise RuntimeError("independently replayed best raw policy mismatch")
    write_json(root / (name + "-audit.json"), full_audit)
    write_json(root / (name + "-quality.json"), quality)
    if (full_audit["status"] != "CHECKED" or
            committed["verified_witnesses"] != meta["witnesses"] or
            meta["sha256"]["formula.cnf"] != full_audit["cnf_sha256"]):
        raise RuntimeError("full independent CNF or journal audit failed")
    if (meta["target"], meta["branch"], meta["masks"]) != (
            target, branch, 2701 if target == 0 else 2181):
        raise RuntimeError("source/target/residual mismatch")
    if stats["budget_scope"] != ("search" if search_budget else "total"):
        raise RuntimeError("incorrect search accounting mode")
    if search_budget and not (0 < stats["elapsed_seconds"] < seconds + 3):
        raise RuntimeError("equal search budget was not honored")
    if (stats["preparation_seconds"] < 0 or
            stats["total_wall_seconds"] < stats["preparation_seconds"] or
            stats["solver_effort_samples"] < 1):
        raise RuntimeError("invalid audited time/solver counters")
    if (sum(stats["selected_mode_counts"].values()) != stats["raw_models"] or
            sum(stats["selected_mode_clauses"].values()) != stats["new_witnesses"]):
        raise RuntimeError("per-mode experiment counters do not reconcile")
    info = meta["imported"].get("opposite_branch_certificates")
    if transfer is not None:
        if not info or info["source_branch"] != 0 or info["destination_branch"] != 1:
            raise RuntimeError("transferred clause provenance mismatch")
        if (info["transferred"] != stats["transfer_clauses"] or
                info["transferred"] != stats["inherited_witnesses"] or
                sum(info[k] for k in ("transferred", "branch_vacuous", "duplicate")) !=
                info["source_witnesses"]):
            raise RuntimeError("cross-branch clause counts disagree")
        if (info["source_audit"]["cnf_sha256"] !=
                sha(Path(transfer) / "formula.cnf")):
            raise RuntimeError("transferred formula digest mismatch")
    elif stats["inherited_witnesses"] != 0:
        raise RuntimeError("cold branch unexpectedly inherited clauses")
    result = {
        "target": target, "branch": branch, "seed": seed,
        "budget_scope": stats["budget_scope"],
        "search_budget_seconds": seconds,
        "total_elapsed_seconds": stats["total_wall_seconds"],
        "external_execution_wall_seconds": wall,
        "preparation_seconds": stats["preparation_seconds"],
        "transfer_seconds": stats["transfer_seconds"],
        "raw_assignments": stats["raw_models"],
        "new_witnesses": stats["new_witnesses"],
        "inherited_witnesses": stats["inherited_witnesses"],
        "final_witnesses": meta["witnesses"],
        "observed_solver_effort": stats["observed_solver_effort"],
        "solver_effort_samples": stats["solver_effort_samples"],
        "unsampled_bounded_timeouts": stats["unsampled_bounded_timeouts"],
        "solver_time": stats["solver_seconds"],
        "replay_time": stats["replay_seconds"],
        "finite_suite_candidates": stats["finite_suite_candidates"],
        "status": stats["status"],
        "cnf_sha256": full_audit["cnf_sha256"],
        "last_raw_policy_quality": quality,
        "best_raw_policy_quality": best,
        "quality_scored_raw_models": stats["quality_scored_raw_models"],
        "quality_improvements": stats["quality_improvements"],
        "quality_sampling_seconds": stats["quality_sampling_seconds"],
        "source_manifest_sha256": (info["source_manifest_sha256"] if info else None)
    }
    write_json(root / (name + "-metrics.json"), result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--scanner", type=Path, required=True)
    p.add_argument("--verifier", type=Path, required=True)
    p.add_argument("--source-seconds", type=float, default=12)
    p.add_argument("--search-seconds", type=float, default=12)
    p.add_argument("--seeds", default="20261103,20261104,20261105")
    p.add_argument("--target3-seconds", type=float, default=8)
    args = p.parse_args()
    seeds = [int(x) for x in args.seeds.split(",")]
    if (not seeds or len(seeds) > 5 or len(set(seeds)) != len(seeds) or
            any(seed < 1 or seed > 2147483647 for seed in seeds)):
        p.error("use one to five distinct valid deterministic SAT seeds")
    if not (0 < args.source_seconds <= 60 and
            0 < args.search_seconds <= 60 and
            0 < args.target3_seconds <= 40):
        p.error("experiments must have small strict per-run time bounds")
    out = args.output.resolve()
    if out.exists():
        p.error("use a new evidence directory")
    out.mkdir(parents=True)
    scanner = args.scanner.resolve(strict=True)
    verifier = args.verifier.resolve(strict=True)
    results = {}
    t = time.monotonic()
    for target in (0, 3):
        name = f"source-t{target}"
        results[name] = run_one(
            out, name, target, 0,
            args.source_seconds if target == 0 else args.target3_seconds,
            20261103, scanner, verifier)
        if results[name]["final_witnesses"] <= 0:
            raise RuntimeError("the source did not produce a certified witness")
    for target, target_seeds, seconds in (
            (0, seeds, args.search_seconds),
            (3, seeds[:1], args.target3_seconds)):
        for seed in target_seeds:
            for label in ("cold", "warm"):
                name = f"t{target}-{seed}-{label}"
                results[name] = run_one(
                    out, name, target, 1, seconds, seed,
                    scanner, verifier,
                    transfer=(out / f"source-t{target}" if label == "warm" else None),
                    search_budget=True)
                write_json(out / "latest-comparison.json", results)
    for target, target_seeds in ((0, seeds), (3, seeds[:1])):
        for label in ("cold", "warm"):
            rows = [results[f"t{target}-{seed}-{label}"] for seed in target_seeds]
            results[f"t{target}-{label}-summary"] = {
                "seeds": target_seeds,
                "mean_raw_assignments": statistics.mean(x["raw_assignments"] for x in rows),
                "per_seed_raw_assignments": [x["raw_assignments"] for x in rows],
                "mean_failing_residuals_of_last_policy": (
                    statistics.mean(x["last_raw_policy_quality"]["failing_residual_masks"]
                        for x in rows if x["last_raw_policy_quality"]["status"] != "NO_RAW_POLICY")
                    if any(x["last_raw_policy_quality"]["status"] != "NO_RAW_POLICY"
                           for x in rows) else None),
                "mean_preparation_seconds": statistics.mean(x["preparation_seconds"] for x in rows),
                "search_budget_seconds_each": rows[0]["search_budget_seconds"],
                "classification_claim": "NONE",
            }
    results["benchmark_elapsed_wall_seconds"] = time.monotonic() - t
    results["interpretation"] = (
        "Equal active-search budgets; transfer audit/initialization independently "
        "counted. Last raw assignment is not the best found; solver effort is only "
        "observed counter deltas, not proof. One/three seeds are descriptive.")
    write_json(out / "amortized-comparison.json", results)
    print(json.dumps({
        k: v for k, v in results.items() if k.endswith("-summary")
    }, sort_keys=True))


if __name__ == "__main__":
    main()
