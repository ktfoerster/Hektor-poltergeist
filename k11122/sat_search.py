"""Boolean CNF synthesis for unrestricted one-bit K11122 routing.

The policy variables are global one-hot selectors.  Per residual, ``good``
and binary-rank variables are certificate variables only; they are not packet
state.  Every clause is streamed to CaDiCaL, while a deterministic clause
fingerprint makes the exact rebuilt instance auditable without storing a very
large DIMACS file.
"""
import argparse
import hashlib
import json
import math
import multiprocessing
import os
import pathlib
import subprocess
import time

import pysat
from pysat.solvers import Cadical195


DEPENDENCY = "python-sat==1.8.dev24/Cadical195"


def graph(n):
    return [(u, v) for u in range(n) for v in range(u + 1, n)
            if n != 7 or (u, v) not in ((3, 4), (5, 6))]


def adjacency(n, edges, mask):
    result = [0] * n
    for i, (u, v) in enumerate(edges):
        if mask >> i & 1:
            result[u] |= 1 << v
            result[v] |= 1 << u
    return result


def vertices(mask, n):
    return [v for v in range(n) if mask >> v & 1]


class BooleanEncoding:
    """Incremental CNF with exact global policy selectors and local proofs."""

    def __init__(self, n, target, seed=20261031):
        self.n, self.t, self.edges = n, target, graph(n)
        self.solver = Cadical195()
        # CaDiCaL is deterministic for this fixed seed and fixed clause order.
        self.solver.configure({"seed": seed})
        self.seed = seed
        self.top = 0
        self.clause_count = 0
        self.fingerprint = hashlib.sha256()
        self.rows = {}
        self.masks = []
        self.residual_stats = []
        host = adjacency(n, self.edges, (1 << len(self.edges)) - 1)
        for u in range(n):
            if u == target:
                continue
            for live in range(1, 1 << n):
                if live & ~host[u]:
                    continue
                arrivals = [(-1, 0)] + [(p, bit) for p in vertices(live, n)
                                        for bit in range(2)]
                for incoming, bit in arrivals:
                    key = (u, live, incoming, bit)
                    # Safe immediate delivery is the only normalization.
                    actions = [2 * target] if live >> target & 1 else [
                        2 * v + next_bit for v in vertices(live, n)
                        for next_bit in range(2)
                    ]
                    choices = [(action, self.new_var()) for action in actions]
                    self.rows[key] = choices
                    self.exactly_one([var for _, var in choices])

    def delete(self):
        if self.solver is not None:
            self.solver.delete()
            self.solver = None

    def new_var(self):
        self.top += 1
        return self.top

    def add_clause(self, clause):
        clause = list(clause)
        if not clause:
            raise ValueError("empty clause")
        self.solver.add_clause(clause)
        self.clause_count += 1
        self.fingerprint.update((" ".join(map(str, clause)) + " 0\n").encode())

    def exactly_one(self, variables):
        self.add_clause(variables)
        for i, left in enumerate(variables):
            for right in variables[i + 1:]:
                self.add_clause((-left, -right))

    def selector(self, key, action):
        for candidate, var in self.rows[key]:
            if candidate == action:
                return var
        raise KeyError((key, action))

    def fix_action(self, key, action):
        self.add_clause((self.selector(key, action),))

    def _and2(self, left, right):
        out = self.new_var()
        self.add_clause((-out, left))
        self.add_clause((-out, right))
        self.add_clause((out, -left, -right))
        return out

    def _and3(self, first, second, third):
        out = self.new_var()
        self.add_clause((-out, first))
        self.add_clause((-out, second))
        self.add_clause((-out, third))
        self.add_clause((out, -first, -second, -third))
        return out

    def _or2(self, left, right):
        out = self.new_var()
        self.add_clause((-left, out))
        self.add_clause((-right, out))
        self.add_clause((left, right, -out))
        return out

    def _xnor(self, left, right):
        out = self.new_var()
        self.add_clause((-out, -left, right))
        self.add_clause((-out, left, -right))
        self.add_clause((out, left, right))
        self.add_clause((out, -left, -right))
        return out

    def add_guarded_less(self, lesser, greater, guard):
        """Add guard -> unsigned(lesser) < unsigned(greater), LSB first."""
        if len(lesser) != len(greater) or not lesser:
            raise ValueError("rank width mismatch")
        index = len(lesser) - 1
        equal = self._xnor(lesser[index], greater[index])
        less = self._and2(-lesser[index], greater[index])
        for index in range(index - 1, -1, -1):
            new_less = self._and3(equal, -lesser[index], greater[index])
            less = self._or2(less, new_less)
            equal = self._and2(equal, self._xnor(lesser[index], greater[index]))
        self.add_clause((-guard, less))

    def add(self, mask):
        if mask in self.masks:
            return
        if not 0 <= mask < 1 << len(self.edges):
            raise ValueError("residual mask out of range")
        self.masks.append(mask)
        adj = adjacency(self.n, self.edges, mask)
        connected = {self.t}
        todo = [self.t]
        while todo:
            u = todo.pop()
            for v in vertices(adj[u], self.n):
                if v not in connected:
                    connected.add(v)
                    todo.append(v)
        states = [(u, incoming, bit) for u in sorted(connected) if u != self.t
                  for incoming in vertices(adj[u], self.n) for bit in range(2)]
        if not states:
            self.residual_stats.append({"mask": mask, "states": 0, "rank_bits": 0})
            return
        # The range has at least one distinct positive value per possible
        # nonterminal arrival configuration, not merely one per vertex.
        width = max(1, math.ceil(math.log2(len(states) + 1)))
        good = {state: self.new_var() for state in states}
        rank = {state: [self.new_var() for _ in range(width)] for state in states}
        for state in states:
            # A certified-good state has a positive rank. Bad/unused states
            # remain unconstrained and impose no delivery or acyclicity duty.
            self.add_clause([-good[state]] + rank[state])
        before_vars, before_clauses = self.top, self.clause_count
        for state in states:
            u, incoming, bit = state
            if adj[u] >> self.t & 1:
                # The normalized selector delivers immediately.
                continue
            row = (u, adj[u], incoming, bit)
            mux = [self.new_var() for _ in range(width)]
            for action, selected in self.rows[row]:
                v, next_bit = divmod(action, 2)
                successor = (v, u, next_bit)
                self.add_clause((-good[state], -selected, good[successor]))
                for j in range(width):
                    successor_bit = rank[successor][j]
                    self.add_clause((-selected, -mux[j], successor_bit))
                    self.add_clause((-selected, mux[j], -successor_bit))
            self.add_guarded_less(mux, rank[state], good[state])
        for source in sorted(connected - {self.t}):
            row = (source, adj[source], -1, 0)
            if adj[source] >> self.t & 1:
                continue
            for action, selected in self.rows[row]:
                v, next_bit = divmod(action, 2)
                self.add_clause((-selected, good[(v, source, next_bit)]))
        self.residual_stats.append({
            "mask": mask, "states": len(states), "rank_bits": width,
            "new_variables": self.top - before_vars,
            "new_clauses": self.clause_count - before_clauses,
        })

    def solve_for(self, seconds, result_path):
        """Solve in an owned fork so the wall-clock limit is enforceable.

        PySAT's CaDiCaL wrapper does not release the GIL for a Python timer and
        does not implement ``solve_limited``.  Forking after deterministic
        construction preserves the exact formula; the parent can terminate
        and join only its own solver child at the bound.  A SAT child returns
        the complete policy, not an unchecked partial model.
        """
        if "fork" not in multiprocessing.get_all_start_methods():
            raise RuntimeError("bounded CaDiCaL execution requires POSIX fork")
        result_path.unlink(missing_ok=True)
        context = multiprocessing.get_context("fork")
        process = context.Process(target=_solve_child, args=(self, result_path))
        process.start()
        process.join(seconds)
        if process.is_alive():
            process.terminate()
            process.join(10)
            if process.is_alive():
                process.kill()
                process.join()
            return None, {"child_exitcode": process.exitcode, "bounded_timeout": True}
        if process.exitcode != 0 or not result_path.exists():
            raise RuntimeError(f"CaDiCaL child failed with exit code {process.exitcode}")
        payload = json.loads(result_path.read_text())
        return payload["result"], payload

    def policy(self):
        model = self.solver.get_model()
        if model is None:
            raise RuntimeError("policy requested without SAT model")
        positive = {literal for literal in model if literal > 0}
        rows = {}
        for key, choices in self.rows.items():
            selected = [action for action, var in choices if var in positive]
            if len(selected) != 1:
                raise RuntimeError("invalid selector model")
            rows[key] = selected[0]
        return rows

    def statistics(self):
        return {
            "variables": self.top,
            "clauses": self.clause_count,
            "formula_sha256": self.fingerprint.copy().hexdigest(),
            "solver": self.solver.accum_stats(),
        }


