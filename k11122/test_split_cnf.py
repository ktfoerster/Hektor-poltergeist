import json
import pathlib
import tempfile
import unittest
from proof_cnf import export, solve, iter_cnf
from split_cnf import plan, child, decode
from pysat.solvers import Solver

class SplitTests(unittest.TestCase):
    def test_coverage_models_and_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            base=pathlib.Path(temp);root=base/'parent'
            export(root,0,[0,1,63],n=4)
            p=plan(root)
            literals=[c['literal'] for c in p['cases']]
            self.assertEqual(len(set(literals)),4)
            with Solver(name='glucose3',bootstrap_with=(list(c) for c in iter_cnf(root/'formula.cnf'))) as solver:
                self.assertFalse(solver.solve(assumptions=[-v for v in literals]))
                for i,v in enumerate(literals):
                    for w in literals[i+1:]:
                        self.assertFalse(solver.solve(assumptions=[v,w]))
            for case in range(4):
                output=base/str(case);child(root,output,case)
                self.assertEqual(solve(output/'formula.cnf',output/'proof.drup'),'SAT_FINITE_CNF')
                decode(output)
                model=json.loads((output/'model.json').read_text())
                literal=literals[case]
                model[model.index(literal)]=-literal
                (output/'model.json').write_text(json.dumps(model))
                with self.assertRaises(ValueError):decode(output)
            (root/'selectors.json').write_text('[]')
            with self.assertRaises(AssertionError):plan(root)

if __name__=='__main__':unittest.main()
