"""Matched cross-backend validation of selective K11122 necessary-clause portfolios.

Build each source *once* per graph cell and reuse the SAME audited source
certificates for all portfolio subsets and continuation backends. Neither
the initial clause selection nor backend preferences restrict legal routing.
All evidence is independently audited and every source/path has a strict
bounded search duration. This is NOT a resilience proof.
"""
import argparse
import json
from pathlib import Path
import sys
import time

from lasso_divergence import first_divergence
from lasso_portfolio import build
from lasso_witness import audit, sha
from merge_checkpoints import merge, LATEST
from portfolio_matrix import run_one, trajectory, verified_bundle

CASES=((0,0),(0,1),(3,0),(3,1))
SOURCE_BACKENDS=("cadical195","maplechrono")
SELECTORS=("all","shortest-half","balanced-half")


def write(path, content):
    Path(path).write_text(json.dumps(content, sort_keys=True, indent=2)+"\n")


def score(info):
    status=info["best_historical_raw_policy"]["status"]
    best=info["best_historical_raw_policy"]
    if status == "INDEPENDENTLY_REPLAYED_HISTORICAL_BEST":
        return dict(failing_masks=best["quality"]["failing_residual_masks"],
                    failing_sources=best["quality"]["failed_connected_sources"],
                    policy_sha256=best["policy_sha256"],
                    observed_raw_model=best["source_model_index"])
    if status=="NO_SCORED_POLICY":
        return None
    raise ValueError("unverified best-policy score")


def compare_sources(source_a, source_b):
    x,y=trajectory(source_a),trajectory(source_b)
    result=first_divergence(x,y)
    result["common_prefix_checked"]=min(len(x),len(y))
    return result


def validate_selector_portfolios(reports, target, branch):
    base=reports["all"]
    total=base["deduplicated_witnesses"]
    assert base["selection"]=="all" and total>0
    for mode in ("shortest-half","balanced-half"):
        item=reports[mode]
        if (item["target"]!=target or item["branch"]!=branch or
                item["unique_before_selection"]!=total or
                not 0 < item["deduplicated_witnesses"]<= (total+1)//2 or
                item["exact_equivalence_to_full"]):
            raise ValueError("selective subset changed problem or cap")
        # Full and subset certificates are structurally audited separately.
        if item["status"]!="INDEPENDENTLY_AUDITED_PORTFOLIO":
            raise ValueError("selective portfolio not independently certified")
    return total


def case(root,target,branch,source_seconds,search_seconds,seed,scanner,scorer,verifier):
    name=f"t{target}-b{branch}"
    directory=root/name
    directory.mkdir()
    frozen=merge(LATEST,target)["masks"]
    expected=2701 if target==0 else 2181
    if len(frozen)!=expected or frozen!=sorted(set(frozen)):
        raise ValueError("strict frozen mask family changed")
    sources={}
    progress=dict(target=target,branch=branch,masks=expected,
                  source_bundles={},portfolios={},continuations={})
    for backend in SOURCE_BACKENDS:
        path=directory/f"source-{backend}"
        info=run_one(path,target,branch,backend,source_seconds,seed,
                     scanner,scorer,verifier,witness_selection="hybrid")
        if info["witnessed_clauses"]<=0 or info["finite_suite_candidates"]!=0:
            raise ValueError("unsupported source state for controlled comparison")
        sources[backend]=path
        progress["source_bundles"][backend]=info
        write(directory/"progress.json",progress)
    div=compare_sources(sources["cadical195"],sources["maplechrono"])
    progress["source_trajectory_divergence"]=div
    if not div["actually_divergent"]:
        progress["interpretation_warning"]="No actual divergence; backend names are not independent evidence"
    paths, reports={},{}
    for mode in SELECTORS:
        dest=directory/f"portfolio-{mode}"
        started=time.monotonic()
        result=build(dest,[sources[backend] for backend in SOURCE_BACKENDS],
                     target,branch,selection=mode)
        result["construction_wall_seconds"]=time.monotonic()-started
        check=audit(dest)
        if check["status"]!="CHECKED" or check["cnf_sha256"]!=result["formula_sha256"]:
            raise ValueError("portfolio independent reconstruction failed")
        paths[mode]=dest
        reports[mode]=result
        progress["portfolios"][mode]=result
        write(directory/"progress.json",progress)
    validate_selector_portfolios(reports,target,branch)
    for continuation_backend in SOURCE_BACKENDS:
        progress["continuations"][continuation_backend]={}
        for mode in SELECTORS:
            output=directory/f"continue-{continuation_backend}-{mode}"
            info=run_one(output,target,branch,continuation_backend,
                         search_seconds,seed,scanner,scorer,verifier,
                         resume=paths[mode],best_interval=8,
                         witness_selection="first")
            if (info["masks"]!=expected or info["target"]!=target or
                    info["branch"]!=branch or
                    info["inherited_necessary_clauses"]!=reports[mode]["deduplicated_witnesses"] or
                    info["resumed_from_sha256"]!=sha(paths[mode]/"manifest.json")):
                raise RuntimeError("continuation certified input mismatch")
            progress["continuations"][continuation_backend][mode]={
                "source_initial_clause_count":info["inherited_necessary_clauses"],
                "new_necessary_clauses":info["new_necessary_clauses"],
                "raw_models":info["raw_models"],
                "observed_sat_conflicts":info["solver_conflicts_observed"],
                "observed_sat_propagations":info["solver_propagations_observed"],
                "search_seconds":info["active_search_seconds"],
                "preparation_seconds":info["preparation_seconds"],
                "external_wall_seconds":info["external_wall_seconds"],
                "finite_suite_candidates":info["finite_suite_candidates"],
                "status":info["status"],
                "last_best_sampled_historical_invalid_policy":score(info),
                "source_sha256":info["resumed_from_sha256"],
                "terminal_cnf_sha256":info["cnf_sha256"],
            }
            write(directory/"progress.json",progress)
    for mode in SELECTORS:
        a=directory/f"continue-cadical195-{mode}"
        b=directory/f"continue-maplechrono-{mode}"
        progress.setdefault("continuation_backend_divergence",{})[mode]=compare_sources(a,b)
    # Here the source portfolio is fixed within each continuation-backend comparison.
    # The only intended factor is initial subset; the two backends are NOT
    # independent random samples.
    progress["scope"]=(
      "best sampled historical raw policies; equal initial source certificates "
      "per case; no terminal CNF SAT or full-graph proof")
    write(directory/"case-results.json",progress)
    return progress


