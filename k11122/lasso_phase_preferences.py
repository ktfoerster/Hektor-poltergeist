"""Generate complete, legal policy tables used ONLY as SAT phase hints.

Generation never adds a solver clause, changes packet state, or claims a
resilient policy. Every row is selected from the global legal selector table.
The distinguished physical-first-hop row is made compatible with the
requested exhaustive branch, but its two emitted-bit choices remain free
in SAT: it is a preference, NOT an assumption.
"""
import argparse
import hashlib
from pathlib import Path

from lasso_witness import selector_rows
from sat_search import graph, adjacency, vertices, write_policy


def distinguished_row(n, target, branch):
    if type(branch) is not int or branch not in (0, 1):
        raise ValueError("first-hop branch must be 0 or 1")
    edges = graph(n)
    host = adjacency(n, edges, (1 << len(edges)) - 1)
    sources = [u for u in range(n) if u != target and
               len(vertices(host[u] & ~(1 << target), n)) >= 2]
    if not sources:
        raise ValueError("graph has no two-way branch source")
    u = sources[0]
    neighbors = vertices(host[u] & ~(1 << target), n)[:2]
    return (u, (1 << neighbors[0]) | (1 << neighbors[1]), -1, 0), neighbors[branch]


def generate(n, target, branch, variant, salt=0):
    if type(salt) is not int or not 0 <= salt <= 2**31 - 1:
        raise ValueError("phase salt must be a bounded nonnegative integer")
    if variant not in ("first", "last", "hash"):
        raise ValueError("unsupported phase generation variant")
    rows = selector_rows(n, target)
    key, hop = distinguished_row(n, target, branch)
    if key not in rows:
        raise RuntimeError("branch selector row absent from global policy domain")
    policy = {}
    for row, choices in rows.items():
        choices = [action for action, _ in choices]
        if row == key:
            choices = [action for action in choices if action // 2 == hop]
        if not choices:
            raise RuntimeError("empty phase-preference choice set")
        if variant == "first":
            policy[row] = choices[0]
        elif variant == "last":
            policy[row] = choices[-1]
        else:
            digest = hashlib.sha256(f"k11122-phases-v1:{salt}:{row}".encode()).digest()
            policy[row] = choices[int.from_bytes(digest[:8], "big") % len(choices)]
    if set(policy) != set(rows):
        raise RuntimeError("incomplete phase policy")
    return policy


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", type=int, choices=(0, 3), required=True)
    p.add_argument("--branch", type=int, choices=(0, 1), required=True)
    p.add_argument("--variant", choices=("first", "last", "hash"), required=True)
    p.add_argument("--salt", type=int, default=0)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error("output must not exist, to preserve exact experiment inputs")
    policy = generate(7, a.target, a.branch, a.variant, a.salt)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    write_policy(a.output, 7, a.target, policy)


if __name__ == "__main__":
    main()