def _solve_child(encoding, result_path):
    """Fork-only target; writes atomically so a killed child leaves no result."""
    try:
        result = encoding.solver.solve()
        payload = {
            "result": result,
            "solver": encoding.solver.accum_stats(),
            "child_pid": os.getpid(),
        }
        if result:
            payload["rows"] = [[*key, action]
                               for key, action in sorted(encoding.policy().items())]
        temporary = result_path.with_suffix(result_path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, sort_keys=True))
        temporary.replace(result_path)
    except BaseException as error:
        error_path = result_path.with_suffix(result_path.suffix + ".error")
        error_path.write_text(repr(error))
        raise


def partition(encoding, branch):
    """Disjoint exhaustive split by physical first hop, never a WLOG claim."""
    if branch == -1:
        return None
    host = adjacency(encoding.n, encoding.edges, (1 << len(encoding.edges)) - 1)
    source = next(u for u in range(encoding.n) if u != encoding.t and
                  len(vertices(host[u] & ~(1 << encoding.t), encoding.n)) >= 2)
    neighbors = vertices(host[source] & ~(1 << encoding.t), encoding.n)[:2]
    live = sum(1 << v for v in neighbors)
    row = (source, live, -1, 0)
    encoding.add_clause([encoding.selector(row, 2 * neighbors[branch] + bit)
                         for bit in range(2)])
    return {"row": list(row), "neighbors": neighbors, "branch": branch}


