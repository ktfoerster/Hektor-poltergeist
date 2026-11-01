"""Semantic and corruption tests for the rank-free lasso learner."""
import copy
import itertools
import json
from pathlib import Path
import tempfile
import unittest

from lasso_witness import (audit, base_clauses, branch_clause, checked_clause,
                           geometry, selector_rows, sha, trace)
from lasso_search import CapturedPolicy, run, snapshot
from sat_search import BooleanEncoding, partition


def tiny_policies():
    rows = selector_rows(4, 3)
    base = {k: choices[0][0] for k, choices in rows.items()}
    keys = [(1, 5, -1, 0), (1, 5, 0, 0), (0, 2, 1, 0)]
    for picks in itertools.product(*(range(len(rows[k])) for k in keys)):
        yield {**base, **{k: rows[k][idx][0] for k, idx in zip(keys, picks)}}


def literal_walk(policy, source, mask=41):
    """Third implementation, specialized to the four-vertex path 0-1-2-3."""
    adj = [2, 5, 10, 4]
    assert mask == 41
    u, previous, bit = source, -1, 0
    seen = set()
    for _ in range(100):
        if u == 3:
            return True
        state = (u, previous, bit)
        if state in seen:
            return False
        seen.add(state)
        choice = policy[(u, adj[u], previous, bit)]
        previous, u, bit = u, choice // 2, choice % 2
    raise AssertionError("not a finite-state walk")


