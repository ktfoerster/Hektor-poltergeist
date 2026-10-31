import itertools
import pathlib
import random
import tempfile
import unittest
from proof_cnf import rup, check, solve
from rup_watch import WatchedRUP


class WatchedTests(unittest.TestCase):
    def test_exhaustive_two_variables(self):
        clauses = [set(v for v in choice if v) for choice in
                   itertools.product([0, 1, -1], [0, 2, -2])]
        for bits in range(1 << len(clauses)):
            formula = [c for i, c in enumerate(clauses) if bits >> i & 1]
            watched = WatchedRUP(formula)
            for candidate in clauses + [{1, -1}]:
                self.assertEqual(watched.rup(candidate), rup(formula, candidate))

    def test_seeded_incremental_differential(self):
        rng = random.Random(20261031)
        for _ in range(100):
            def clause():
                return set(rng.choice([-1, 1]) * rng.randint(1, 12)
                           for _ in range(rng.randint(1, 5)))
            formula = [clause() for _ in range(30)]
            watched = WatchedRUP(formula)
            for _ in range(100):
                candidate = clause()
                expected = rup(formula, candidate)
                self.assertEqual(watched.rup(candidate), expected)
                if expected:
                    formula.append(candidate)
                    watched.add(candidate)

    def test_pigeonhole_proof_both_engines(self):
        clauses = []
        variable = lambda p, h: 1 + 4*p + h
        for p in range(5):
            clauses.append([variable(p, h) for h in range(4)])
        for p, q in itertools.combinations(range(5), 2):
            for h in range(4):
                clauses.append([-variable(p,h), -variable(q,h)])
        with tempfile.TemporaryDirectory() as temp:
            cnf, proof = pathlib.Path(temp)/'formula.cnf', pathlib.Path(temp)/'proof.drup'
            cnf.write_text(f'p cnf 20 {len(clauses)}\n' + ''.join(
                ' '.join(map(str, c))+' 0\n' for c in clauses))
            self.assertEqual(solve(cnf, proof), 'UNSAT_UNCERTIFIED')
            for engine in ['reference', 'watched']:
                self.assertEqual(check(cnf, proof, engine)['status'], 'CNF_UNSAT_RUP_VERIFIED')
            proof.write_text('d malformed\n0\n')
            for engine in ['reference', 'watched']:
                with self.assertRaises(ValueError):
                    check(cnf, proof, engine)


if __name__ == '__main__':
    unittest.main()
