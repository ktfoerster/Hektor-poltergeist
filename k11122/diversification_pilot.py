"""Finite, fully audited K11122 SAT trajectory diversification experiment.

Build two common certified rank-free checkpoints. Restart from each exact
checkpoint with alternative legal phase preferences or SAT backends, keeping
the routing CNF, frozen masks and active search budgets fixed.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from lasso_phase_preferences import generate
from lasso_divergence import compare
from lasso_witness import audit, sha
from sat_search import write_policy
from merge_checkpoints import merge, LATEST

HERE = Path(__file__).resolve().parent


def write(path, obj):
    path.write_text(json.dumps(obj, sort_keys=True, indent=2) + "\n")


def run_one(root, name, target, backend, seed, seconds, scanner,
            scorer, verifier, phase_policy=None, resume=None):
    out = root / name
    command = [sys.executable, str(HERE / "lasso_search.py"), "run",
               "--output", str(out), "--target", str(target),
               "--branch", "0", "--seconds", str(seconds),
               "--budget-scope", "search", "--backend", backend,
               "--seed", str(seed), "--walker", "cpp",
               "--batch-binary", str(scanner), "--verify", str(verifier),
               "--witness-selection", "hybrid", "--hybrid-every", "8",
               "--checkpoint-mode", "journal", "--max-new-per-round", "96"]
    if resume is not None:
        command.extend(["--resume", str(resume),
                        "--best-interval", "8", "--quality-binary", str(scorer)])
    if phase_policy is not None:
        command.extend(["--phase-policy", str(phase_policy)])
    started = time.monotonic()
    try:
        completed = subprocess.run(command, capture_output=True, text=True,
                                   timeout=seconds + 120)
    except subprocess.TimeoutExpired as error:
        write(root / (name + "-external-timeout.json"),
              {"status": "EXTERNAL_TIMEOUT", "wall_seconds": time.monotonic() - started,
               "command": command})
        raise RuntimeError("bounded diversification worker exceeded external timeout") from error
    (root / (name + "-stdout.json")).write_text(completed.stdout)
    (root / (name + "-stderr.log")).write_text(completed.stderr)
    if completed.returncode:
        raise RuntimeError(f"{name} failed: {completed.stderr[-3500:]}")
    check = audit(out)
    manifest = json.loads((out / "manifest.json").read_text())
    stats = json.loads((out / "summary.json").read_text())
    if (check["status"] != "CHECKED" or
            (manifest["target"], manifest["branch"], manifest["masks"]) !=
            (target, 0, 2701 if target == 0 else 2181) or
            manifest["sha256"]["formula.cnf"] != check["cnf_sha256"]):
        raise RuntimeError("independent full-CNF/source-orbit audit mismatch")
    if resume is None and check["witnesses"] == 0:
        raise RuntimeError("source failed to produce necessary clauses")
    if resume is not None:
        expected = sha(Path(resume) / "manifest.json")
        if (manifest["imported"]["resumed_from"]["manifest_sha256"] != expected or
                stats["inherited_witnesses"] !=
                json.loads((Path(resume) / "manifest.json").read_text())["witnesses"]):
            raise RuntimeError("diversification used mismatched initial constraints")
    write(root / (name + "-audit.json"), check)
    item = {
        "name": name, "target": target, "branch": 0, "backend": backend,
        "seed": seed, "phase_sha256": sha(phase_policy) if phase_policy else None,
        "cnf_sha256": check["cnf_sha256"],
        "raw_models": stats["raw_models"],
        "learned_necessary_clauses": stats["new_witnesses"],
        "inherited_necessary_clauses": stats["inherited_witnesses"],
        "status": stats["status"], "external_wall_seconds": time.monotonic() - started
    }
    write(root / (name + "-metrics.json"), item)
    return item


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scanner", required=True, type=Path)
    parser.add_argument("--scorer", required=True, type=Path)
    parser.add_argument("--verifier", required=True, type=Path)
    parser.add_argument("--source-seconds", type=float, default=9)
    parser.add_argument("--search-seconds", type=float, default=12)
    parser.add_argument("--target3-seconds", type=float, default=9)
    parser.add_argument("--seed", type=int, default=20261103)
    args = parser.parse_args()
    if not (0 < args.source_seconds <= 60 and
            0 < args.search_seconds <= 60 and
            0 < args.target3_seconds <= 60 and
            1 <= args.seed <= 2147483647):
        parser.error("all search limits and seed must be finite and bounded")
    root = args.output.resolve()
    if root.exists():
        parser.error("evidence directory must not exist")
    scanner, scorer, verifier = [
        path.resolve(strict=True) for path in
        (args.scanner, args.scorer, args.verifier)]
    root.mkdir(parents=True)
    phase_dir = root / "phases"
    phase_dir.mkdir()
    summary = {"scope": "different legal SAT phase hints and backends, same initial independently audited source CNF; no mathematical classification",
               "runs": {}}
    for target in (0, 3):
        frozen = merge(LATEST, target)["masks"]
        expected = 2701 if target == 0 else 2181
        if len(frozen) != expected or frozen != sorted(set(frozen)):
            raise RuntimeError("unexpected frozen mask domain")
        for variant in ("first", "hash"):
            path = phase_dir / f"t{target}-{variant}.tsv"
            write_policy(path, 7, target,
                         generate(7, target, 0, variant, args.seed))
        source = f"source-t{target}"
        summary["runs"][source] = run_one(
            root, source, target, "cadical195", args.seed,
            args.source_seconds if target == 0 else args.target3_seconds,
            scanner, scorer, verifier)
        write(root / "latest-diversification.json", summary)
        options = (
            [("cadical-none", "cadical195", None),
             ("cadical-first", "cadical195", phase_dir / f"t{target}-first.tsv"),
             ("cadical-hash", "cadical195", phase_dir / f"t{target}-hash.tsv"),
             ("glucose-none", "glucose42", None),
             ("maple-none", "maplechrono", None)]
            if target == 0 else
            [("cadical-none", "cadical195", None),
             ("cadical-hash", "cadical195", phase_dir / f"t{target}-hash.tsv"),
             ("maple-none", "maplechrono", None)]
        )
        for suffix, backend, phase in options:
            name = f"t{target}-{suffix}"
            summary["runs"][name] = run_one(
                root, name, target, backend, args.seed,
                args.search_seconds if target == 0 else args.target3_seconds,
                scanner, scorer, verifier, phase, root / source)
            write(root / "latest-diversification.json", summary)
        result = compare(
            root, target, f"t{target}-cadical-none",
            [f"t{target}-{suffix}" for suffix, _, _ in options[1:]])
        write(root / f"divergence-t{target}.json", result)
        summary[f"target{target}"] = dict(
            divergent=result["observed_at_least_one_actual_divergence"],
            best_failing_masks={key: value["best_historical_failing_masks"]
                                for key, value in result["runs"].items()},
            raw_models={key: value["raw_models"]
                        for key, value in result["runs"].items()},
            first_divergence={key: value["first_divergent_model_in_common_prefix"]
                              for key, value in result["divergence_from_baseline"].items()})
        write(root / "latest-diversification.json", summary)
    summary["mathematical_status"] = "UNKNOWN BOTH TARGET ORBITS unless independently certified"
    write(root / "diversification-summary.json", summary)
    print(json.dumps({k: value for k, value in summary.items()
                      if k.startswith("target")}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
