#!/usr/bin/env python3
"""Bounded labelled-graph enumeration + MiniSat 3-colourability smoke test.

This is not a perfect-resilience/touring encoding.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import platform
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def graph_edges(vertices: int, mask: int) -> list[tuple[int, int]]:
    """Decode a labelled simple graph using lexicographically ordered edges."""
    possible = list(itertools.combinations(range(vertices), 2))
    if mask < 0 or mask >= (1 << len(possible)):
        raise ValueError("graph mask outside graph space")
    return [edge for bit, edge in enumerate(possible) if mask & (1 << bit)]


def var(vertex: int, colour: int) -> int:
    return 3 * vertex + colour + 1


def colour_cnf(vertices: int, edges: list[tuple[int, int]]) -> list[list[int]]:
    """Exactly one of three colours per vertex; incident colours differ."""
    clauses = []
    for vertex in range(vertices):
        clauses.append([var(vertex, c) for c in range(3)])
        for c, d in itertools.combinations(range(3), 2):
            clauses.append([-var(vertex, c), -var(vertex, d)])
    for u, v in edges:
        for c in range(3):
            clauses.append([-var(u, c), -var(v, c)])
    return clauses


def dimacs(vertices: int, clauses: list[list[int]]) -> str:
    lines = [f"p cnf {3 * vertices} {len(clauses)}"]
    lines.extend(" ".join(map(str, clause)) + " 0" for clause in clauses)
    return "\n".join(lines) + "\n"


def brute_three_colours(vertices: int, edges: list[tuple[int, int]]) -> bool:
    """Independent bounded checker; practical only for these tiny graphs."""
    neighbours: list[list[int]] = [[] for _ in range(vertices)]
    for u, v in edges:
        neighbours[u].append(v)
        neighbours[v].append(u)
    order = sorted(range(vertices), key=lambda u: -len(neighbours[u]))
    colours = [-1] * vertices

    def search(index: int) -> bool:
        if index == vertices:
            return True
        u = order[index]
        forbidden = {colours[v] for v in neighbours[u] if colours[v] != -1}
        for colour in range(3):
            if colour not in forbidden:
                colours[u] = colour
                if search(index + 1):
                    return True
        colours[u] = -1
        return False

    return search(0)


def validate_witness(vertices: int, edges: list[tuple[int, int]], literals: list[int]) -> list[int]:
    positive = {literal for literal in literals if literal > 0}
    colouring = []
    for u in range(vertices):
        selected = [c for c in range(3) if var(u, c) in positive]
        if len(selected) != 1:
            raise ValueError("MiniSat model does not assign exactly one colour")
        colouring.append(selected[0])
    if any(colouring[u] == colouring[v] for u, v in edges):
        raise ValueError("MiniSat model violates an edge constraint")
    return colouring


def solve_with_minisat(vertices: int, edges: list[tuple[int, int]], workdir: Path) -> tuple[bool, list[int] | None]:
    input_file = workdir / "case.cnf"
    output_file = workdir / "case.model"
    input_file.write_text(dimacs(vertices, colour_cnf(vertices, edges)), encoding="ascii")
    try:
        result = subprocess.run(
            ["minisat", str(input_file), str(output_file)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("MiniSat executable not installed") from exc
    if result.returncode not in (10, 20):
        raise RuntimeError(f"MiniSat failed: exit={result.returncode}; {result.stderr[-400:]}")
    lines = output_file.read_text(encoding="ascii").splitlines()
    if not lines or lines[0].strip() not in ("SAT", "UNSAT"):
        raise RuntimeError("MiniSat did not produce a recognised result")
    sat = lines[0].strip() == "SAT"
    if sat != (result.returncode == 10):
        raise RuntimeError("MiniSat exit code and output disagree")
    if not sat:
        return False, None
    literals = [int(token) for line in lines[1:] for token in line.split() if token != "0"]
    return True, validate_witness(vertices, edges, literals)


def parse_config(config_file: Path) -> dict:
    data = json.loads(config_file.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("experiment") != "graph-3colourability-demo":
        raise ValueError("unsupported experiment kind")
    for key in ("vertices", "start_mask", "graph_count", "shard_count"):
        if type(data.get(key)) is not int:  # bool is not an acceptable integer
            raise ValueError(f"{key} must be an integer")
    n = data["vertices"]
    start = data["start_mask"]
    count = data["graph_count"]
    if not 1 <= n <= 7 or start < 0 or not 1 <= count <= 32768:
        raise ValueError("bounded graph settings exceeded")
    if data["shard_count"] != 4:
        raise ValueError("this workflow uses exactly four shards")
    if start + count > (1 << (n * (n - 1) // 2)):
        raise ValueError("graph interval exceeds the labelled graph space")
    return data


def shard_masks(start: int, count: int, shard: int, shards: int) -> list[int]:
    if shards < 1 or not 0 <= shard < shards:
        raise ValueError("invalid shard")
    return [start + index for index in range(count) if index % shards == shard]


def run(config_file: Path, shard: int, output: Path) -> None:
    cfg = parse_config(config_file)
    masks = shard_masks(cfg["start_mask"], cfg["graph_count"], shard, cfg["shard_count"])
    output.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    sat_count = unsat_count = 0
    results = output / "results.jsonl"

    with tempfile.TemporaryDirectory(prefix="graph-sat-") as temporary, results.open("w", encoding="utf-8") as out:
        tmp = Path(temporary)
        for index, mask in enumerate(masks, 1):
            edges = graph_edges(cfg["vertices"], mask)
            t0 = time.monotonic()
            sat, colouring = solve_with_minisat(cfg["vertices"], edges, tmp)
            independent = brute_three_colours(cfg["vertices"], edges)
            if sat != independent:
                raise RuntimeError(f"independent checker disagrees for mask {mask}")
            if sat:
                sat_count += 1
            else:
                unsat_count += 1
            record = {
                "mask": mask,
                "edges": edges,
                "sat": sat,
                "colouring": colouring,
                "elapsed_ms": round((time.monotonic() - t0) * 1000, 3),
                "independently_checked": True,
            }
            out.write(json.dumps(record, sort_keys=True) + "\n")
            if index % 100 == 0 or index == len(masks):
                print(f"shard {shard}: {index}/{len(masks)} checked ({sat_count} SAT, {unsat_count} UNSAT)", flush=True)

    try:
        banner = subprocess.run(["minisat", "-h"], capture_output=True, text=True, timeout=5, check=False)
        solver_banner = (banner.stdout + "\n" + banner.stderr).strip().splitlines()[:4]
    except (OSError, subprocess.TimeoutExpired):
        solver_banner = ["minisat (banner unavailable)"]

    summary = {
        "experiment": cfg["experiment"],
        "purpose": "infrastructure-smoke-test-not-resilience",
        "vertices": cfg["vertices"],
        "start_mask": cfg["start_mask"],
        "graph_count": cfg["graph_count"],
        "shard": shard,
        "shard_count": cfg["shard_count"],
        "processed": len(masks),
        "sat": sat_count,
        "unsat": unsat_count,
        "elapsed_seconds": round(time.monotonic() - start, 3),
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": hashlib.sha256(config_file.read_bytes()).hexdigest(),
        "git_sha": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "solver_banner": solver_banner,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--shard", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.config, args.shard, args.output)


if __name__ == "__main__":
    main()
