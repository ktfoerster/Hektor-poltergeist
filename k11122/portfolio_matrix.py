"""Four-case K11122 portfolio study: both target orbits x both first-hop branches.

All initial policies remain legal; only independently checked, source-reachable
necessary clauses are pooled. Both source backends receive the SAME active
search duration; all three continuation arms use CaDiCaL, the SAME
first-witness scanner, SAME seed and SAME active search duration. This removes
the inherited hybrid modulo-clock as a comparison confound.

Each complete CNF and historical best policy is independently checked.
A benchmark is not evidence of a graph-positive policy or UNSAT proof.
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
from lasso_phase_preferences import generate
from lasso_portfolio import build
from lasso_witness import audit, sha
from sat_search import write_policy
from merge_checkpoints import merge, LATEST

HERE = Path(__file__).resolve().parent
CASES = ((0, 0), (0, 1), (3, 0), (3, 1))
BACKENDS = ("cadical195", "maplechrono")


def save(path, item):
    Path(path).write_text(json.dumps(item, indent=2, sort_keys=True) + "\n")


def read(path):
    return json.loads(Path(path).read_text())


def trajectory(bundle):
    """Use every completed C++ scanner policy hash, NOT every Nth quality score."""
    file = Path(bundle) / "cpp-batches.jsonl"
    records = [json.loads(line) for line in file.read_text().splitlines()]
    result = []
    previous = None
    for item in records:
        idx, digest = item.get("global_model_index"), item.get("policy_sha256")
        if (type(idx) is not int or
                previous is not None and idx != previous + 1 or
                type(digest) is not str or len(digest) != 64 or
                any(c not in "0123456789abcdef" for c in digest)):
            raise ValueError("noncontiguous or malformed complete-policy hash")
        previous = idx
        result.append(digest)
    return result


def verified_bundle(root, target, branch, with_best):
    folder = Path(root)
    meta = read(folder / "manifest.json")
    stats = read(folder / "summary.json")
    verified = audit(folder)
    ledger = check_committed(folder)
    expected = 2701 if target == 0 else 2181
    if (verified["status"] != "CHECKED" or
            (meta["n"], meta["target"], meta["branch"], meta["masks"])
            != (7, target, branch, expected) or
            ledger["verified_witnesses"] != meta["witnesses"] or
            verified["cnf_sha256"] != meta["sha256"]["formula.cnf"] or
            stats["status"] not in ("UNKNOWN", "UNSAT_UNCERTIFIED",
                                    "FINITE_SUITE_SAT_UNVERIFIED",
                                    "FINITE_SAT_GLOBALLY_INVALID",
                                    "VERIFIED_POSITIVE_ONE_ORBIT")):
        raise ValueError("bundle graph/branch/certificate provenance failed")
    best = independently_check_best(folder)
    if with_best:
        if (stats["quality_scored_raw_models"] > 0 and
                (best["status"] != "INDEPENDENTLY_REPLAYED_HISTORICAL_BEST" or
                 best["quality"] != stats["best_observed_raw_quality"])):
            raise ValueError("historical best has no matching independent replay")
        if stats["raw_models"] > 0 and best["status"] == "NO_SCORED_POLICY":
            raise ValueError("raw assignment not independently scored")
    return dict(
        target=target, branch=branch, masks=expected,
        checkpoint_manifest_sha256=sha(folder / "manifest.json"),
        cnf_sha256=verified["cnf_sha256"],
        witnessed_clauses=verified["witnesses"],
        raw_models=stats["raw_models"],
        new_necessary_clauses=stats["new_witnesses"],
        inherited_necessary_clauses=stats["inherited_witnesses"],
        status=stats["status"],
        finite_suite_candidates=stats["finite_suite_candidates"],
        preparation_seconds=stats["preparation_seconds"],
        active_search_seconds=stats["elapsed_seconds"],
        solver_conflicts_observed=stats["observed_solver_effort"]["conflicts"],
        solver_propagations_observed=stats["observed_solver_effort"]["propagations"],
        quality_samples=stats["quality_scored_raw_models"],
        best_historical_raw_policy=best,
    )


def run_one(output, target, branch, backend, seconds, seed,
            scanner, scorer, verifier, resume=None, phase=None,
            best_interval=0, witness_selection="hybrid"):
    output = Path(output)
    args = [sys.executable, str(HERE / "lasso_search.py"), "run",
            "--output", str(output), "--target", str(target),
            "--branch", str(branch), "--backend", backend,
            "--seconds", str(seconds), "--budget-scope", "search",
            "--seed", str(seed), "--walker", "cpp",
            "--batch-binary", str(scanner),
            "--verify", str(verifier),
            "--checkpoint-mode", "journal",
            "--witness-selection", witness_selection,
            "--hybrid-every", "8", "--max-new-per-round", "96"]
    if resume is not None:
        args += ["--resume", str(resume)]
    if phase is not None:
        args += ["--phase-policy", str(phase)]
    if best_interval:
        args += ["--best-interval", str(best_interval),
                 "--quality-binary", str(scorer)]
    started = time.monotonic()
    try:
        proc = subprocess.run(args, capture_output=True, text=True,
                              timeout=seconds + 135)
    except subprocess.TimeoutExpired as err:
        save(output.parent / (output.name + "-external-timeout.json"),
             {"status": "EXTERNAL_TIMEOUT", "elapsed": time.monotonic() - started})
        raise RuntimeError("bounded solver runner exceeded external wall timeout") from err
    (output.parent / (output.name + "-stdout.json")).write_text(proc.stdout)
    (output.parent / (output.name + "-stderr.txt")).write_text(proc.stderr)
    if proc.returncode:
        raise RuntimeError(f"{output.name}: exit={proc.returncode}:\n" +
                           proc.stderr[-2800:])
    info = verified_bundle(output, target, branch, bool(best_interval))
    info["external_wall_seconds"] = time.monotonic() - started
    info["backend"] = backend
    info["seed"] = seed
    info["witness_selection"] = witness_selection
    info["resumed_from_sha256"] = sha(Path(resume) / "manifest.json") if resume else None
    if resume:
        manifest = read(output / "manifest.json")
        if manifest["imported"]["resumed_from"]["manifest_sha256"] != info["resumed_from_sha256"]:
            raise ValueError("resume checkpoint manifest mismatch")
        if info["inherited_necessary_clauses"] != read(Path(resume) / "manifest.json")["witnesses"]:
            raise ValueError("resume omitted or forged necessary clauses")
    save(output.parent / (output.name + "-metrics.json"), info)
    return info


def case(root, target, branch, seed, source_seconds,
         continue_seconds, scanner, scorer, verifier, selective_modes=False):
    label = f"t{target}-b{branch}"
    folder = root / label
    folder.mkdir()
    report = dict(target=target, branch=branch,
                  frozen_masks=2701 if target == 0 else 2181,
                  sources={}, continuations={}, diversity={})
    frozen = merge(LATEST, target)["masks"]
    if len(frozen) != report["frozen_masks"] or frozen != sorted(set(frozen)):
        raise ValueError("unexpected frozen residual family")
    # Two distinct backends, identical policy domain and source budget.
    for backend in BACKENDS:
        name = f"source-{backend}"
        info = run_one(folder / name, target, branch, backend,
                       source_seconds, seed, scanner, scorer, verifier)
        if info["witnessed_clauses"] == 0:
            raise RuntimeError("source produced no independently checked necessary clause")
        report["sources"][backend] = info
        save(folder / "case-progress.json", report)
    seqs = [trajectory(folder / f"source-{backend}") for backend in BACKENDS]
    diversity = first_divergence(*seqs)
    report["diversity"]["cadical_vs_maple"] = diversity
    chosen = [folder / f"source-{backend}" for backend in BACKENDS]
    # If the nominal backend switch explores the same complete-policy prefix,
    # produce a legal alternative phase-only source and record whether it
    # ACTUALLY diverges before claiming a diversified portfolio.
    if not diversity["actually_divergent"]:
        phase = folder / "alternate-phase.tsv"
        write_policy(phase, 7, target, generate(7, target, branch, "hash", seed))
        alt = run_one(folder / "source-phase", target, branch, "cadical195",
                      source_seconds, seed, scanner, scorer, verifier, phase=phase)
        report["sources"]["cadical-phase"] = alt
        report["diversity"]["cadical_vs_phase"] = first_divergence(
            seqs[0], trajectory(folder / "source-phase"))
        if report["diversity"]["cadical_vs_phase"]["actually_divergent"]:
            chosen = [folder / "source-cadical195", folder / "source-phase"]
    actual = any(v["actually_divergent"] for v in report["diversity"].values())
    report["genuine_policy_hash_divergence"] = actual
    if not actual:
        # No fabricated diversity: a nondivergent instance is explicit
        # and still safe to pool; scientific interpretation excludes it.
        report["caution"] = "NO OBSERVED DIVERGENCE; pooled run NOT independent solver trajectory evidence"
    portfolio = folder / "portfolio"
    begun = time.monotonic()
    pooled = build(portfolio, chosen, target, branch)
    report["portfolio_construction_seconds"] = time.monotonic() - begun
    if pooled["status"] != "INDEPENDENTLY_AUDITED_PORTFOLIO" or pooled["source_count"] != 2:
        raise RuntimeError("invalid new independent portfolio")
    if pooled["input_witnesses"] != sum(
            read(source / "manifest.json")["witnesses"] for source in chosen):
        raise RuntimeError("portfolio contribution count mismatch")
    if pooled["deduplicated_witnesses"] > pooled["input_witnesses"]:
        raise RuntimeError("portfolio introduced non-necessary clauses")
    report["portfolio"] = dict(
        chosen_sources=[p.name for p in chosen],
        source_audit_seconds=report["portfolio_construction_seconds"],
        **pooled)
    if selective_modes:
        report["selective_portfolios"] = {}
        for selection in ("lossless", "shortest-half", "balanced-half"):
            started = time.monotonic()
            result = build(folder / ("portfolio-" + selection), chosen,
                           target, branch, selection=selection)
            if (result["status"] != "INDEPENDENTLY_AUDITED_PORTFOLIO" or
                    result["target"] != target or result["branch"] != branch or
                    result["residuals"] != report["frozen_masks"] or
                    result["unique_before_selection"] != pooled["deduplicated_witnesses"] or
                    result["deduplicated_witnesses"] <= 0 or
                    result["deduplicated_witnesses"] > pooled["deduplicated_witnesses"]):
                raise RuntimeError("selective portfolio changed an input domain or lost soundness")
            if (selection == "lossless") != result["exact_equivalence_to_full"]:
                raise RuntimeError("incorrect selection equivalence claim")
            if selection.endswith("half") and result["deduplicated_witnesses"] > (
                    pooled["deduplicated_witnesses"] + 1) // 2:
                raise RuntimeError("half-size clause limit ignored")
            report["selective_portfolios"][selection] = dict(
                construction_and_audit_seconds=time.monotonic() - started,
                **result)
            save(folder / "case-progress.json", report)
    save(folder / "case-progress.json", report)
    # All continuations use the exact SAME CaDiCaL195 backend, one-first-walk
    # strategy, seed, clock and search budget. The only intended comparison
    # variable is the independently certified starting CNF clauses.
    continuation_arms = [("cadical", folder / "source-cadical195"),
                         ("alternative", chosen[1]),
                         ("pooled", portfolio)]
    if selective_modes:
        continuation_arms.extend([
            ("shortest-half", folder / "portfolio-shortest-half"),
            ("balanced-half", folder / "portfolio-balanced-half")])
    for name, source in continuation_arms:
        info = run_one(folder / f"continue-{name}", target, branch,
                       "cadical195", continue_seconds, seed,
                       scanner, scorer, verifier,
                       resume=source, best_interval=8,
                       witness_selection="first")
        report["continuations"][name] = info
        save(folder / "case-progress.json", report)
    # Clauses learned on the frozen finite mask family remain necessary, not
    # a proof either way. Historical best is a raw SAT policy for a PREVIOUS
    # CNF, not a model of the terminal CNF.
    report["comparison"] = {
        name: dict(
            imported=info["inherited_necessary_clauses"],
            newly_certified=info["new_necessary_clauses"],
            total_certified=info["witnessed_clauses"],
            raw_models=info["raw_models"],
            observed_conflicts=info["solver_conflicts_observed"],
            preparation_seconds=info["preparation_seconds"],
            active_search_seconds=info["active_search_seconds"],
            best_sampled_failing_masks=(
                info["best_historical_raw_policy"]["quality"]["failing_residual_masks"]
                if info["best_historical_raw_policy"]["status"]
                == "INDEPENDENTLY_REPLAYED_HISTORICAL_BEST" else None),
            best_sampled_failed_sources=(
                info["best_historical_raw_policy"]["quality"]["failed_connected_sources"]
                if info["best_historical_raw_policy"]["status"]
                == "INDEPENDENTLY_REPLAYED_HISTORICAL_BEST" else None),
            terminal_cnf_sha256=info["cnf_sha256"],
            status=info["status"],
            finite_suite_candidates=info["finite_suite_candidates"],
        ) for name, info in report["continuations"].items()
    }
    report["interpretation"] = ("Single active-time-matched pilot on identical legal policy "
                                "space and frozen residuals; no verified graph result.")
    save(folder / "case-results.json", report)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--scanner", type=Path, required=True)
    p.add_argument("--scorer", type=Path, required=True)
    p.add_argument("--verifier", type=Path, required=True)
    p.add_argument("--source-seconds", type=float, default=7)
    p.add_argument("--continuation-seconds", type=float, default=9)
    p.add_argument("--seed", type=int, default=20261103)
    p.add_argument("--cases", default="all", choices=(
        "all", "t0-b0", "t0-b1", "t3-b0", "t3-b1"))
    p.add_argument("--selective-modes", action="store_true",
                   help="compare full pooling against shortest/balanced half and lossless pruning")
    args = p.parse_args()
    if (not 0 < args.source_seconds <= 45 or
            not 0 < args.continuation_seconds <= 45 or
            type(args.seed) is not int or not 1 <= args.seed <= 2147483647):
        p.error("bounded positive time budgets and integer seed required")
    root = args.output.resolve()
    if root.exists():
        p.error("new evidence directory required; never overwrite an old run")
    scanner = args.scanner.resolve(strict=True)
    scorer = args.scorer.resolve(strict=True)
    verifier = args.verifier.resolve(strict=True)
    root.mkdir(parents=True)
    cases = CASES if args.cases == "all" else [
        tuple(map(int, args.cases.replace("t", "").replace("b", "").split("-")))]
    # Above converts t0-b1 -> 0, 1; strict CLI limits case names.
    report = dict(
        schema=1, source_seconds=args.source_seconds,
        continuation_seconds=args.continuation_seconds, seed=args.seed,
        selective_modes=args.selective_modes,
        cases={}, semantic_scope="one-bit source-reachable K11122; frozen strict masks",
        interpretation="no one-bit resilience theorem; no uncertified status promoted")
    started = time.monotonic()
    for target, branch in cases:
        item = case(root, target, branch, args.seed,
                    args.source_seconds, args.continuation_seconds,
                    scanner, scorer, verifier,
                    selective_modes=args.selective_modes)
        report["cases"][f"t{target}-b{branch}"] = item
        save(root / "matrix-checkpoint.json", report)
    report["total_wall_seconds"] = time.monotonic() - started
    save(root / "matrix-results.json", report)
    for label, item in report["cases"].items():
        print(json.dumps({
            "case": label, "divergence": item["genuine_policy_hash_divergence"],
            "portfolio_unique": item["portfolio"]["deduplicated_witnesses"],
            "source_total": item["portfolio"]["input_witnesses"],
            "comparison": item["comparison"]}, sort_keys=True))
    print("MATHEMATICAL_STATUS=UNKNOWN_BOTH_ORBITS")


if __name__ == "__main__":
    main()
