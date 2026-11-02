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

from lasso_checkpoint import checkpoint_root
from merge_checkpoints import LATEST, merge
from sat_search import BooleanEncoding, partition, write_policy
from lasso_witness import (sha, selector_rows, trace, checked_clause, audit)
from lasso_journal import Journal, check_committed, iter_committed_lines, lock_directory


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
    names = ("lasso_search.py", "lasso_witness.py", "lasso_batch.cpp", "lasso_journal.py", "lasso_checkpoint.py", "sat_search.py",
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
    names = ["formula.cnf", "selectors.json", "masks.json", "witnesses.jsonl"]
    for optional in ("masks.txt", "cpp-batches.jsonl", "last-policy.tsv",
                     "exhaustive-verifier.log"):
        if (out / optional).is_file():
            names.append(optional)
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
        imported=None, max_new_per_round=96, walker="python", batch_binary=None,
        allow_audited_migration=False, checkpoint_mode="journal", checkpoint_seconds=5.0,
        witness_selection="first"):
    if witness_selection not in ("first", "short-diverse") or (walker != "cpp" and witness_selection != "first"):
        raise ValueError("short-diverse selection requires --walker cpp; selection must be first or short-diverse")
    if type(max_new_per_round) is not int or max_new_per_round < 1:
        raise ValueError("max_new_per_round must be a positive integer")
    if checkpoint_mode == "generations":
        from lasso_generation_search import run as generation_run
        return generation_run(output, n, target, branch, masks, seconds,
                              verifier=verifier, resume=resume, seed=seed, backend=backend,
                              imported=imported, max_new_per_round=max_new_per_round,
                              walker=walker, batch_binary=batch_binary,
                              allow_audited_migration=allow_audited_migration,
                              checkpoint_seconds=checkpoint_seconds, witness_selection=witness_selection)
    if not 0.0 < seconds <= 180:
        raise ValueError("bounded run must be 0..180 seconds")
    if (not isinstance(masks, list) or not masks or
            masks != sorted(set(masks)) or
            any(type(x) is not int for x in masks)):
        raise ValueError("require nonempty strictly sorted frozen masks")
    if checkpoint_mode not in ("journal", "full"):
        raise ValueError("checkpoint mode must be journal or full")
    if walker not in ("python", "cpp"):
        raise ValueError("walker must be python or cpp")
    if walker == "cpp":
        if batch_binary is None or not Path(batch_binary).is_file():
            raise ValueError("cpp walker requires a compiled --batch-binary")
        batch_binary = Path(batch_binary).resolve()
    independent = selector_rows(n, target)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    # Nonblocking lock; never kill or replace another run's local owner.
    owner = lock_directory(output)
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
    if walker == "cpp":
        (output / "masks.txt").write_text("".join(f"{mask}\n" for mask in masks))
    base_seconds = time.monotonic() - construction
    stats = dict(status="UNKNOWN", raw_models=0, finite_suite_candidates=0,
                 new_witnesses=0, inherited_witnesses=0,
                 solver_seconds=0.0, replay_seconds=0.0,
                 construction_seconds=base_seconds, budget_seconds=seconds,
                 max_new_per_round=max_new_per_round, witness_selection=witness_selection,
                 clause_literals_total=0, clause_literals_min=None, clause_literals_max=0,
                 completed_scans=0, interrupted_scans=0, walker=walker,
                 batch_invocations=0, batch_cpp_seconds=0.0,
                 batch_python_check_seconds=0.0,
                 batch_binary_sha256=sha(batch_binary) if walker == "cpp" else None,
                 checkpoint_mode=checkpoint_mode, checkpoint_seconds=0.0,
                 checkpoint_count=0, final_export_seconds=0.0,
                 recovered_uncommitted_body_bytes=0,
                 recovered_uncommitted_witness_bytes=0)
    learned = set()
    if imported is None:
        imported = {}
    else:
        imported = dict(imported)
    witness_count = 0
    ledger = Journal(output, n, target, branch, masks, source_hashes(), imported)
    def record_witness(records, line):
        ledger.append(records, line)
    def save_checkpoint(records):
        before = time.monotonic()
        if checkpoint_mode == "journal":
            ledger.commit(enc, records, witness_count, stats)
        else:
            records.flush()
            snapshot(output, enc, masks, target, branch, witness_count, stats, imported)
        stats["checkpoint_seconds"] += time.monotonic() - before
        stats["checkpoint_count"] += 1
    try:
        with (output / "witnesses.jsonl").open("wb") as records:
            if resume is not None:
                previous = checkpoint_root(resume)
                if (previous / "manifest.json").is_file():
                    audit(previous)
                    old = json.loads((previous / "manifest.json").read_text())
                    resume_lines = (previous / "witnesses.jsonl").read_text().splitlines()
                else:
                    verified = check_committed(previous)
                    old = verified["metadata"]
                    stats["recovered_uncommitted_body_bytes"] = verified["uncommitted_body_bytes"]
                    stats["recovered_uncommitted_witness_bytes"] = verified["uncommitted_witness_bytes"]
                    resume_lines = iter_committed_lines(previous, old["witness_bytes"])
                if (old["n"], old["target"], old["branch"]) != (n, target, branch):
                    raise ValueError("resume model/branch mismatch")
                if json.loads((previous / "masks.json").read_text()) != masks:
                    raise ValueError("resume frozen suite mismatch")
                migrated = old["source_sha256"] != source_hashes()
                if migrated and not allow_audited_migration:
                    raise ValueError("resume source mismatch; use explicit audited migration")
                checkpoint_file = ("manifest.json" if (previous / "manifest.json").is_file()
                                   else "journal.json")
                imported["resumed_from"] = {
                    "checkpoint_kind": "complete" if checkpoint_file == "manifest.json" else "journal-prefix",
                    "checkpoint_sha256": sha(previous / checkpoint_file),
                    "formula_sha256": (sha(previous / "formula.cnf")
                                       if checkpoint_file == "manifest.json"
                                       else old["clause_body_sha256"]),
                    "source_sha256": old["source_sha256"],
                    "migration": "independently rechecked CNF and every committed witness"
                                 if migrated else "same dependency hashes",
                }
                if checkpoint_file == "manifest.json":
                    imported["resumed_from"]["manifest_sha256"] = sha(previous / checkpoint_file)
                for line in resume_lines:
                    item = json.loads(line)
                    clause = checked_clause(item["witness"], n, target, independent)
                    if tuple(clause) in learned:
                        raise ValueError("duplicate resumed blocking clause")
                    learned.add(tuple(clause))
                    enc.add_clause(clause)
                    record_witness(records, item)
                    witness_count += 1
                    stats["inherited_witnesses"] += 1
            save_checkpoint(records)
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
                        save_checkpoint(records)
                    continue
                if outcome is False:
                    stats["status"] = "UNSAT_UNCERTIFIED"
                    break
                policy = checked_policy(payload, independent)
                stats["raw_models"] += 1
                write_policy(output / "last-policy.tsv", n, target, policy)
                added = 0
                round_new = set()
                full_scan = True
                before = time.monotonic()
                batch_witnesses = None
                if walker == "cpp":
                    remaining = seconds - (time.monotonic() - started)
                    if remaining <= 0:
                        full_scan = False
                        stats["interrupted_scans"] += 1
                        break
                    cpp_started = time.monotonic()
                    stats["batch_invocations"] += 1
                    try:
                        process = subprocess.run(
                            [str(batch_binary), str((output / "last-policy.tsv").resolve()),
                             str((output / "masks.txt").resolve()), str(max_new_per_round), witness_selection],
                            capture_output=True, text=True, check=True,
                            timeout=max(0.01, min(15.0, remaining)))
                    except subprocess.TimeoutExpired:
                        full_scan = False
                        stats["interrupted_scans"] += 1
                        break
                    finally:
                        stats["batch_cpp_seconds"] += time.monotonic() - cpp_started
                    messages = [json.loads(line) for line in process.stdout.splitlines()]
                    if not messages or messages[-1].get("type") != "summary":
                        raise RuntimeError("missing C++ scan summary")
                    report = messages[-1]
                    batch_witnesses = []
                    if (report.get("schema") != 1 or report.get("n") != n or
                            report.get("target") != target or
                            report.get("total_masks") != len(masks) or
                            report.get("witnesses") != len(messages) - 1 or
                            report.get("scanned_masks", -1) > len(masks) or
                            type(report.get("scan_complete")) is not bool):
                        raise RuntimeError("invalid C++ scan accounting")
                    if witness_selection == "short-diverse":
                        if (report.get("selection") != "short-diverse" or
                                report.get("scan_complete") is not True or
                                report.get("scanned_masks") != len(masks) or
                                type(report.get("unique_candidates")) is not int or
                                report["unique_candidates"] < len(messages) - 1):
                            raise RuntimeError("invalid C++ short-diverse full-scan accounting")
                    for item in messages[:-1]:
                        if item.get("type") != "witness" or set(item) != {"type", "witness"}:
                            raise RuntimeError("invalid C++ scan record")
                        batch_witnesses.append(item["witness"])
                    # Preserve exact per-model scan statistics, without
                    # treating the untrusted scanner's success as proof.
                    with (output / "cpp-batches.jsonl").open("a") as cpp_logs:
                        cpp_logs.write(json.dumps({
                            "iteration": iteration,
                            "policy_sha256": sha(output / "last-policy.tsv"),
                            "report": report}, sort_keys=True) + "\n")
                    full_scan = report["scan_complete"]
                    if not batch_witnesses and full_scan:
                        # Verify zero failures from scratch with the separate
                        # Python implementation before accepting finite-suite SAT.
                        for mask in masks:
                            if time.monotonic() - started >= seconds:
                                full_scan = False
                                break
                            for source in range(n):
                                if trace(policy, n, target, mask, source) is not None:
                                    raise RuntimeError("C++ missed a reachable failure")
                if walker == "python":
                    def python_witnesses():
                        nonlocal full_scan
                        for mask in masks:
                            if time.monotonic() - started >= seconds:
                                full_scan = False
                                return
                            for source in range(n):
                                witness = trace(policy, n, target, mask, source)
                                if witness is not None:
                                    yield witness
                                    break  # one witness per mask
                    iterable = python_witnesses()
                else:
                    iterable = batch_witnesses
                for witness in iterable:
                    if time.monotonic() - started >= seconds:
                        full_scan = False
                        break
                    validation_started = time.monotonic()
                    clause = checked_clause(witness, n, target, independent)
                    stats["batch_python_check_seconds"] += time.monotonic() - validation_started
                    if tuple(clause) in learned:
                        if tuple(clause) in round_new:
                            continue
                        raise RuntimeError("SAT assignment violates a previously learned clause")
                    learned.add(tuple(clause))
                    round_new.add(tuple(clause))
                    stats["clause_literals_total"] += len(clause)
                    stats["clause_literals_min"] = min(len(clause), stats["clause_literals_min"]) if stats["clause_literals_min"] is not None else len(clause)
                    stats["clause_literals_max"] = max(len(clause), stats["clause_literals_max"])
                    enc.add_clause(clause)
                    record_witness(records, {"witness": witness, "clause": clause})
                    witness_count += 1
                    stats["new_witnesses"] += 1
                    added += 1
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
                stats["elapsed_seconds"] = time.monotonic() - started
                save_checkpoint(records)
            stats["elapsed_seconds"] = time.monotonic() - started
            stats["peak_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            save_checkpoint(records)
            # Journal prefix is the durable checkpoint; conventional final artifact once.
            if checkpoint_mode == "journal":
                final_start = time.monotonic()
                snapshot(output, enc, masks, target, branch,
                         witness_count, stats, imported)
                stats["final_export_seconds"] = time.monotonic() - final_start
    finally:
        enc.close()
        owner.close()
    result = audit(output)
    (output / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    (output / "summary.json").write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n")
    if checkpoint_mode == "full":
        (output / "clauses.body").unlink(missing_ok=True)
    # In journal mode preserve the committed clause prefix for crash recovery.
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
    p.add_argument("--walker", choices=("python", "cpp"), default="python")
    p.add_argument("--batch-binary", type=Path, help="compiled C++ scanner (only for --walker cpp)")
    p.add_argument("--checkpoint-mode", choices=("full", "journal", "generations"), default="journal",
                   help="full exports every round; journal commits fsynced prefixes")
    p.add_argument("--checkpoint-seconds", type=float, default=5.0,
                   help="complete snapshot interval in generations mode")
    p.add_argument("--max-new-per-round", type=int, default=96)
    p.add_argument("--witness-selection", choices=("first", "short-diverse"), default="first",
                   help="C++ witness preference, no routing-model restrictions")
    p.add_argument("--allow-audited-migration", action="store_true",
                   help="explicitly recheck old complete witness CNF despite source version change")
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
                   "source_root": str(a.root)},
               walker=a.walker, batch_binary=a.batch_binary,
               allow_audited_migration=a.allow_audited_migration,
               checkpoint_mode=a.checkpoint_mode,
               checkpoint_seconds=a.checkpoint_seconds,
               max_new_per_round=a.max_new_per_round,
                witness_selection=a.witness_selection)
    print(json.dumps(data, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
