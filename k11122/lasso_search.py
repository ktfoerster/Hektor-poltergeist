"""Bounded rank-free SAT learning for K11122, with independently replayed lasso clauses.

A finite-suite SAT policy is NOT a positive result. A raw UNSAT is NOT a
negative result. Both require the existing independent certification chain.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import time

from merge_checkpoints import LATEST, merge
from sat_search import BooleanEncoding, partition, write_policy
from lasso_witness import (sha, selector_rows, trace, checked_clause, audit)


class CapturedPolicy(BooleanEncoding):
    """Identical global selectors as the rank encoder, but no residual ranks."""

    def __init__(self, n, target, body, seed=20261101, backend="cadical195"):
        self.body_path = Path(body)
        self.body = self.body_path.open("wb")
        try:
            super().__init__(n, target, seed=seed, backend=backend)
        except BaseException:
            self.body.close()
            raise

    def add_clause(self, clause):
        values = list(clause)
        super().add_clause(values)
        self.body.write((" ".join(map(str, values)) + " 0\n").encode())

    def close(self):
        try:
            self.delete()
        finally:
            self.body.close()


def checked_policy(payload, reference_rows):
    rows = payload["rows"]
    if len(rows) != len(reference_rows):
        raise RuntimeError("incomplete policy")
    result = {}
    for raw in rows:
        if (not isinstance(raw, list) or len(raw) != 5 or
                any(type(x) is not int for x in raw)):
            raise RuntimeError("invalid solver row")
        key, action = tuple(raw[:4]), raw[4]
        if key in result or action not in dict(reference_rows.get(key, [])):
            raise RuntimeError("duplicate/illegal solver row")
        result[key] = action
    if set(result) != set(reference_rows):
        raise RuntimeError("policy has missing/unexpected observation")
    return result


def source_hashes():
    names = ("lasso_search.py", "lasso_witness.py", "sat_search.py",
             "merge_checkpoints.py", "verify.cpp", "proof_cnf.py")
    return {name: sha(Path(__file__).with_name(name)) for name in names}


def snapshot(out, enc, masks, target, branch, witnesses, stats, imported):
    """Atomically replace complete checkpoint records; no solver-memory claim."""
    out = Path(out)
    enc.body.flush()
    if sha(enc.body_path) != enc.fingerprint.hexdigest():
        raise RuntimeError("CNF streaming fingerprint disagreement")
    formula_tmp = out / "formula.cnf.tmp"
    with formula_tmp.open("wb") as f, enc.body_path.open("rb") as body:
        f.write(f"p cnf {enc.top} {enc.clause_count}\n".encode())
        shutil.copyfileobj(body, f)
    formula_tmp.replace(out / "formula.cnf")
    meta = dict(schema=1, encoding="source-reachable-lasso-v1",
                n=enc.n, target=target, branch=branch,
                variables=enc.top, clauses=enc.clause_count,
                witnesses=witnesses, masks=len(masks),
                clause_body_sha256=enc.fingerprint.hexdigest(),
                source_sha256=source_hashes(), imported=imported,
                backend=enc.backend, seed=enc.seed,
                scope="finite residual suite and one physical-first-hop branch",
                progress=stats,
                commit=os.environ.get("GITHUB_SHA"))
    names = ("formula.cnf", "selectors.json", "masks.json", "witnesses.jsonl")
    meta["sha256"] = {name: sha(out / name) for name in names}
    temporary = out / "manifest.json.tmp"
    temporary.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")
    temporary.replace(out / "manifest.json")
    return meta


def independent_replay(out, policy, n, target, verifier):
    if verifier is None:
        return {"status": "NOT_RUN"}
    command = [str(Path(verifier).resolve()), str(Path(out) / "last-policy.tsv")]
    completed = subprocess.run(command, check=True, capture_output=True,
                               text=True, timeout=45)
    (Path(out) / "exhaustive-verifier.log").write_text(
        completed.stdout + completed.stderr)
    result = json.loads(completed.stdout)
    if n == 7:
        expected = 2979236 if target == 0 else 2937186
        if result.get("masks") != 524288 or result.get("obligations") != expected:
            raise RuntimeError("independent replay omitted obligations")
    return dict(status=("VERIFIED_POSITIVE_ONE_ORBIT" if result["failures"] == 0
                        else "FINITE_SAT_GLOBALLY_INVALID"),
                result=result, verifier_sha256=sha(verifier),
                policy_sha256=sha(Path(out) / "last-policy.tsv"))


def run(output, n, target, branch, masks, seconds, verifier=None,
        resume=None, seed=20261101, backend="cadical195",
        imported=None, max_new_per_round=96):
    if not 0.0 < seconds <= 180:
        raise ValueError("bounded run must be 0..180 seconds")
    if (not isinstance(masks, list) or not masks or
            masks != sorted(set(masks)) or
            any(type(x) is not int for x in masks)):
        raise ValueError("require nonempty strictly sorted frozen masks")
    independent = selector_rows(n, target)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    construction = time.monotonic()
    enc = CapturedPolicy(n, target, output / "clauses.body", seed, backend)
    partition(enc, branch)
    if enc.rows != independent:
        enc.close()
        raise RuntimeError("synthesizer and independent selector mapping disagree")
    (output / "selectors.json").write_text(json.dumps(
        [[*key, choices] for key, choices in independent.items()]) + "\n")
    (output / "masks.json").write_text(json.dumps(masks) + "\n")
    base_seconds = time.monotonic() - construction
    stats = dict(status="UNKNOWN", raw_models=0, finite_suite_candidates=0,
                 new_witnesses=0, inherited_witnesses=0,
                 solver_seconds=0.0, replay_seconds=0.0,
                 construction_seconds=base_seconds, budget_seconds=seconds,
                 completed_scans=0, interrupted_scans=0)
    learned = set()
    if imported is None:
        imported = {}
    witness_count = 0
    try:
        with (output / "witnesses.jsonl").open("w") as records:
            if resume is not None:
                previous = Path(resume)
                audit(previous)
                old = json.loads((previous / "manifest.json").read_text())
                if (old["n"], old["target"], old["branch"]) != (n, target, branch):
                    raise ValueError("resume model/branch mismatch")
                if json.loads((previous / "masks.json").read_text()) != masks:
                    raise ValueError("resume frozen suite mismatch")
                if old["source_sha256"] != source_hashes():
                    raise ValueError("resume source dependency mismatch")
                for line in (previous / "witnesses.jsonl").read_text().splitlines():
                    item = json.loads(line)
                    clause = checked_clause(item["witness"], n, target, independent)
                    if tuple(clause) in learned:
                        raise ValueError("duplicate resumed blocking clause")
                    learned.add(tuple(clause))
                    enc.add_clause(clause)
                    records.write(line + "\n")
                    witness_count += 1
                    stats["inherited_witnesses"] += 1
            records.flush()
            snapshot(output, enc, masks, target, branch, witness_count, stats, imported)
            iteration = 0
            while time.monotonic() - started < seconds:
                iteration += 1
                remaining = seconds - (time.monotonic() - started)
                before = time.monotonic()
                outcome, payload = enc.solve_for(max(0.01, min(3.0, remaining)),
                                                  output / f"solve-{iteration:05}.json",
                                                  conflict_budget=40000)
                stats["solver_seconds"] += time.monotonic() - before
                if outcome is None:
                    # Retain the worker's learned clauses across bounded slices.
                    if iteration % 5 == 0:
                        stats["elapsed_seconds"] = time.monotonic() - started
                        snapshot(output, enc, masks, target, branch,
                                 witness_count, stats, imported)
                    continue
                if outcome is False:
                    stats["status"] = "UNSAT_UNCERTIFIED"
                    break
                policy = checked_policy(payload, independent)
                stats["raw_models"] += 1
                write_policy(output / "last-policy.tsv", n, target, policy)
                added = 0
                full_scan = True
                before = time.monotonic()
                for mask in masks:
                    if time.monotonic() - started >= seconds:
                        full_scan = False
                        break
                    for source in range(n):
                        witness = trace(policy, n, target, mask, source)
                        if witness is None:
                            continue
                        clause = checked_clause(witness, n, target, independent)
                        if tuple(clause) in learned:
                            raise RuntimeError("SAT assignment violates an existing clause")
                        learned.add(tuple(clause))
                        enc.add_clause(clause)
                        records.write(json.dumps(
                            {"witness": witness, "clause": clause},
                            sort_keys=True, separators=(",", ":")) + "\n")
                        witness_count += 1
                        stats["new_witnesses"] += 1
                        added += 1
                        break  # one independent failure witness per residual
                    if added >= max_new_per_round:
                        full_scan = False
                        break
                stats["replay_seconds"] += time.monotonic() - before
                if full_scan:
                    stats["completed_scans"] += 1
                else:
                    stats["interrupted_scans"] += 1
                if full_scan and not added:
                    stats["finite_suite_candidates"] += 1
                    stats["status"] = "FINITE_SUITE_SAT_UNVERIFIED"
                    stats["independent_replay"] = independent_replay(
                        output, policy, n, target, verifier)
                    if stats["independent_replay"]["status"] == "VERIFIED_POSITIVE_ONE_ORBIT":
                        stats["status"] = "VERIFIED_POSITIVE_ONE_ORBIT"
                    elif stats["independent_replay"]["status"] == "FINITE_SAT_GLOBALLY_INVALID":
                        stats["status"] = "FINITE_SAT_GLOBALLY_INVALID"
                    break
                records.flush()
                stats["elapsed_seconds"] = time.monotonic() - started
                snapshot(output, enc, masks, target, branch,
                         witness_count, stats, imported)
            stats["elapsed_seconds"] = time.monotonic() - started
            stats["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            records.flush()
            snapshot(output, enc, masks, target, branch, witness_count, stats, imported)
    finally:
        enc.close()
    result = audit(output)
    (output / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    (output / "summary.json").write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n")
    (output / "clauses.body").unlink(missing_ok=True)
    return stats


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("run", "audit"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--target", type=int, choices=(0, 3), default=0)
    p.add_argument("--branch", type=int, choices=(-1, 0, 1), default=0)
    p.add_argument("--root", type=Path, default=LATEST)
    p.add_argument("--seconds", type=float, default=60)
    p.add_argument("--resume", type=Path)
    p.add_argument("--verify", type=Path)
    p.add_argument("--seed", type=int, default=20261101)
    p.add_argument("--backend", choices=("cadical195", "glucose42", "maplechrono"),
                   default="cadical195")
    a = p.parse_args()
    if a.mode == "audit":
        print(json.dumps(audit(a.output), indent=2))
        return
    if a.seed < 1 or a.seed > 2147483647:
        p.error("invalid seed")
    union = merge(a.root, a.target)  # strict branch provenance/hashes
    data = run(a.output, 7, a.target, a.branch, union["masks"], a.seconds,
               verifier=a.verify, resume=a.resume, seed=a.seed,
               backend=a.backend, imported={
                   "sources": union["sources"],
                   "intersection_count": union["intersection_count"],
                   "source_root": str(a.root)})
    print(json.dumps(data, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
