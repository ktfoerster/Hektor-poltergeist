import json
import pathlib
import tempfile
import unittest
from proof_cnf import export, check, solve, read_cnf
from sat_search import BooleanEncoding


class ProofTests(unittest.TestCase):
    def test_export_matches_encoder(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            a = export(root / 'a', 0, [7, 3, 7], n=3)
            b = export(root / 'b', 0, [3, 7], n=3)
            self.assertEqual(a, b)
            enc = BooleanEncoding(3, 0)
            try:
                for mask in [3, 7]:
                    enc.add(mask)
                self.assertEqual(a['clause_body_sha256'], enc.fingerprint.hexdigest())
                self.assertEqual(a['variables'], enc.top)
                self.assertEqual(a['clauses'], enc.clause_count)
                self.assertEqual(solve(root / 'a/formula.cnf', root / 'a/proof.drup'), 'SAT_FINITE_CNF')
            finally:
                enc.delete()

    def test_unsat_proof_and_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            cnf, proof = root / 'formula.cnf', root / 'proof.drup'
            cnf.write_text('p cnf 2 4\n1 2 0\n1 -2 0\n-1 2 0\n-1 -2 0\n')
            self.assertEqual(solve(cnf, proof), 'UNSAT_UNCERTIFIED')
            self.assertEqual(check(cnf, proof)['status'], 'CNF_UNSAT_RUP_VERIFIED')
            proof.write_text('0\n')
            with self.assertRaises(ValueError):
                check(cnf, proof)
            proof.write_text('1 0\n')
            with self.assertRaises(ValueError):
                check(cnf, proof)
            cnf.write_text('p cnf 1 1\n1 0\n')
            proof.write_text('0\n')
            with self.assertRaises(ValueError):
                check(cnf, proof)

    def test_invalid_dimacs(self):
        with tempfile.TemporaryDirectory() as temp:
            path = pathlib.Path(temp) / 'bad.cnf'
            for text in ['p cnf 1 1\n2 0\n', 'p cnf 1 2\n1 0\n', 'p cnf 1 1\n1\n']:
                path.write_text(text)
                with self.assertRaises(ValueError):
                    read_cnf(path)


if __name__ == '__main__':
    unittest.main()
