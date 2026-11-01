"""Independent, solver-free certificates for source-reachable failing walks.

No imports from the synthesizer.  The entire injection/prefix/cycle is checked:
blocking an unreachable arrival cycle alone would be unsound.
"""
import hashlib
import json
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def geometry(n, target, mask):
    if type(n) is not int or not 2 <= n <= 7:
        raise ValueError("n")
    if type(target) is not int or not 0 <= target < n:
        raise ValueError("target")
    edges = [(u, v) for u in range(n) for v in range(u + 1, n)
             if n != 7 or (u, v) not in ((3, 4), (5, 6))]
    if type(mask) is not int or not 0 <= mask < (1 << len(edges)):
        raise ValueError("residual mask")
    live = [0] * n
    for i, (u, v) in enumerate(edges):
        if mask & (1 << i):
            live[u] |= 1 << v
            live[v] |= 1 << u
    reachable = {target}
    queue = [target]
    while queue:
        u = queue.pop()
        for v in range(n):
            if live[u] & (1 << v) and v not in reachable:
                reachable.add(v)
                queue.append(v)
    return live, reachable


def selector_rows(n, target):
    """Reconstruct the reference's numbered global rows without importing it."""
    edge_count = n * (n - 1) // 2 - (2 if n == 7 else 0)
    host, _ = geometry(n, target, (1 << edge_count) - 1)
    result = {}
    number = 0
    for u in range(n):
        if u == target:
            continue
        for local in range(1, 1 << n):
            if local & ~host[u]:
                continue
            ports = [v for v in range(n) if local & (1 << v)]
            arrivals = [(-1, 0)] + [(p, bit) for p in ports for bit in (0, 1)]
            actions = ([2 * target] if target in ports else
                       [2 * v + bit for v in ports for bit in (0, 1)])
            for incoming, bit in arrivals:
                choices = []
                for action in actions:
                    number += 1
                    choices.append((action, number))
                result[(u, local, incoming, bit)] = choices
    return result


