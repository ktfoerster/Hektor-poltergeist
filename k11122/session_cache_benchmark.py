"""Bounded same-process certified-transfer cache benchmark.

Each source is independently fully reconstructed and every lasso witnessed
by the existing checker before the session cache is created. The cache is
never serialized as a portable proof; the original source files are checked
by content hashes on every reuse, and all destination CNFs are still
independently reconstructed and audited. No mathematical classification.
"""
import argparse
import json
from pathlib import Path
import statistics
import time

from amortization_benchmark import run_one, write_json
from lasso_search import run as search_run, source_hashes
from lasso_transfer_session import certify_session
from lasso_policy_quality import score
from lasso_witness import audit
from lasso_journal import check_committed
from lasso_best import independently_check_best
from merge_checkpoints import LATEST, merge


def cached_run(out, name, target, masks, seconds, seed, scanner, verifier, cache,
               best_interval=0, quality_binary=None):
    directory = out / name
    started = time.monotonic()
    stats = search_run(directory, 7, target, 1, masks, seconds,
                       seed=seed, walker="cpp", batch_binary=scanner,
                       verifier=verifier, checkpoint_mode="journal",
                       witness_selection="hybrid", hybrid_every=8,
                       max_new_per_round=96,
                       budget_scope="search", transfer_session_cache=cache,
                        best_interval=best_interval, quality_binary=quality_binary)
    external = time.monotonic()-started
    check = audit(directory)
    committed = check_committed(directory)
    meta = json.loads((directory/"manifest.json").read_text())
    quality = score(directory)
    best = independently_check_best(directory)
    if best_interval and (best["status"] != "INDEPENDENTLY_REPLAYED_HISTORICAL_BEST" or
                          stats["quality_scored_raw_models"] <= 0 or
                          best["quality"] != stats["best_observed_raw_quality"]):
        raise RuntimeError("independent best policy replay disagrees with recorded C++ ranking")
    info = meta["imported"]["opposite_branch_certificates"]
    if (check["status"]!="CHECKED" or
            committed["verified_witnesses"]!=meta["witnesses"] or
            info["cache_mode"]!="same_process_fully_audited_then_reused" or
            info["cache_semantic_audits_this_import"]!=0 or
            not info["source_audit"]["status"]=="CHECKED" or
            meta["sha256"]["formula.cnf"] != check["cnf_sha256"] or
            info["transferred"]!=stats["inherited_witnesses"] or
            stats["budget_scope"]!="search" or
            (meta["target"],meta["branch"],meta["masks"]) !=
            (target,1,len(masks))):
        raise RuntimeError("cached destination complete-CNF/provenance audit failed")
    if stats["solver_effort_samples"]<1:
        raise RuntimeError("cache trial lacked observed SAT effort")
    results = dict(
        target=target,branch=1,seed=seed,budget_scope="search",
        search_budget_seconds=seconds,
        total_elapsed_seconds=stats["total_wall_seconds"],
        external_execution_wall_seconds=external,
        preparation_seconds=stats["preparation_seconds"],
        transfer_seconds=stats["transfer_seconds"],
        raw_assignments=stats["raw_models"],
        new_witnesses=stats["new_witnesses"],
        inherited_witnesses=stats["inherited_witnesses"],
        final_witnesses=meta["witnesses"],
        observed_solver_effort=stats["observed_solver_effort"],
        solver_effort_samples=stats["solver_effort_samples"],
        unsampled_bounded_timeouts=stats["unsampled_bounded_timeouts"],
        solver_time=stats["solver_seconds"],replay_time=stats["replay_seconds"],
        finite_suite_candidates=stats["finite_suite_candidates"],
        status=stats["status"],cnf_sha256=check["cnf_sha256"],
        last_raw_policy_quality=quality,
        best_raw_policy_quality=best,
        quality_scored_raw_models=stats["quality_scored_raw_models"],
        quality_improvements=stats["quality_improvements"],
        quality_sampling_seconds=stats["quality_sampling_seconds"],
        source_manifest_sha256=info["source_manifest_sha256"],
        cache_semantic_audits_this_import=0,
        cache_hash_checked_files=info["cache_hash_checked_files"])
    write_json(out/(name+"-audit.json"), check)
    write_json(out/(name+"-quality.json"), quality)
    write_json(out/(name+"-metrics.json"), results)
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--scanner",required=True,type=Path)
    p.add_argument("--verifier",required=True,type=Path)
    p.add_argument("--source-seconds",type=float,default=10)
    p.add_argument("--search-seconds",type=float,default=10)
    p.add_argument("--target3-seconds",type=float,default=7)
    p.add_argument("--seeds",default="20261103,20261104,20261105")
    p.add_argument("--best-interval",type=int,default=0)
    p.add_argument("--quality-binary",type=Path)
    a=p.parse_args()
    seeds=[int(x) for x in a.seeds.split(",")]
    if not seeds or len(seeds)>5 or len(set(seeds))!=len(seeds):
        p.error("specify 1-5 distinct deterministic seeds")
    if (not 0<a.source_seconds<=60 or not 0<a.search_seconds<=60 or
            not 0<a.target3_seconds<=40):
        p.error("finite bounded budgets required")
    if (type(a.best_interval) is not int or not 0 <= a.best_interval <= 1024 or
            (a.best_interval>0 and a.quality_binary is None)):
        p.error("enable tracking with --best-interval N and --quality-binary")
    root=a.output.resolve()
    if root.exists():
        p.error("use a fresh output directory")
    root.mkdir(parents=True)
    scanner=a.scanner.resolve(strict=True)
    verifier=a.verifier.resolve(strict=True)
    quality_binary=a.quality_binary.resolve(strict=True) if a.best_interval else None
    all_results={}
    caches={}
    mask_families={}
    setup_times={}
    for target in (0,3):
        source_name=f"source-t{target}"
        seconds=a.source_seconds if target==0 else a.target3_seconds
        all_results[source_name]=run_one(
            root,source_name,target,0,seconds,20261103,scanner,verifier)
        masks=merge(LATEST,target)["masks"]
        if len(masks)!=(2701 if target==0 else 2181):
            raise RuntimeError("wrong frozen residual family")
        started=time.monotonic()
        caches[target]=certify_session(root/source_name,7,target,1,masks,
                                       expected_source_hashes=source_hashes())
        setup_times[target]=time.monotonic()-started
        mask_families[target]=masks
        write_json(root/f"cache-certification-t{target}.json", {
            "target":target,
            "session_only":True,
            "source_folder":source_name,
            "source_audit_seconds_once":setup_times[target],
            "full_source_audit":caches[target].certification,
            "cached_clauses":len(caches[target].entries),
            "source_file_hashes":dict(caches[target].attested_source_hashes),
            "never_treat_as_portable_proof":True})
    for target,target_seeds,seconds in (
            (0,seeds,a.search_seconds),
            (3,seeds[:1],a.target3_seconds)):
        for seed in target_seeds:
            for label in ("uncached","cached"):
                name=f"t{target}-{seed}-{label}"
                if label=="uncached":
                    result=run_one(
                        root,name,target,1,seconds,seed,scanner,verifier,
                        transfer=root/f"source-t{target}",search_budget=True,
                         best_interval=a.best_interval,quality_binary=quality_binary)
                else:
                    result=cached_run(
                        root,name,target,mask_families[target],seconds,seed,
                        scanner,verifier,caches[target],
                         best_interval=a.best_interval,quality_binary=quality_binary)
                all_results[name]=result
                if label=="cached":
                    cold=all_results[f"t{target}-{seed}-uncached"]
                    if not (cold["inherited_witnesses"]==
                            result["inherited_witnesses"]==
                            len(caches[target].entries) and
                            cold["source_manifest_sha256"]==
                            result["source_manifest_sha256"]):
                        raise RuntimeError("cache and full audit imported different constraints")
                write_json(root/"latest-comparison.json",all_results)
    for target,target_seeds in ((0,seeds),(3,seeds[:1])):
        comparisons={}
        for label in ("uncached","cached"):
            data=[all_results[f"t{target}-{seed}-{label}"]
                  for seed in target_seeds]
            comparisons[label]={
                "seed_models":[x["raw_assignments"] for x in data],
                "mean_models":statistics.mean(x["raw_assignments"] for x in data),
                "mean_preparation_seconds":statistics.mean(
                    x["preparation_seconds"] for x in data),
                "sum_preparation_seconds":sum(
                    x["preparation_seconds"] for x in data),
                "mean_failing_residuals_of_last_raw_policy":statistics.mean(
                    x["last_raw_policy_quality"]["failing_residual_masks"]
                    for x in data
                    if x["last_raw_policy_quality"]["status"]!="NO_RAW_POLICY"),
                "best_raw_policy_failure_masks": [
                    x["best_raw_policy_quality"]["quality"]["failing_residual_masks"]
                    if x["best_raw_policy_quality"]["status"]=="INDEPENDENTLY_REPLAYED_HISTORICAL_BEST"
                    else None for x in data],
                "best_raw_policy_failure_sources": [
                    x["best_raw_policy_quality"]["quality"]["failed_connected_sources"]
                    if x["best_raw_policy_quality"]["status"]=="INDEPENDENTLY_REPLAYED_HISTORICAL_BEST"
                    else None for x in data],
                "scored_raw_policies": [x["quality_scored_raw_models"] for x in data],
                "best_policy_improvements": [x["quality_improvements"] for x in data],
                "solver_effort_sampled_conflicts":[
                    x["observed_solver_effort"]["conflicts"] for x in data],
            }
        all_results[f"t{target}-summary"]=dict(
            seeds=target_seeds,
            source_initial_full_semantic_audit_seconds=setup_times[target],
            uncached=comparisons["uncached"],
            cached=comparisons["cached"],
            net_preparation_seconds_saved_after_source_audit=
                comparisons["uncached"]["sum_preparation_seconds"] -
                comparisons["cached"]["sum_preparation_seconds"] -
                setup_times[target],
            best_policy_sample_interval=a.best_interval,
            active_search_budget_seconds_each=(a.search_seconds if target==0
                                               else a.target3_seconds),
            research_status="UNKNOWN",
            caveat="Session-only cache, not a portable proof; active budgets equal. "
                   "Best historical raw policy is independently replayed but is not a solution of the terminal CNF.",
        )
    all_results["source_certifications"]={
        str(k):{"seconds":v,"cached_clauses":len(caches[k].entries)}
        for k,v in setup_times.items()}
    all_results["mathematical_classification"]="UNKNOWN both target orbits"
    write_json(root/"session-cache-comparison.json",all_results)
    print(json.dumps({k:v for k,v in all_results.items()
                      if k.endswith("-summary")},indent=2,sort_keys=True))


if __name__=="__main__":
    main()
