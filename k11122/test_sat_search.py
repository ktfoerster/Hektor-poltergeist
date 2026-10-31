import itertools
import json
import pathlib
import subprocess
import tempfile
import unittest

import z3

from sat_search import (BooleanEncoding, adjacency, graph, partition, vertices,
                        write_policy)
from search import Encoding


def assumptions_for(values):
    return [var if value else -var for var, value in values]


def literal_policy_succeeds(n, target, rows):
    edges = graph(n)
    for mask in range(1 << len(edges)):
        adj = adjacency(n, edges, mask)
        connected = {target}
        for _ in range(n):
            connected |= {v for u in list(connected) for v in vertices(adj[u], n)}
        for source in connected - {target}:
            u, incoming, bit = source, -1, 0
            seen = set()
            while u != target and (u, incoming, bit) not in seen:
                seen.add((u, incoming, bit))
                action = rows[(u, adj[u], incoming, bit)]
                u, incoming, bit = action // 2, u, action % 2
            if u != target:
                return False
    return True


def literal_mask_succeeds(n, target, rows, mask):
    adj = adjacency(n, graph(n), mask)
    connected = {target}
    for _ in range(n):
        connected |= {v for u in list(connected) for v in vertices(adj[u], n)}
    for source in connected - {target}:
        u, incoming, bit = source, -1, 0
        seen = set()
        while u != target and (u, incoming, bit) not in seen:
            seen.add((u, incoming, bit))
            action = rows[(u, adj[u], incoming, bit)]
            u, incoming, bit = action // 2, u, action % 2
        if u != target:
            return False
    return True


class BooleanPrimitiveTests(unittest.TestCase):
    def test_guarded_comparator_boundaries(self):
        encoding = BooleanEncoding(2, 0)
        lesser = [encoding.new_var() for _ in range(3)]
        greater = [encoding.new_var() for _ in range(3)]
        guard = encoding.new_var()
        encoding.add_guarded_less(lesser, greater, guard)
        for left in range(8):
            for right in range(8):
                pins = [(guard, True)]
                pins += [(var, bool(left >> bit & 1)) for bit, var in enumerate(lesser)]
                pins += [(var, bool(right >> bit & 1)) for bit, var in enumerate(greater)]
                self.assertEqual(encoding.solver.solve(assumptions=assumptions_for(pins)), left < right)
                pins[0] = (guard, False)
                self.assertTrue(encoding.solver.solve(assumptions=assumptions_for(pins)))
        encoding.delete()

    def test_exact_one_selector(self):
        encoding = BooleanEncoding(3, 0)
        key = (1, 4, -1, 0)
        choices = encoding.rows[key]
        self.assertEqual(len(choices), 2)
        variables = [var for _, var in choices]
        self.assertFalse(encoding.solver.solve(assumptions=[-var for var in variables]))
        self.assertFalse(encoding.solver.solve(assumptions=variables))
        for selected in variables:
            self.assertTrue(encoding.solver.solve(assumptions=[selected]))
        encoding.delete()

    def test_persistent_worker_receives_new_clauses(self):
        encoding = BooleanEncoding(2, 0)
        key = (1, 1, -1, 0)
        selected = encoding.selector(key, 0)
        with tempfile.TemporaryDirectory() as directory:
            first, first_payload = encoding.solve_for(
                5, pathlib.Path(directory) / "first.json", 100)
            self.assertTrue(first)
            encoding.add_clause((-selected,))
            second, second_payload = encoding.solve_for(
                5, pathlib.Path(directory) / "second.json", 100)
            self.assertFalse(second)
            self.assertEqual(first_payload["worker_pid"], second_payload["worker_pid"])
            self.assertEqual(second_payload["clauses_added"], 1)
        encoding.delete()


