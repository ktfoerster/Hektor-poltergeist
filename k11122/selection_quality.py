"""Independent structural comparison of two sound lasso selection heuristics.

Compare ONE fixed complete policy and exact residual family; do not equate
shorter clauses with SAT solve speed or routing graph classification.
"""
import argparse
import json
from pathlib import Path
import statistics

from lasso_witness import checked_clause, geometry, selector_rows, trace


def compare(policy_file, masks_file, first_file, better_file):
    lines=Path(policy_file).read_text().splitlines()
    n, target=map(int, lines[0].split())
    policy={}
    for line in lines[1:]:
        fields=list(map(int,line.split()))
        if len(fields)!=5:
            raise ValueError("malformed fixed policy")
        key=tuple(fields[:4])
        if key in policy:
            raise ValueError("duplicate fixed policy")
        policy[key]=fields[4]
    rows=selector_rows(n,target)
    if set(policy)!=set(rows) or any(policy[key] not in dict(choices)
                                    for key,choices in rows.items()):
        raise ValueError("fixed policy is incomplete or illegal")
    masks=[int(x) for x in Path(masks_file).read_text().split()]
    if masks!=sorted(set(masks)) or not masks:
        raise ValueError("invalid frozen residual family")
    result={"scope":"One fixed invalid policy; clause geometry only, NOT solving speed",
            "n":n,"target":target,"residual_count":len(masks)}
    for mode,path in (("first",first_file),("short-diverse",better_file)):
        messages=[json.loads(x) for x in Path(path).read_text().splitlines()]
        if not messages or messages[-1].get("type")!="summary":
            raise ValueError("missing summary")
        report=messages[-1]
        if report["n"]!=n or report["target"]!=target or report["total_masks"]!=len(masks):
            raise ValueError("bad scanner mask/model metadata")
        clauses=[]
        for item in messages[:-1]:
            if set(item)!={"type","witness"} or item["type"]!="witness":
                raise ValueError("bad witness record")
            w=item["witness"]
            if w["mask"] not in masks or trace(policy,n,target,w["mask"],w["source"])!=w:
                raise ValueError("C++ witness disagrees with independent literal execution")
            clause=checked_clause(w,n,target,rows)
            if clause in clauses:
                raise ValueError("duplicate selected clause")
            if mode=="short-diverse":
                _, reachable=geometry(n,target,w["mask"])
                lengths=[len(checked_clause(v,n,target,rows))
                         for source in reachable-{target}
                         if (v:=trace(policy,n,target,w["mask"],source)) is not None]
                if len(clause)!=min(lengths):
                    raise ValueError("C++ did not use shortest failing source")
            clauses.append(clause)
        if report["witnesses"]!=len(clauses):
            raise ValueError("bad witness count")
        if mode=="short-diverse":
            if report.get("selection")!="short-diverse" or not report["scan_complete"]:
                raise ValueError("short-diverse scan incomplete")
            for i,a in enumerate(clauses):
                if any(set(b)<set(a) for j,b in enumerate(clauses) if i!=j):
                    raise ValueError("selected redundant (subsumed) clause")
        bad_masks=[x["witness"]["mask"] for x in messages[:-1]]
        distances=[(m^other).bit_count() for i,m in enumerate(bad_masks)
                   for other in bad_masks[i+1:]]
        lengths=list(map(len,clauses))
        result[mode]={"witness_count":len(clauses),
                      "scanned_masks":report["scanned_masks"],
                      "distinct_residuals":len(set(bad_masks)),
                      "mean_clause_literals":statistics.mean(lengths) if lengths else None,
                      "median_clause_literals":statistics.median(lengths) if lengths else None,
                      "min_pairwise_residual_hamming":min(distances) if distances else None,
                      "independent_replay":"PASS"}
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("policy","masks","first","short","output"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    result=compare(a.policy,a.masks,a.first,a.short)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