def branch_clause(n, target, branch, rows):
    if branch == -1:
        return None
    if branch not in (0, 1) or type(branch) is not int:
        raise ValueError("branch")
    full = (1 << (n * (n - 1) // 2 - (2 if n == 7 else 0))) - 1
    host, _ = geometry(n, target, full)
    for u in range(n):
        if u == target:
            continue
        neighbors = [v for v in range(n) if v != target and host[u] & (1 << v)]
        if len(neighbors) >= 2:
            neighbors = neighbors[:2]
            key = (u, (1 << neighbors[0]) | (1 << neighbors[1]), -1, 0)
            return [dict(rows[key])[2 * neighbors[branch] + bit] for bit in (0, 1)]
    raise ValueError("no branchable observation")


def base_clauses(n, target, branch, rows):
    for choices in rows.values():
        ids = [var for _, var in choices]
        yield ids
        for i, left in enumerate(ids):
            for right in ids[i + 1:]:
                yield [-left, -right]
    if branch != -1:
        yield branch_clause(n, target, branch, rows)


def trace(policy, n, target, mask, source):
    """Find the first reachable repeating arrival, or return None on delivery."""
    live, reachable = geometry(n, target, mask)
    if type(source) is not int or not 0 <= source < n:
        raise ValueError("source")
    if source == target or source not in reachable:
        return None
    u, incoming, bit = source, -1, 0
    seen = {}
    steps = []
    while u != target:
        state = (u, incoming, bit)
        if incoming >= 0:
            if state in seen:
                return dict(schema=1, mask=mask, source=source,
                            cycle_start=seen[state], steps=steps)
            seen[state] = len(steps)
        key = (u, live[u], incoming, bit)
        action = policy[key]
        if (type(action) is not int or action < 0 or action >= 2 * n or
                not live[u] & (1 << (action // 2)) or
                (live[u] & (1 << target) and action != 2 * target)):
            raise ValueError("illegal or unnormalized policy")
        steps.append([*key, action])
        incoming, u, bit = u, action // 2, action % 2
    return None


def checked_clause(witness, n, target, rows=None):
    """Reconstruct a necessary blocking clause; reject a detached/partial cycle."""
    if not isinstance(witness, dict) or set(witness) != {
            "schema", "mask", "source", "cycle_start", "steps"}:
        raise ValueError("witness schema")
    if type(witness["schema"]) is not int or witness["schema"] != 1:
        raise ValueError("schema version")
    live, reachable = geometry(n, target, witness["mask"])
    source = witness["source"]
    if type(source) is not int or source == target or source not in reachable:
        raise ValueError("vacuous source")
    steps = witness["steps"]
    if (not isinstance(steps, list) or
            not 2 <= len(steps) <= 1 + 2 * sum(x.bit_count() for x in live)):
        raise ValueError("step count")
    cycle_start = witness["cycle_start"]
    if (type(cycle_start) is not int or
            not 1 <= cycle_start < len(steps)):
        raise ValueError("cycle start")
    if rows is None:
        rows = selector_rows(n, target)
    current, incoming, bit = source, -1, 0
    visited, chosen, ids = {}, {}, set()
    for i, step in enumerate(steps):
        if (not isinstance(step, list) or len(step) != 5 or
                any(type(v) is not int for v in step)):
            raise ValueError("malformed step")
        if current == target:
            raise ValueError("already delivered")
        state = (current, incoming, bit)
        if incoming >= 0:
            if state in visited:
                raise ValueError("not the first repeated arrival")
            visited[state] = i
        key = (current, live[current], incoming, bit)
        if tuple(step[:4]) != key:
            raise ValueError("wrong local observation / omitted prefix")
        action = step[4]
        choices = dict(rows.get(key, []))
        if action not in choices:
            raise ValueError("illegal action")
        if key in chosen and chosen[key] != action:
            raise ValueError("nondeterministic policy row")
        chosen[key] = action
        ids.add(choices[action])
        incoming, current, bit = current, action // 2, action % 2
    if current == target or visited.get((current, incoming, bit)) != cycle_start:
        raise ValueError("cycle does not close at its claimed arrival state")
    return sorted(-var for var in ids)


def audit(directory):
    """Recheck hashes, masks, numbering and EACH CNF clause independently."""
    root = Path(directory)
    if (root / "current").is_symlink():
        root = (root / "current").resolve(strict=True)
    meta = json.loads((root / "manifest.json").read_text())
    if meta.get("encoding") != "source-reachable-lasso-v1" or meta.get("schema") != 1:
        raise ValueError("bundle encoding")
    n, target, branch = meta["n"], meta["target"], meta["branch"]
    geometry(n, target, 0)
    if branch not in (-1, 0, 1) or type(branch) is not int:
        raise ValueError("branch")
    digests = meta.get("sha256")
    required = {"formula.cnf", "selectors.json", "masks.json", "witnesses.jsonl"}
    for optional in ("masks.txt", "cpp-batches.jsonl", "last-policy.tsv",
                     "exhaustive-verifier.log"):
        if (root / optional).exists():
            required.add(optional)
    if not isinstance(digests, dict) or not required <= digests.keys():
        raise ValueError("incomplete bundle hashes")
    for filename, digest in digests.items():
        if Path(filename).name != filename or sha(root / filename) != digest:
            raise ValueError("bundle hash mismatch: " + filename)
    expected_rows = selector_rows(n, target)
    expected_map = [[*key, [[action, var] for action, var in choices]]
                    for key, choices in expected_rows.items()]
    if json.loads((root / "selectors.json").read_text()) != expected_map:
        raise ValueError("selector map mismatch")
    masks = json.loads((root / "masks.json").read_text())
    if (not isinstance(masks, list) or not masks or
            any(type(x) is not int for x in masks) or masks != sorted(set(masks))):
        raise ValueError("invalid frozen suite")
    for mask in masks:
        geometry(n, target, mask)
    allowed = set(masks)
    if type(meta.get("masks")) is not int or meta["masks"] != len(masks):
        raise ValueError("mask accounting mismatch")
    variables = sum(map(len, expected_rows.values()))
    for key in ("variables", "clauses", "witnesses"):
        if type(meta.get(key)) is not int or meta[key] < 0:
            raise ValueError("invalid CNF accounting")
    if meta["variables"] != variables:
        raise ValueError("CNF accounting mismatch")
    # Independently reconstruct and compare one clause at a time. No growing
    # list of all expected clauses, and no trust in the supplied clause count.
    h = hashlib.sha256()
    clause_count = witness_count = 0
    with (root / "formula.cnf").open("rb") as f:
        if f.readline() != f"p cnf {variables} {meta['clauses']}\n".encode():
            raise ValueError("DIMACS header")

        def compare(clause):
            nonlocal clause_count
            raw = (" ".join(map(str, clause)) + " 0\n").encode()
            if f.readline() != raw:
                raise ValueError("DIMACS clause/translation mismatch")
            h.update(raw)
            clause_count += 1

        for clause in base_clauses(n, target, branch, expected_rows):
            compare(clause)
        with (root / "witnesses.jsonl").open() as records:
            for line in records:
                item = json.loads(line)
                if (set(item) != {"witness", "clause"} or
                        item["witness"]["mask"] not in allowed):
                    raise ValueError("witness not in frozen suite")
                clause = checked_clause(item["witness"], n, target, expected_rows)
                if item["clause"] != clause:
                    raise ValueError("incorrect witness clause")
                compare(clause)
                witness_count += 1
        if f.read(1):
            raise ValueError("extra DIMACS data")
    if meta["clauses"] != clause_count or meta["witnesses"] != witness_count:
        raise ValueError("CNF accounting mismatch")
    if h.hexdigest() != meta["clause_body_sha256"]:
        raise ValueError("CNF fingerprint mismatch")
    return {"status": "CHECKED", "clauses": clause_count,
            "witnesses": witness_count, "variables": variables,
            "cnf_sha256": sha(root / "formula.cnf")}
