"""Pre-registered K11122 clause-selection holdout on new legal SAT phases.

NO search result from this holdout may influence the choice of initial
portfolio: the choice table is frozen from the SHA1-pinned, committed
independently audited training report. Build sources once per case, use
identical source certificates for every mode/backend, and score *every*
raw SAT assignment in the holdout. No graph classification follows from
a finite suite, historical best, solver timeout or raw UNSAT.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from lasso_divergence import first_divergence
from lasso_phase_preferences import generate
from lasso_portfolio import build
from lasso_witness import audit, sha
from merge_checkpoints import merge, LATEST
from portfolio_matrix import run_one, trajectory
from sat_search import write_policy
from selective_backend_robustness import score, validate_selector_portfolios

TRAINING_FILE = Path(__file__).with_name("SELECTIVE_CROSS_BACKEND_RESULTS_20261104.json")
TRAINING_GIT_BLOB = "8c56fffbefb2d8c8117db65a0ffc45dc0ba91454"
TRAINING_CI_RUN = 41811555234
TRAINING_CODE_SHA = "172f039767657c5f83ffff8bd9e36bface2f5ce3"
CASES = ((0, 0), (0, 1), (3, 0), (3, 1))
BACKENDS = ("cadical195", "maplechrono")
MODES = ("all", "shortest-half", "balanced-half")
TIE_PREFERENCE = ("shortest-half", "balanced-half", "all")
SOURCE_PHASE_SALT = 20261104
CONTINUATION_PHASE_SALT = 20261105
HOLDOUT_SOLVER_SEED = 20261104


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def locked_training(path=TRAINING_FILE):
    data = Path(path).read_bytes()
    git_blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
    if git_blob != TRAINING_GIT_BLOB:
        raise ValueError("training file changed after preregistration")
    doc = json.loads(data)
    if (doc.get("schema") != 1 or
            doc.get("github_actions_run") != TRAINING_CI_RUN or
            doc.get("tested_code_commit") != TRAINING_CODE_SHA or
            doc["counts"].get("finite_suite_candidates") != 0 or
            set(doc.get("results", {})) !=
            {f"t{t}-b{b}" for t, b in CASES}):
        raise ValueError("unexpected training experiment provenance")
    chosen = {}
    training = {}
    for t, b in CASES:
        key = f"t{t}-b{b}"
        cell = doc["results"][key]
        if (not cell.get("actual_source_divergence") or
                cell.get("finite_suite_candidates") != 0):
            raise ValueError("training cell not independently diverse or unexplained SAT")
        chosen[key], training[key] = {}, {}
        for backend in BACKENDS:
            m = cell["best_sampled_failed_masks"][backend]
            if set(m) != set(MODES) or any(type(m[mode]) is not int or
                                           m[mode] < 0 for mode in MODES):
                raise ValueError("training score missing or invalid")
            mode = min(TIE_PREFERENCE, key=lambda s: (m[s], TIE_PREFERENCE.index(s)))
            chosen[key][backend] = mode
            training[key][backend] = {s: m[s] for s in MODES}
    return {
        "schema": 1, "status": "PREREGISTERED_BEFORE_HOLDOUT",
        "training_source": TRAINING_FILE.name,
        "training_git_blob_sha1": git_blob,
        "training_sha256": hashlib.sha256(data).hexdigest(),
        "training_workflow_run": TRAINING_CI_RUN,
        "training_code_commit": TRAINING_CODE_SHA,
        "selection_rule": "per case/backend minimum training failing masks; ties prefer shortest-half then balanced-half then all",
        "fixed_choices": chosen, "training_scores": training,
        "source_phase": {"variant": "hash", "salt": SOURCE_PHASE_SALT},
        "continuation_phase": {"variant": "hash", "salt": CONTINUATION_PHASE_SALT},
        "holdout_solver_seed": HOLDOUT_SOLVER_SEED,
        "evaluation": "all complete raw SAT policies scored; independent replay of historical best; no terminal-CNF or graph proof",
        "not_independent_mask_split": "same frozen mask suite, but new source/continuation phases; assesses trajectory transfer, not unseen failures"
    }


def changed_trajectory(first, second):
    seq_a, seq_b = trajectory(first), trajectory(second)
    result = first_divergence(seq_a, seq_b)
    result["models_compared"] = min(len(seq_a), len(seq_b))
    if result["models_compared"] == 0:
        raise RuntimeError("cannot test phase diversity without complete raw policies")
    return result


def make_phase(path, target, branch, salt):
    table = generate(7, target, branch, "hash", salt)
    write_policy(path, 7, target, table)
    return sha(path)


def evaluate_case(root, target, branch, prereg, source_seconds, continuation_seconds,
                  control_seconds, scanner, scorer, verifier):
    name = f"t{target}-b{branch}"
    case = root / name
    case.mkdir()
    masks = merge(LATEST, target)["masks"]
    if len(masks) != (2701 if target == 0 else 2181) or masks != sorted(set(masks)):
        raise ValueError("frozen residual family unexpectedly changed")
    holdout = dict(case=name, target=target, branch=branch, frozen_masks=len(masks),
                   sources={}, phase_checks={}, portfolios={}, continuations={},
                   preregistered_choices=prereg["fixed_choices"][name])
    source_phase = case / "heldout-source-phase.tsv"
    continuation_phase = case / "heldout-continuation-phase.tsv"
    holdout["source_phase_sha256"] = make_phase(
        source_phase, target, branch, SOURCE_PHASE_SALT)
    holdout["continuation_phase_sha256"] = make_phase(
        continuation_phase, target, branch, CONTINUATION_PHASE_SALT)
    if holdout["source_phase_sha256"] == holdout["continuation_phase_sha256"]:
        raise RuntimeError("holdout source and continuation phases unexpectedly equal")
    save(case / "progress.json", holdout)
    # Same code and seed as heldout source, but NO phase: the control exists
    # only to test whether the heldout legal phase actually changes trajectories.
    control = case / "phase-free-control"
    holdout["phase_free_control"] = run_one(
        control, target, branch, "cadical195",
        control_seconds, HOLDOUT_SOLVER_SEED, scanner, scorer, verifier,
        witness_selection="first")
    save(case / "progress.json", holdout)
    sources = {}
    for backend in BACKENDS:
        output = case / f"source-{backend}"
        info = run_one(output, target, branch, backend,
                       source_seconds, HOLDOUT_SOLVER_SEED,
                       scanner, scorer, verifier, phase=source_phase,
                       witness_selection="first")
        if info["witnessed_clauses"] <= 0 or info["finite_suite_candidates"] != 0:
            raise RuntimeError("unexpected source status in holdout")
        holdout["sources"][backend] = info
        sources[backend] = output
        save(case / "progress.json", holdout)
    holdout["phase_checks"]["new_phase_vs_no_phase_cadical"] = changed_trajectory(
        control, sources["cadical195"])
    holdout["phase_checks"]["cadical_vs_maple_source"] = changed_trajectory(
        sources["cadical195"], sources["maplechrono"])
    # Neither outcome is forced: honest reporting includes lack of divergence.
    save(case / "progress.json", holdout)

    portfolios = {}
    for mode in MODES:
        dest = case / f"portfolio-{mode}"
        start = time.monotonic()
        result = build(dest, [sources[backend] for backend in BACKENDS],
                       target, branch, selection=mode)
        result["wall_seconds_including_audit"] = time.monotonic() - start
        independently = audit(dest)
        if (independently["status"] != "CHECKED" or
                independently["cnf_sha256"] != result["formula_sha256"]):
            raise RuntimeError("independent holdout portfolio audit failed")
        portfolios[mode] = dest
        holdout["portfolios"][mode] = result
        save(case / "progress.json", holdout)
    validate_selector_portfolios(holdout["portfolios"], target, branch)
    for backend in BACKENDS:
        holdout["continuations"][backend] = {}
        for mode in MODES:
            dest = case / f"continuation-{backend}-{mode}"
            result = run_one(dest, target, branch, backend, continuation_seconds,
                             HOLDOUT_SOLVER_SEED, scanner, scorer, verifier,
                             resume=portfolios[mode], phase=continuation_phase,
                             best_interval=1, witness_selection="first")
            if (result["resumed_from_sha256"] != sha(portfolios[mode] / "manifest.json")
                    or result["inherited_necessary_clauses"] !=
                    holdout["portfolios"][mode]["deduplicated_witnesses"]):
                raise RuntimeError("holdout shared initial certificate provenance mismatch")
            holdout["continuations"][backend][mode] = {
                "source_cnf_sha256": sha(portfolios[mode] / "formula.cnf"),
                "initial_certified_clauses": result["inherited_necessary_clauses"],
                "learned_certified_clauses": result["new_necessary_clauses"],
                "raw_models": result["raw_models"],
                "observed_conflicts": result["solver_conflicts_observed"],
                "active_search_seconds": result["active_search_seconds"],
                "preparation_seconds": result["preparation_seconds"],
                "full_elapsed_seconds": result["external_wall_seconds"],
                "finite_suite_candidates": result["finite_suite_candidates"],
                "status": result["status"],
                "best_all_raw_policies_scored": result["quality_samples"] == result["raw_models"],
                "best_historical_policy": score(result)
            }
            if result["quality_samples"] != result["raw_models"]:
                raise RuntimeError("some raw SAT policies were not scored")
            save(case / "progress.json", holdout)
    holdout["continuation_backend_divergence"] = {}
    for mode in MODES:
        holdout["continuation_backend_divergence"][mode] = changed_trajectory(
            case / f"continuation-cadical195-{mode}",
            case / f"continuation-maplechrono-{mode}")
    for backend in BACKENDS:
        sel = holdout["preregistered_choices"][backend]
        scores = holdout["continuations"][backend]
        chosen = scores[sel]["best_historical_policy"]
        complete = scores["all"]["best_historical_policy"]
        if chosen is None or complete is None:
            holdout.setdefault("holdout_evaluation", {})[backend] = {
                "status": "NOT_SCORED", "chosen_mode": sel}
            continue
        chosen_score = chosen["failing_masks"]
        baseline_score = complete["failing_masks"]
        holdout.setdefault("holdout_evaluation", {})[backend] = {
            "chosen_before_holdout": sel,
            "chosen_failing_masks": chosen_score,
            "full_failing_masks": baseline_score,
            "chosen_minus_full": chosen_score - baseline_score,
            "improved_on_full": chosen_score < baseline_score,
            "tied_full": chosen_score == baseline_score,
            "posthoc_best_mode_for_diagnostics_only": min(
                MODES, key=lambda mode: scores[mode]["best_historical_policy"]["failing_masks"]),
            "holdout_source_diverged_from_phase_free_control": holdout["phase_checks"][
                "new_phase_vs_no_phase_cadical"]["actually_divergent"],
            "actual_cross_backend_source_divergence": holdout["phase_checks"][
                "cadical_vs_maple_source"]["actually_divergent"],
        }
    holdout["scientific_status"] = "UNKNOWN unless separately independently verified"
    save(case / "case-results.json", holdout)
    return holdout


def summarise(cases):
    result = {"cells": {}, "preregistered_less_than_full": 0,
              "preregistered_greater_than_full": 0,
              "preregistered_equal_to_full": 0,
              "nontrivial_selected_half_comparisons": 0,
              "actual_phase_trajectory_divergence_cells": 0,
              "actual_source_backend_divergence_cells": 0,
              "complete_finite_suite_candidates": 0}
    for name, r in cases.items():
        result["actual_phase_trajectory_divergence_cells"] += int(
            r["phase_checks"]["new_phase_vs_no_phase_cadical"]["actually_divergent"])
        result["actual_source_backend_divergence_cells"] += int(
            r["phase_checks"]["cadical_vs_maple_source"]["actually_divergent"])
        scores = {}
        for backend in BACKENDS:
            c = r["holdout_evaluation"][backend]
            result["preregistered_less_than_full"] += int(c.get("chosen_minus_full", 0) < 0)
            result["preregistered_greater_than_full"] += int(c.get("chosen_minus_full", 0) > 0)
            result["preregistered_equal_to_full"] += int(c.get("chosen_minus_full", 0) == 0)
            result["nontrivial_selected_half_comparisons"] += int(c.get("chosen_before_holdout") != "all")
            scores[backend] = {
                "preregistered_mode": c["chosen_before_holdout"],
                "preregistered_failing_masks": c["chosen_failing_masks"],
                "full_failing_masks": c["full_failing_masks"],
                "all_mode_holdout_scores": {mode: r["continuations"][backend][mode][
                    "best_historical_policy"]["failing_masks"] for mode in MODES}
            }
            result["complete_finite_suite_candidates"] += sum(
                r["continuations"][backend][mode]["finite_suite_candidates"]
                for mode in MODES)
        result["cells"][name] = scores
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scanner", type=Path, required=True)
    parser.add_argument("--scorer", type=Path, required=True)
    parser.add_argument("--verifier", type=Path, required=True)
    parser.add_argument("--cases", default="t0-b0,t0-b1,t3-b0,t3-b1")
    parser.add_argument("--source-seconds", type=float, default=4)
    parser.add_argument("--continue-seconds", type=float, default=5)
    parser.add_argument("--control-seconds", type=float, default=1)
    args = parser.parse_args()
    valid = {f"t{t}-b{b}": (t, b) for t, b in CASES}
    labels = args.cases.split(",")
    if (len(labels) != len(set(labels)) or not labels or len(labels) > 4 or
            any(name not in valid for name in labels) or
            not 0 < args.source_seconds <= 15 or
            not 0 < args.continue_seconds <= 15 or
            not 0 < args.control_seconds <= 10):
        parser.error("unique valid graph cases and strictly bounded search budgets required")
    training = locked_training()
    root = args.output.resolve()
    if root.exists():
        parser.error("refuse to overwrite previous experiment")
    scanner = args.scanner.resolve(strict=True)
    scorer = args.scorer.resolve(strict=True)
    verifier = args.verifier.resolve(strict=True)
    root.mkdir(parents=True)
    training["holdout_cases"] = labels
    training["source_active_search_seconds"] = args.source_seconds
    training["continuation_active_search_seconds"] = args.continue_seconds
    training["phase_free_control_active_seconds"] = args.control_seconds
    training["source_commit"] = os.environ.get("GITHUB_SHA")
    save(root / "precommitted-selection-plan.json", training)  # BEFORE any search
    results = {}
    started = time.monotonic()
    for name in labels:
        t, b = valid[name]
        results[name] = evaluate_case(root, t, b, training,
                                      args.source_seconds, args.continue_seconds,
                                      args.control_seconds, scanner, scorer, verifier)
        save(root / "latest-results.json", results)
    result = {
        "schema": 1,
        "experiment": "K11122 SHA1-pinned preregistered backend-aware clause-selection holdout",
        "preregistered_training_sha256": training["training_sha256"],
        "precommitted_plan_sha256": sha(root / "precommitted-selection-plan.json"),
        "holdout_phase_changed": {"source": SOURCE_PHASE_SALT,
                                  "continuation": CONTINUATION_PHASE_SALT},
        "holdout_seed": HOLDOUT_SOLVER_SEED,
        "report": summarise(results),
        "wall_seconds_including_all_source_and_audit_work": time.monotonic() - started,
        "scientific_status": "UNKNOWN for both destination orbits absent independently checked results",
        "caution": "fixed finite mask suite, four deterministic cases and one phase/seed holdout; no statistical or mathematical proof"}
    save(root / "holdout-results.json", result)
    print(json.dumps(result["report"], sort_keys=True))
    print("ONE_BIT_K11122_CLASSIFICATION=UNKNOWN")


if __name__ == "__main__":
    main()