def load_checkpoint(path, target):
    old = json.loads(path.read_text())
    if old.get("target") != target or old.get("schema") not in (1, 2, 3):
        raise ValueError("checkpoint mismatch")
    masks = old.get("masks")
    if not masks or any(type(mask) is not int or not 0 <= mask < 1 << 19 for mask in masks):
        raise ValueError("invalid checkpoint masks")
    return list(dict.fromkeys(masks))


def write_policy(path, n, target, rows):
    path.write_text(f"{n} {target}\n" + "".join(
        " ".join(map(str, (*key, action))) + "\n"
        for key, action in sorted(rows.items())))


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, choices=(0, 3), required=True)
    parser.add_argument("--seconds", type=int, default=1200)
    parser.add_argument("--solve-seconds", type=int, default=1200)
    parser.add_argument("--branch", type=int, choices=(-1, 0, 1), default=-1)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--resume", type=pathlib.Path)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 14400 or not 1 <= args.solve_seconds <= 1200:
        parser.error("budget out of range")
    output = args.output
    if output.exists() and any(output.iterdir()):
        parser.error("output must be empty; use --resume with a NEW output")
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    deadline = started + args.seconds
    source_dir = pathlib.Path(__file__).parent
    binary = output / "verify"
    subprocess.run(["g++", "-O3", "-std=c++17", str(source_dir / "verify.cpp"),
                    "-o", str(binary)], check=True)
    encoding = BooleanEncoding(7, args.target)
    split = partition(encoding, args.branch)
    masks = [(1 << 19) - 1] + [((1 << 19) - 1) ^ (1 << i) for i in range(19)]
    if args.resume:
        masks = load_checkpoint(args.resume, args.target)
    initial_count = len(masks)
    status, stage, reason = "UNKNOWN", "constructing", ""
    iteration, last_candidate = 0, None
    source_hashes = {name: file_sha256(source_dir / name) for name in
                     ("sat_search.py", "verify.cpp", "merge_checkpoints.py")}

    def checkpoint():
        data = {
            "schema": 3, "target": args.target, "masks": encoding.masks,
            "status": status, "stage": stage, "iteration": iteration,
            "partition": split, "initial_residuals": initial_count,
            "reason": reason, "last_candidate": last_candidate,
            "elapsed_seconds": time.monotonic() - started,
            "backend": DEPENDENCY, "pysat": pysat.__version__,
            "seed": encoding.seed, "model": "static-undirected/common-source-local/two-state",
            "resume_sha256": file_sha256(args.resume) if args.resume else None,
            "source_sha256": source_hashes, **encoding.statistics(),
        }
        temporary = output / "checkpoint.tmp"
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True))
        temporary.replace(output / "checkpoint.json")

    try:
        checkpoint()
        for index, mask in enumerate(masks, 1):
            encoding.add(mask)
            if index % 25 == 0 or index == len(masks):
                checkpoint()
        stage = "solving"
        checkpoint()
        while time.monotonic() < deadline:
            limit = min(args.solve_seconds, max(0.001, deadline - time.monotonic()))
            before = time.monotonic()
            solve_result_path = output / f"solve-{iteration + 1}.json"
            result, solve_payload = encoding.solve_for(limit, solve_result_path)
            iteration += 1
            child_summary = {key: value for key, value in solve_payload.items()
                             if key != "rows"}
            record = {
                "iteration": iteration, "residuals": len(encoding.masks),
                "solver": "SAT" if result is True else "UNSAT" if result is False else "UNKNOWN",
                "limit_seconds": limit, "solve_seconds": time.monotonic() - before,
                "elapsed_seconds": time.monotonic() - started,
                **encoding.statistics(), "child": child_summary,
            }
            with (output / "progress.jsonl").open("a") as progress:
                progress.write(json.dumps(record, sort_keys=True) + "\n")
            print(json.dumps(record, sort_keys=True), flush=True)
            if result is None:
                reason = "interrupted at bounded solve slice; same incremental solver retained"
                checkpoint()
                continue
            if result is False:
                status, reason = "UNSAT_UNCERTIFIED", "CaDiCaL result has no independently checked proof"
                checkpoint()
                break
            rows = {tuple(item[:4]): item[4] for item in solve_payload["rows"]}
            write_policy(output / "candidate.tsv", 7, args.target, rows)
            replay = subprocess.run([str(binary), str(output / "candidate.tsv")], check=True,
                                    capture_output=True, text=True, timeout=180)
            audit = json.loads(replay.stdout)
            (output / "verification.json").write_text(json.dumps(audit, indent=2, sort_keys=True))
            expected = 2979236 if args.target == 0 else 2937186
            if audit["masks"] != 524288 or audit["obligations"] != expected:
                raise RuntimeError("incomplete independent verification")
            last_candidate = {
                "iteration": iteration, "sha256": file_sha256(output / "candidate.tsv"),
                "failures": audit["failures"],
            }
            if not audit["failures"]:
                status, stage, reason = "VERIFIED_POSITIVE", "verified", ""
                checkpoint()
                break
            if not audit["counterexamples"] or any(mask in encoding.masks for mask in audit["counterexamples"]):
                raise RuntimeError("encoder/checker disagreement: candidate fails enforced residual")
            for mask in audit["counterexamples"]:
                encoding.add(mask)
            checkpoint()
        stage = "finished"
        checkpoint()
    finally:
        encoding.delete()
    hashes = {path.name: file_sha256(path) for path in output.iterdir()
              if path.is_file() and path.name not in ("SHA256.json", "verify")}
    (output / "SHA256.json").write_text(json.dumps(hashes, indent=2, sort_keys=True))
    print(json.dumps({"status": status, "iterations": iteration,
                      "residuals": len(encoding.masks), "partition": split}), flush=True)


if __name__ == "__main__":
    main()
