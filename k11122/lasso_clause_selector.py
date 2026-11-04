"""Exact logical subsumption and sound source-balanced clause selection.

Only returns subsets of independently audited necessary negative-selector
lasso clauses. No new routing restrictions, policy assumptions, or proof
verdicts are introduced.
"""


def _minimal(entries):
    order = sorted(range(len(entries)),
                   key=lambda i: (len(entries[i]["clause"]), entries[i]["clause"], i))
    trie, keep, dominated = {}, set(), {}

    def find_subset(node, clause, pos):
        if None in node:
            return node[None]
        for j in range(pos, len(clause)):
            nxt = node.get(clause[j])
            if nxt is not None:
                match = find_subset(nxt, clause, j + 1)
                if match is not None:
                    return match
        return None

    for i in order:
        clause = entries[i]["clause"]
        if tuple(clause) != tuple(sorted(set(clause))):
            raise ValueError("noncanonical or duplicate clause literals")
        strong = find_subset(trie, clause, 0)
        if strong is not None:
            dominated[i] = strong
            continue
        keep.add(i)
        node = trie
        for v in clause:
            node = node.setdefault(v, {})
        node[None] = i
    if len(keep) + len(dominated) != len(entries):
        raise RuntimeError("subsumption accounting")
    for weaker, stronger in dominated.items():
        if stronger not in keep or not set(entries[stronger]["clause"]).issubset(
                entries[weaker]["clause"]):
            raise RuntimeError("invalid subsumption certificate")
    return keep, dominated


def select_clauses(entries, mode, source_count=2):
    """Return selected indices and exact dominator indices.

    lossless: remove only clauses logically implied by shorter clauses.
    shortest-half: at most half, sorted shortest-first.
    balanced-half: half, equal source quotas, first cover distinct failure
      masks per source, then fill with shorter clauses.
    """
    if mode not in ("lossless", "shortest-half", "balanced-half"):
        raise ValueError("invalid selective clause mode")
    if (type(source_count) is not int or source_count < 1 or
            not entries or any(not isinstance(x, dict) or
              type(x.get("source")) is not int or
              not 0 <= x["source"] < source_count or
              type(x.get("mask")) is not int or
              not isinstance(x.get("clause"), (tuple, list)) or
              not x["clause"] for x in entries)):
        raise ValueError("invalid indexed source witnesses")
    minimal, dominated = _minimal(entries)
    if mode == "lossless":
        chosen = set(minimal)
    else:
        cap = min(len(minimal), (len(entries) + 1) // 2)
        if mode == "shortest-half":
            chosen = set(sorted(minimal, key=lambda i: (
                len(entries[i]["clause"]), entries[i]["clause"], i))[:cap])
        else:
            buckets = []
            for origin in range(source_count):
                ranked = sorted(
                    (i for i in minimal if entries[i]["source"] == origin),
                    key=lambda i: (len(entries[i]["clause"]), entries[i]["mask"],
                                   entries[i]["clause"], i))
                observed, unique, rest = set(), [], []
                for i in ranked:
                    if entries[i]["mask"] not in observed:
                        unique.append(i)
                        observed.add(entries[i]["mask"])
                    else:
                        rest.append(i)
                buckets.append(unique + rest)
            chosen = set()
            for bucket in buckets:
                chosen.update(bucket[:cap // source_count])
            if len(chosen) < cap:
                extra = sorted((i for i in minimal if i not in chosen),
                               key=lambda i: (len(entries[i]["clause"]),
                                              entries[i]["source"], entries[i]["mask"],
                                              entries[i]["clause"], i))
                chosen.update(extra[:cap-len(chosen)])
        if len(chosen) != cap or not chosen.issubset(minimal):
            raise RuntimeError("invalid selective witness cap")
    if mode == "lossless" and any(i not in chosen for i in dominated.values()):
        raise RuntimeError("dominating clause removed from lossless CNF")
    return chosen, dominated