class LassoSemanticTests(unittest.TestCase):
    def test_selector_numbering_and_exact_branch_partition(self):
        for n, target in [(4, 3), (7, 0), (7, 3)]:
            e = BooleanEncoding(n, target)
            try:
                rows = selector_rows(n, target)
                self.assertEqual(rows, e.rows)
                left = branch_clause(n, target, 0, rows)
                right = branch_clause(n, target, 1, rows)
                self.assertEqual((len(left), len(right)), (2, 2))
                self.assertFalse(set(left) & set(right))
                self.assertEqual(len(left + right), 4)
                for ids in (left, right):
                    matching = [(k, a) for k, values in rows.items()
                                for a, v in values if v in ids]
                    self.assertEqual(len(matching), 2)
                    self.assertEqual({a % 2 for _, a in matching}, {0, 1})
                    self.assertEqual(len({a // 2 for _, a in matching}), 1)
                enc = BooleanEncoding(n, target)
                try:
                    partition(enc, 0)
                    self.assertEqual(enc.clause_count, e.clause_count + 1)
                    self.assertEqual(list(base_clauses(n, target, 0, rows))[-1], left)
                finally:
                    enc.delete()
            finally:
                e.delete()

    def test_32_policy_literal_vs_rank_and_clause_soundness(self):
        rows = selector_rows(4, 3)
        policies = list(tiny_policies())
        self.assertEqual(len(policies), 32)
        reference = BooleanEncoding(4, 3)
        reference.add(41)
        seen_success = seen_failure = False
        try:
            for policy in policies:
                expected = all(literal_walk(policy, s) for s in (0, 1, 2))
                assumptions = [reference.selector(key, value)
                               for key, value in policy.items()]
                self.assertEqual(reference.solver.solve(assumptions=assumptions),
                                 expected, "rank encoding differs from literal walks")
                seen_success |= expected
                seen_failure |= not expected
                for source in (0, 1, 2):
                    witness = trace(policy, 4, 3, 41, source)
                    self.assertEqual(witness is None, literal_walk(policy, source))
                    if witness is None:
                        continue
                    clause = checked_clause(witness, 4, 3, rows)
                    selected = {dict(rows[key])[value] for key, value in policy.items()}
                    self.assertTrue(all(-lit in selected for lit in clause))
                    for other in policies:
                        choice = {dict(rows[key])[a] for key, a in other.items()}
                        if all(-lit in choice for lit in clause):
                            self.assertFalse(literal_walk(other, source),
                                             "learned clause would block a valid walk")
        finally:
            reference.delete()
        self.assertTrue(seen_success)
        self.assertTrue(seen_failure)

    def test_successful_source_revisit_and_unreachable_cycle(self):
        p = next(tiny_policies())
        # First execution revisits the physical source with a different bit.
        p[(0, 2, -1, 0)] = 2
        p[(1, 5, 0, 0)] = 1
        p[(0, 2, 1, 1)] = 3
        p[(1, 5, 0, 1)] = 4
        self.assertTrue(literal_walk(p, 0))
        self.assertIsNone(trace(p, 4, 3, 41, 0))
        # Make an arrival cycle that is unreachable from source injection.
        p[(0, 2, -1, 0)] = 3
        p[(1, 5, 0, 1)] = 4
        p[(1, 5, 0, 0)] = 0
        p[(0, 2, 1, 0)] = 2
        self.assertTrue(literal_walk(p, 0))
        self.assertIsNone(trace(p, 4, 3, 41, 0))

    def test_disconnected_and_shared_injection(self):
        p = next(tiny_policies())
        self.assertIsNone(trace(p, 4, 3, 0, 0))
        self.assertIsNone(trace(p, 4, 3, 41, 3))
        a, _ = geometry(4, 3, 41)
        b, _ = geometry(4, 3, 57)  # remote edge 1-3 differs
        self.assertEqual(a[0], b[0])
        self.assertEqual((0, a[0], -1, 0), (0, b[0], -1, 0))
        self.assertEqual(dict(selector_rows(4, 3)[(0, a[0], -1, 0)]),
                         dict(selector_rows(4, 3)[(0, b[0], -1, 0)]))

    def test_corrupted_witnesses_rejected(self):
        witness = trace(next(tiny_policies()), 4, 3, 41, 0)
        self.assertIsNotNone(witness)
        checked_clause(witness, 4, 3)
        modified = []
        for key, value in [("source", 3), ("mask", 0), ("schema", True),
                           ("cycle_start", 0), ("cycle_start", 99)]:
            item = copy.deepcopy(witness)
            item[key] = value
            modified.append(item)
        for operation in [
                lambda w: w["steps"].pop(0),
                lambda w: w["steps"].pop(),
                lambda w: w["steps"][0].__setitem__(4, 6),
                lambda w: w["steps"][0].__setitem__(1, 123)]:
            item = copy.deepcopy(witness)
            operation(item)
            modified.append(item)
        for item in modified:
            with self.assertRaises(ValueError):
                checked_clause(item, 4, 3)

    def test_rebuild_entire_cnf_corruption_and_resume(self):
        rows = selector_rows(4, 3)
        witness = trace(next(tiny_policies()), 4, 3, 41, 0)
        clause = checked_clause(witness, 4, 3, rows)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "bundle"
            out.mkdir()
            enc = CapturedPolicy(4, 3, out / "clauses.body")
            try:
                self.assertEqual(rows, enc.rows)
                (out / "selectors.json").write_text(json.dumps(
                    [[*k, options] for k, options in rows.items()]) + "\n")
                (out / "masks.json").write_text("[41]\n")
                enc.add_clause(clause)
                (out / "witnesses.jsonl").write_text(json.dumps(
                    {"witness": witness, "clause": clause}) + "\n")
                snapshot(out, enc, [41], 3, -1, 1, {"status": "UNKNOWN"}, {})
            finally:
                enc.close()
            self.assertEqual(audit(out)["witnesses"], 1)
            # Rehashing both the manifest and the corrupted clause cannot
            # bypass the independently reconstructed translation.
            path = out / "witnesses.jsonl"
            item = json.loads(path.read_text())
            item["clause"] = [-1]
            path.write_text(json.dumps(item) + "\n")
            meta = json.loads((out / "manifest.json").read_text())
            meta["sha256"]["witnesses.jsonl"] = sha(path)
            (out / "manifest.json").write_text(json.dumps(meta))
            with self.assertRaises(ValueError):
                audit(out)

    def test_bounded_live_solver_and_independent_bundle_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "first"
            result = run(out, 4, 3, -1, [41], 2)
            self.assertIn(result["status"], {
                "UNKNOWN", "UNSAT_UNCERTIFIED", "FINITE_SUITE_SAT_UNVERIFIED"})
            self.assertEqual(audit(out)["status"], "CHECKED")
            next_out = Path(tmp) / "second"
            run(next_out, 4, 3, -1, [41], 2, resume=out)
            self.assertEqual(audit(next_out)["status"], "CHECKED")


if __name__ == "__main__":
    unittest.main()
