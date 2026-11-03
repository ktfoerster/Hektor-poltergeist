"""Audit full K11122 routing-policy hash trajectories after controlled solver diversification.

A model's SHA-256 sequence, not its integer seed alone, demonstrates actual
search divergence. Divergence is an engineering observation, NOT a resilience
proof or a claim of independent statistical samples.
"""
import argparse
import json
from pathlib import Path
import re

from lasso_best import independently_check_best
from lasso_witness import audit, sha


_HASH = re.compile(r"^[0-9a-f]{64}$")


def first_divergence(reference, candidate):
    if not isinstance(reference, list) or not isinstance(candidate, list):
        raise ValueError("trajectories must be lists")
    for seq in (reference, candidate):
        if any(not isinstance(x, str) or not _HASH.fullmatch(x) for x in seq):
            raise ValueError("invalid raw-policy hash")
    common = min(len(reference), len(candidate))
    first = next((i + 1 for i in range(common)
                  if reference[i] != candidate[i]), None)
    return {
        "common_complete_models": common,
        "first_divergent_model_in_common_prefix": first,
        "shared_identical_prefix_models": first - 1 if first else common,
        "actually_divergent": first is not None,
        "no_divergence_observed_if_none": first is None,
        "reference_complete_models": len(reference),
        "candidate_complete_models": len(candidate),
    }


def load_trajectory(root, name, target):
    folder = Path(root) / name
    meta = json.loads((folder / "manifest.json").read_text())
    stats = json.loads((folder / "summary.json").read_text())
    check = audit(folder)
    if check["status"] != "CHECKED":
        raise ValueError("independent complete-CNF audit failed for " + name)
    if (meta["target"] != target or meta["branch"] != 0 or
            meta["masks"] != (2701 if target == 0 else 2181) or
            meta["sha256"]["formula.cnf"] != check["cnf_sha256"]):
        raise ValueError("graph/target/branch/frozen mask mismatch for " + name)
    if stats.get("status") not in (
            "UNKNOWN", "UNSAT_UNCERTIFIED", "FINITE_SUITE_SAT_UNVERIFIED",
            "FINITE_SAT_GLOBALLY_INVALID", "VERIFIED_POSITIVE_ONE_ORBIT"):
        raise ValueError("unrecognized solver classification status")
    info = meta.get("imported", {}).get("resumed_from")
    if not isinstance(info, dict) or not info.get("manifest_sha256"):
        raise ValueError("must start from one independently audited source")
    phase = stats.get("phase_preference")
    if phase is None:
        if (folder / "phase-policy.tsv").exists():
            raise ValueError("missing phase provenance for captured phase file")
    else:
        if (phase.get("sha256") != sha(folder / "phase-policy.tsv") or
                meta["sha256"].get("phase-policy.tsv") != phase["sha256"] or
                phase.get("semantics") != "branching phases only, no clauses or assumptions" or
                phase.get("branch") != 0 or phase.get("backend") != meta["backend"]):
            raise ValueError("phase file, metadata or manifest hash mismatch")
    quality = independently_check_best(folder)
    if stats.get("quality_scored_raw_models", 0):
        if (quality["status"] != "INDEPENDENTLY_REPLAYED_HISTORICAL_BEST" or
                quality["quality"] != stats["best_observed_raw_quality"]):
            raise ValueError("best policy failed independent literal replay")
    if stats["raw_models"] and quality["status"] == "NO_SCORED_POLICY":
        raise ValueError("raw search produced models without required best monitoring")
    logs_path = folder / "cpp-batches.jsonl"
    logs = [json.loads(x) for x in logs_path.read_text().splitlines()] \
        if logs_path.exists() else []
    previous = 0
    policies = []
    for log in logs:
        idx = log.get("global_model_index")
        policy_hash = log.get("policy_sha256")
        if (type(idx) is not int or idx <= previous or
                not isinstance(policy_hash, str) or not _HASH.fullmatch(policy_hash)):
            raise ValueError("nonmonotone or malformed scanner model/hash record")
        if (previous and idx != previous + 1):
            raise ValueError("scanner model hash sequence has a hole")
        previous = idx
        policies.append(policy_hash)
    if len(policies) > stats["raw_models"]:
        raise ValueError("more scanned policies than SAT models")
    if logs and (logs[0]["global_model_index"] != stats["selection_model_offset"] + 1):
        raise ValueError("incorrect resumed scanner starting model index")
    return {
        "name": name,
        "backend": meta["backend"],
        "seed": meta["seed"],
        "source_checkpoint_manifest_sha256": info["manifest_sha256"],
        "source_checkpoint_formula_sha256": info.get("formula_sha256"),
        "phase_preference_sha256": phase["sha256"] if phase else None,
        "solver_status": stats["status"],
        "raw_models": stats["raw_models"],
        "complete_policy_hashes": policies,
        "complete_policy_hash_records": len(policies),
        "first_policy_sha256": policies[0] if policies else None,
        "last_complete_policy_sha256": policies[-1] if policies else None,
        "terminal_cnf_sha256": check["cnf_sha256"],
        "independently_replayed_best_historical_policy": quality,
        "best_historical_failing_masks": (
            quality["quality"]["failing_residual_masks"]
            if quality["status"] == "INDEPENDENTLY_REPLAYED_HISTORICAL_BEST" else None),
        "solver_conflicts_observed": stats["observed_solver_effort"]["conflicts"],
        "solver_propagations_observed": stats["observed_solver_effort"]["propagations"],
        "active_search_seconds": stats["elapsed_seconds"],
        "preparation_seconds": stats["preparation_seconds"],
        "learned_necessary_clauses": stats["new_witnesses"],
        "inherited_necessary_clauses": stats["inherited_witnesses"],
        "finite_suite_candidates": stats["finite_suite_candidates"],
    }