def summarize(results):
    concise={}
    for name,r in results.items():
        arms={}
        for backend in SOURCE_BACKENDS:
            arms[backend]={mode:r["continuations"][backend][mode][
                "last_best_sampled_historical_invalid_policy"]["failing_masks"]
                if r["continuations"][backend][mode][
                "last_best_sampled_historical_invalid_policy"] is not None else None
                for mode in SELECTORS}
        concise[name]=dict(
            actual_source_divergence=r["source_trajectory_divergence"]["actually_divergent"],
            input_unique_clauses=r["portfolios"]["all"]["deduplicated_witnesses"],
            selected_clause_counts={mode:r["portfolios"][mode]["deduplicated_witnesses"]
                                    for mode in SELECTORS},
            best_sampled_failed_masks=arms,
            continuation_divergence={
                mode:r["continuation_backend_divergence"][mode]["actually_divergent"]
                for mode in SELECTORS},
            all_statuses=[r["continuations"][be][mode]["status"]
                          for be in SOURCE_BACKENDS for mode in SELECTORS],
            finite_suite_candidates=sum(r["continuations"][be][mode]["finite_suite_candidates"]
                                        for be in SOURCE_BACKENDS for mode in SELECTORS))
    return concise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--scanner",required=True,type=Path)
    p.add_argument("--scorer",required=True,type=Path)
    p.add_argument("--verifier",required=True,type=Path)
    p.add_argument("--cases",default="t0-b1,t3-b1")
    p.add_argument("--source-seconds",type=float,default=4)
    p.add_argument("--continuation-seconds",type=float,default=5)
    p.add_argument("--seed",type=int,default=20261103)
    args=p.parse_args()
    if not (0<args.source_seconds<=15 and 0<args.continuation_seconds<=15
            and 1<=args.seed<=2147483647):
        p.error("bounded positive time budget and seed required")
    case_names=args.cases.split(",")
    legal={f"t{t}-b{b}":(t,b) for t,b in CASES}
    if not case_names or len(case_names)>4 or len(case_names)!=len(set(case_names)) or any(x not in legal for x in case_names):
        p.error("cases must be unique exact t0-b0,t0-b1,t3-b0,t3-b1")
    output=args.output.resolve()
    if output.exists():
        p.error("refuse to overwrite existing evidence")
    scanner=args.scanner.resolve(strict=True)
    scorer=args.scorer.resolve(strict=True)
    verifier=args.verifier.resolve(strict=True)
    output.mkdir(parents=True)
    results={}
    started=time.monotonic()
    for name in case_names:
        t,b=legal[name]
        results[name]=case(output,t,b,args.source_seconds,args.continuation_seconds,
                           args.seed,scanner,scorer,verifier)
        write(output/"latest-results.json",dict(results=results))
    report=dict(schema=1,source_seconds=args.source_seconds,
                continuation_seconds=args.continuation_seconds,seed=args.seed,
                tested_cases=case_names,overall_wall_seconds=time.monotonic()-started,
                summary=summarize(results),
                scientific_status="UNKNOWN unless independently checked proof/policy",
                caution="one fixed seed and source pair per cell, two continuation backends; no statistical superiority claim")
    write(output/"matched-backend-summary.json",report)
    print(json.dumps(report["summary"],sort_keys=True))
    print("K11122_ONE_BIT_STATUS=UNKNOWN")


if __name__=="__main__":
    main()