class DifferentialTests(unittest.TestCase):
    def test_miner_agrees_with_unchanged_verifier_and_literal_walks(self):
        n, target = 4, 0
        encoding = BooleanEncoding(n, target)
        rows = {}
        for key in encoding.rows:
            live = key[1]
            neighbor = target if live >> target & 1 else vertices(live, n)[0]
            rows[key] = 2 * neighbor
        encoding.delete()
        source = pathlib.Path(__file__).parent
        with tempfile.TemporaryDirectory() as directory:
            directory = pathlib.Path(directory)
            policy = directory / "policy.tsv"
            write_policy(policy, n, target, rows)
            results = []
            for name in ("verify", "counterexample_miner"):
                binary = directory / name
                subprocess.run(
                    ["g++", "-O2", "-std=c++17", str(source / f"{name}.cpp"),
                     "-o", str(binary)], check=True)
                run = subprocess.run([str(binary), str(policy)], check=True,
                                     capture_output=True, text=True)
                results.append(json.loads(run.stdout))
            verifier, miner = results
            self.assertEqual(miner["masks"], verifier["masks"])
            self.assertEqual(miner["obligations"], verifier["obligations"])
            self.assertEqual(miner["failures"], verifier["failures"])
            self.assertGreater(miner["failures"], 0)
            self.assertTrue(miner["counterexamples"])
            for mask in miner["counterexamples"]:
                self.assertFalse(literal_mask_succeeds(n, target, rows, mask))

    def test_all_triangle_bit_policies_against_smt_and_walks(self):
        n, target = 3, 0
        smt = Encoding(n, target)
        cnf = BooleanEncoding(n, target)
        for mask in range(1 << len(graph(n))):
            smt.add(mask)
            cnf.add(mask)
        free = [key for key in smt.rows if not key[1] & 1]
        self.assertEqual(len(free), 6)
        for bits in itertools.product(range(2), repeat=len(free)):
            rows = {}
            for key in smt.rows:
                if key[1] & 1:
                    rows[key] = 0
                else:
                    emitted = bits[free.index(key)]
                    rows[key] = 2 * vertices(key[1], n)[0] + emitted
            expected = literal_policy_succeeds(n, target, rows)
            smt.s.push()
            for key, action in rows.items():
                smt.s.add(smt.rows[key] == action)
            smt_result = smt.s.check() == z3.sat
            smt.s.pop()
            pins = [cnf.selector(key, action) for key, action in rows.items()]
            cnf_result = cnf.solver.solve(assumptions=pins)
            self.assertEqual((cnf_result, smt_result), (expected, expected))
        cnf.delete()

    def test_shared_injection_disconnected_and_both_orbits(self):
        encoding = BooleanEncoding(3, 0)
        variable = encoding.selector((1, 4, -1, 0), 4)
        encoding.add(0)
        encoding.add(4)
        self.assertEqual(variable, encoding.selector((1, 4, -1, 0), 4))
        self.assertTrue(encoding.solver.solve())
        encoding.delete()
        for target in (0, 3):
            encoding = BooleanEncoding(7, target)
            encoding.add((1 << 19) - 1)
            encoding.add(((1 << 19) - 1) ^ 1)
            self.assertTrue(encoding.solver.solve())
            encoding.delete()

    def test_transient_source_revisit_and_unreachable_loop(self):
        encoding = BooleanEncoding(4, 0)
        encoding.add(57)  # 01,12,13,23
        assignments = {
            (3, 6, -1, 0): 2,
            (3, 6, 2, 0): 5,
            (2, 10, 3, 1): 2,
            (2, 10, 3, 0): 7,
            (3, 6, 2, 1): 4,
            (2, 10, -1, 0): 6,
        }
        pins = [encoding.selector(key, action) for key, action in assignments.items()]
        self.assertTrue(encoding.solver.solve(assumptions=pins))
        pins[-1] = encoding.selector((2, 10, -1, 0), 7)
        self.assertFalse(encoding.solver.solve(assumptions=pins))
        encoding.delete()

    def test_partition_preserves_both_emitted_bits(self):
        for target in (0, 3):
            for branch in (0, 1):
                encoding = BooleanEncoding(7, target)
                spec = partition(encoding, branch)
                row = tuple(spec["row"])
                for neighbor_index, neighbor in enumerate(spec["neighbors"]):
                    for bit in (0, 1):
                        result = encoding.solver.solve(
                            assumptions=[encoding.selector(row, 2 * neighbor + bit)])
                        self.assertEqual(result, neighbor_index == branch)
                encoding.delete()


if __name__ == "__main__":
    unittest.main()