def compare(root, target, baseline, alternatives):
    if not alternatives or baseline in alternatives or len(set(alternatives)) != len(alternatives):
        raise ValueError("require unique alternatives distinct from baseline")
    names = [baseline] + alternatives
    loaded = {name: load_trajectory(root, name, target) for name in names}
    source = loaded[baseline]["source_checkpoint_manifest_sha256"]
    inherited = loaded[baseline]["inherited_necessary_clauses"]
    for name, data in loaded.items():
        if (data["source_checkpoint_manifest_sha256"] != source or
                data["inherited_necessary_clauses"] != inherited):
            raise ValueError("experiment used different initial certified constraints")
    differences = {name: first_divergence(
        loaded[baseline]["complete_policy_hashes"],
        loaded[name]["complete_policy_hashes"]) for name in alternatives}
    return {
        "target": target, "branch": 0, "baseline": baseline,
        "complete_frozen_masks": 2701 if target == 0 else 2181,
        "matched_starting_source_manifest_sha256": source,
        "matched_inherited_necessary_clauses": inherited,
        "runs": loaded,
        "divergence_from_baseline": differences,
        "observed_at_least_one_actual_divergence":
            any(v["actually_divergent"] for v in differences.values()),
        "interpretation": (
            "Only SHA-256 differences within the same complete-model prefix "
            "demonstrate actual SAT search diversification. A historical best "
            "raw SAT assignment does not necessarily satisfy the terminal CNF. "
            "UNKNOWN/uncertified UNSAT never settle graph perfect resilience."),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--target", type=int, choices=(0, 3), required=True)
    p.add_argument("--baseline", required=True)
    p.add_argument("--alternatives", nargs="+", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    data = compare(args.root, args.target, args.baseline, args.alternatives)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    # Human-relevant digest only; full hash sequences remain in the evidence.
    print(json.dumps(dict(
        target=args.target,
        observed_at_least_one_actual_divergence=data["observed_at_least_one_actual_divergence"],
        divergence=data["divergence_from_baseline"],
        best_failing_masks={k: v["best_historical_failing_masks"]
                            for k, v in data["runs"].items()},
        raw_models={k: v["raw_models"] for k, v in data["runs"].items()}),
        indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
